import os
import psycopg2
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_URL = os.environ.get('DATABASE_URL', 'postgres://postgres:postgres@localhost:5432/postgres')

def get_db_connection():
    return psycopg2.connect(DB_URL)

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_approved BOOLEAN DEFAULT FALSE,
                    password_hash VARCHAR(255),
                    language_code VARCHAR(10) DEFAULT 'tg',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

def add_user(user_id: int, username: str = None, is_admin: bool = False):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (user_id, username, is_admin)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE
                    SET username = EXCLUDED.username
                    RETURNING user_id
                """, (user_id, username, is_admin))
                conn.commit()
                return cur.fetchone()[0]
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return None

def approve_user(user_id: int, password_hash: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users
                    SET is_approved = TRUE, password_hash = %s
                    WHERE user_id = %s
                    RETURNING user_id
                """, (password_hash, user_id))
                conn.commit()
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error approving user: {e}")
        return False

def get_user(user_id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, username, is_admin, is_approved, password_hash, language_code
                    FROM users
                    WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
                if result:
                    return {
                        'user_id': result[0],
                        'username': result[1],
                        'is_admin': result[2],
                        'is_approved': result[3],
                        'password_hash': result[4],
                        'language_code': result[5]
                    }
                return None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def update_user_language(user_id: int, language_code: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users
                    SET language_code = %s
                    WHERE user_id = %s
                    RETURNING user_id, language_code
                """, (language_code, user_id))
                conn.commit()
                result = cur.fetchone()
                return result is not None
    except Exception as e:
        logger.error(f"Error updating user language: {e}")
        return False

def get_user_language(user_id: int) -> str:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT language_code
                    FROM users
                    WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
                return result[0] if result else 'tg'
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        return 'tg'

def verify_user_password(user_id: int, password_hash: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM users
                    WHERE user_id = %s AND password_hash = %s AND is_approved = TRUE
                """, (user_id, password_hash))
                count = cur.fetchone()[0]
                return count > 0
    except Exception as e:
        logger.error(f"Error verifying user password: {e}")
        return False

# Initialize database tables
init_db()