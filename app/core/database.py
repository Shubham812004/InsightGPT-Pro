# app/core/database.py
from sqlalchemy import create_engine
import os

DB_FILE_PATH = os.path.join('data', 'analytics.db')
DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"

# Create a single, reusable engine
engine = create_engine(
    DATABASE_URL,
    # connect_args is needed for SQLite to allow multi-threaded access
    connect_args={"check_same_thread": False}
)

# Dependency to get a DB session
def get_db():
    """Yields a new database connection for a single request."""
    with engine.connect() as connection:
        yield connection