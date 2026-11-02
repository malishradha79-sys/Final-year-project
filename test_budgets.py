
from database import get_db_connection

connection = get_db_connection()

tables = connection.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
""").fetchall()

print("Database Tables:")

for table in tables:
    print(table["name"])

connection.close()
