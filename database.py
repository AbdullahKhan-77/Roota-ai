import psycopg2
import psycopg2.errors
from psycopg2.extras import RealDictCursor
import json
import os
from datetime import datetime, timedelta, timezone
import secrets
import bcrypt

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            reset_token TEXT,
            reset_token_expiry TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id SERIAL PRIMARY KEY,
            timestamp TEXT NOT NULL,
            log_text TEXT NOT NULL,
            repo TEXT,
            errors TEXT NOT NULL,
            warnings TEXT NOT NULL,
            diagnosis TEXT,
            total_lines INTEGER,
            error_count INTEGER,
            warning_count INTEGER,
            feedback TEXT,
            user_id INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS waitlist (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limits (
            identifier TEXT NOT NULL,
            bucket TEXT NOT NULL,
            window_start BIGINT NOT NULL,
            count INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (identifier, bucket, window_start)
        )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized.")


def save_incident(log_text, repo, errors, warnings, diagnosis, total_lines, user_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO incidents
        (timestamp, log_text, repo, errors, warnings, diagnosis, total_lines, error_count, warning_count, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    ''', (
        datetime.now().isoformat(),
        log_text,
        repo,
        json.dumps(errors),
        json.dumps(warnings),
        diagnosis,
        total_lines,
        len(errors),
        len(warnings),
        user_id
    ))

    incident_id = cursor.fetchone()['id']
    conn.commit()
    cursor.close()
    conn.close()
    return incident_id


def get_all_incidents():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM incidents ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(row) for row in rows]


def get_incident(incident_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM incidents WHERE id = %s', (incident_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None


def save_feedback(incident_id, rating):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE incidents SET feedback = %s WHERE id = %s',
        (rating, incident_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


def create_user(name, username, email, password):
    if len(password) < 8:
        return {"error": "Password must be at least 8 characters"}
    if not email or "@" not in email or "." not in email.split("@")[-1] or len(email) > 254:
        return {"error": "Enter a valid email address"}

    conn = get_connection()
    cursor = conn.cursor()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    api_key = secrets.token_urlsafe(32)
    try:
        cursor.execute(
            '''INSERT INTO users (name, username, email, api_key, password_hash, created_at)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id''',
            (name, username, email, api_key, password_hash, datetime.now().isoformat())
        )
        user_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        return {"id": user_id, "name": name, "username": username, "email": email, "api_key": api_key}
    except psycopg2.errors.UniqueViolation as e:
        conn.rollback()
        cursor.close()
        conn.close()
        if 'username' in str(e):
            return {"error": "Username already taken"}
        return {"error": "Email already registered"}


def verify_user(login, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = %s OR email = %s', (login, login))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return None
    user = dict(row)
    if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return user
    return None


def get_user_by_api_key(api_key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE api_key = %s', (api_key,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return dict(row) if row else None


def get_user_incidents(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM incidents WHERE user_id = %s ORDER BY timestamp DESC',
        (user_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [dict(row) for row in rows]


def update_user_password(user_id, new_password_hash):
    """Used by /change-password and /reset-password in api.py (previously raw sqlite3 in api.py)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET password_hash = %s WHERE id = %s',
        (new_password_hash, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


def add_to_waitlist(email):
    """Used by /waitlist in api.py (previously raw sqlite3 in api.py, table created on every request)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO waitlist (email, created_at) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING',
            (email, datetime.now().isoformat())
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def set_reset_token(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return None

    token = secrets.token_urlsafe(32)
    expiry = (datetime.now() + timedelta(hours=1)).isoformat()

    cursor.execute(
        'UPDATE users SET reset_token = %s, reset_token_expiry = %s WHERE email = %s',
        (token, expiry, email)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return token

def check_rate_limit(identifier, bucket, limit, window_seconds):
    """
    Fixed-window rate limiter backed by Postgres. Safe across multiple gunicorn
    workers because the increment is a single atomic upsert - Postgres
    serializes concurrent writers on the same row, so two workers can't both
    read count=N and both write back N+1.
    """
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    window_start = now_epoch - (now_epoch % window_seconds)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO rate_limits (identifier, bucket, window_start, count)
           VALUES (%s, %s, %s, 1)
           ON CONFLICT (identifier, bucket, window_start)
           DO UPDATE SET count = rate_limits.count + 1
           RETURNING count''',
        (identifier, bucket, window_start)
    )
    count = cursor.fetchone()['count']
    conn.commit()
    cursor.close()
    conn.close()
    return count <= limit

def get_user_by_reset_token(token):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE reset_token = %s', (token,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return None
    user = dict(row)

    if not user['reset_token_expiry'] or datetime.fromisoformat(user['reset_token_expiry']) < datetime.now():
        return None

    return user


def clear_reset_token(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET reset_token = NULL, reset_token_expiry = NULL WHERE id = %s',
        (user_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()


if __name__ == '__main__':
    init_db()