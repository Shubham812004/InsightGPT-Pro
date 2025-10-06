# app/services/redis_service.py
import redis
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")),
        password=os.getenv("REDIS_PASSWORD"), decode_responses=True,
    )
    redis_client.ping()
    print("✅ Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"⚠️ Could not connect to Redis: {e}.")
    redis_client = None

def create_new_session(username: str, chat_history: list) -> str:
    """Creates a new chat session in Redis and returns the session ID."""
    if not redis_client: return None

    session_id = f"{username}:{int(time.time())}"
    session_key = f"session:{session_id}"
    user_sessions_key = f"user_sessions:{username}"

    try:
        # Store the chat history for the new session
        redis_client.set(session_key, json.dumps(chat_history))
        # Add the new session ID to the user's list of sessions
        redis_client.lpush(user_sessions_key, session_id)
        print(f"Created new session {session_id} for user {username}")
        return session_id
    except Exception as e:
        print(f"Error creating new session in Redis: {e}")
        return None

def update_session(session_id: str, chat_history: list):
    """Updates an existing chat session in Redis."""
    if not redis_client: return

    session_key = f"session:{session_id}"
    try:
        redis_client.set(session_key, json.dumps(chat_history))
        print(f"Updated session {session_id}")
    except Exception as e:
        print(f"Error updating session in Redis: {e}")

def get_sessions_for_user(username: str) -> list:
    """Retrieves a list of all session IDs and their titles for a user."""
    if not redis_client: return []

    user_sessions_key = f"user_sessions:{username}"
    session_ids = redis_client.lrange(user_sessions_key, 0, -1)

    sessions_with_titles = []
    for session_id in session_ids:
        history = get_session(session_id)
        if history and len(history) > 0:
            # Use the first user question as the title
            title = history[0].get('content', 'Untitled Chat')
            sessions_with_titles.append({"id": session_id, "title": title})
    return sessions_with_titles

def get_session(session_id: str) -> list:
    """Retrieves the chat history for a specific session ID."""
    if not redis_client: return []

    session_key = f"session:{session_id}"
    data = redis_client.get(session_key)
    if data:
        return json.loads(data)
    return []