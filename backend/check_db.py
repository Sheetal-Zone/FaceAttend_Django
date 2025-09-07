import sqlite3

# Check current database structure
conn = sqlite3.connect('face_attendance.db')
cursor = conn.cursor()

print("=== Current Database Structure ===")
cursor.execute("PRAGMA table_info(students)")
print("Students table columns:")
for row in cursor.fetchall():
    print(row)

print("\nTables in database:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for row in cursor.fetchall():
    print(row[0])

conn.close()
