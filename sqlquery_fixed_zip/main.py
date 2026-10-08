# we will create streamlit here
from dotenv import load_dotenv
load_dotenv()  # load all environment variables
import streamlit as st
import os
import re
import sqlite3
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "student.db")

API_KEY = next(
    (os.environ.get(key) for key in ["GROQ_API_KEY", "API_KEY", "api_key"] if os.environ.get(key)),
    None,
)

if API_KEY is None:
    raise RuntimeError(
        "API key not found. Set GROQ_API_KEY (or API_KEY) in your .env file."
    )

GROQ_API_URL = ""
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def call_groq_api(question: str, system_prompt: str) -> str:
    """Call Groq's OpenAI-compatible chat completions endpoint."""
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question.strip()},
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        raise RuntimeError(f"Request to Groq failed: {exc}") from exc

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f"Groq returned a non-JSON response: {response.text[:300]}")

    if response.status_code >= 400:
        message = data.get("error", {}).get("message", response.text)
        raise RuntimeError(f"Groq API error {response.status_code}: {message}")

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Groq response shape: {data}") from exc


def clean_sql(raw_sql: str) -> str:
    """Strip markdown code fences the model sometimes adds despite instructions."""
    sql = raw_sql.strip()
    sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\s*```$", "", sql)
    return sql.strip()


def is_select_only(sql: str) -> bool:
    """Only allow single, read-only SELECT statements to be executed."""
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    if len(statements) != 1:
        return False
    return bool(re.match(r"(?is)^\s*select\b", statements[0]))


def read_sql_query(sql: str, db: str):
    with sqlite3.connect(db) as conn:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = cur.fetchall()
    return columns, rows


SYSTEM_PROMPT = (
    "You are a SQL expert. You will be given a question and you will generate "
    "the SQL query for it. You will not give any explanation or any other text, "
    "and you will not wrap the query in markdown code fences. You will only "
    "output the raw SQL query. The query must be a single read-only SELECT "
    "statement compatible with SQLite. The table is STUDENT with columns "
    "NAME, CLASS, SECTION, MARKS."
)

## streamlit app
st.set_page_config(page_title="SQL QUERY GENERATOR")
st.header("SQL Query Generator using AI")

question = st.text_input("Enter your question here")
submit = st.button("Ask the AI to answer your question")

if submit:
    if not question.strip():
        st.error("Please enter a question before submitting.")
    else:
        try:
            raw_response = call_groq_api(question, SYSTEM_PROMPT)
        except RuntimeError as exc:
            st.error(str(exc))
        else:
            sql_query = clean_sql(raw_response)
            st.markdown("**Generated SQL query:**")
            st.code(sql_query, language="sql")

            if not is_select_only(sql_query):
                st.error(
                    "Refusing to run this query: only a single read-only SELECT "
                    "statement is allowed."
                )
            else:
                try:
                    columns, data = read_sql_query(sql_query, DB_PATH)
                    st.subheader("The records are:")
                    if data:
                        if columns:
                            st.dataframe(
                                [dict(zip(columns, row)) for row in data],
                                use_container_width=True,
                            )
                        else:
                            for row in data:
                                st.write(row)
                    else:
                        st.write("No rows returned.")
                except sqlite3.Error as error:
                    st.error(f"SQL execution error: {error}")
