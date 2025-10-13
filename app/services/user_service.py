# app/services/user_service.py
from app.core.security import get_password_hash
from app.schemas.user import UserCreate, UserInDB
from sqlalchemy.orm import Session
from sqlalchemy import text

def get_user(db: Session, username: str) -> UserInDB | None:
    """Fetches a single user from the database by username."""
    query = text("SELECT id, username, hashed_password FROM users WHERE username = :username")
    result = db.execute(query, {"username": username}).fetchone()

    if result:
        user_data = result._asdict()
        return UserInDB(**user_data)
    return None

def create_user(db: Session, user: UserCreate) -> UserInDB:
    """Creates a new user in the database."""
    hashed_password = get_password_hash(user.password)

    insert_query = text("""
        INSERT INTO users (username, hashed_password)
        VALUES (:username, :hashed_password)
    """)
    db.execute(insert_query, {"username": user.username, "hashed_password": hashed_password})
    db.commit()

    new_user = get_user(db, user.username)
    if not new_user:
         raise Exception("Failed to retrieve user after creation.")
    return new_user
