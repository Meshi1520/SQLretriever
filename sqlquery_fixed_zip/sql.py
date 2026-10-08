import sqlite3

## connect to the student database
connection = sqlite3.connect('student.db')
# create a cursor
cursor = connection.cursor()
table_info = """
CREATE TABLE IF NOT EXISTS STUDENT(
    NAME VARCHAR(25),
    CLASS VARCHAR(25),
    SECTION VARCHAR(25),
    MARKS INT
);
"""
cursor.execute(table_info)
# insert some records
cursor.execute("INSERT INTO STUDENT VALUES('Shivansh','12th','A',95)")
cursor.execute("INSERT INTO STUDENT VALUES('Rohit','12th','B',85)")
cursor.execute("INSERT INTO STUDENT VALUES('Rohit','12th','B',90)")
cursor.execute("INSERT INTO STUDENT VALUES('Rohit','12th','B',80)")
cursor.execute("INSERT INTO STUDENT VALUES('Rohit','12th','B',75)")

# display the records
print("The records are:")
data = cursor.execute('SELECT * FROM STUDENT')
for row in data:
    print(row)

# close the connection
connection.commit()
connection.close()



