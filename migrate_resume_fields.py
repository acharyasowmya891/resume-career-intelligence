import sqlite3
import os

# Locate the existing database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "resumeai.db")

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

# Check existing columns
cursor.execute("PRAGMA table_info(users)")
existing_columns = [
    column[1] for column in cursor.fetchall()
]

# Add missing columns
new_columns = {
    "resume_skills": "JSON",
    "matched_skills": "JSON",
    "missing_skills": "JSON"
}

for column_name, column_type in new_columns.items():

    if column_name not in existing_columns:
        cursor.execute(
            f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
        )
        print(f"Added column: {column_name}")
    else:
        print(f"Column already exists: {column_name}")

connection.commit()
connection.close()

print("Database migration completed successfully!")