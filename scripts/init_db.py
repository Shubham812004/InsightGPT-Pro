# scripts/init_db.py
from sqlalchemy import create_engine, text
import os

DB_FILE_PATH = os.path.join('data', 'analytics.db')
engine = create_engine(f'sqlite:///{DB_FILE_PATH}')

def initialize_database():
    with engine.connect() as connection:
        # Reverting to the original schema without the email column
        create_table_sql = text("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL
        );
        """)
        connection.execute(create_table_sql)

    print("Database initialized. 'users' table created for SQLite.")

if __name__ == "__main__":
    initialize_database()