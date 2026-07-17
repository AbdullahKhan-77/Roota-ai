import sqlite3
import json
from datetime import datetime
from pathlib import Path
import secrets
import bcrypt
import secrets
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent / "debugai.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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

    conn.commit()
    conn.close()
    print("Database initialized.")

def save_incident(log_text, repo, errors, warnings, diagnosis, total_lines,user_id=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO incidents 
        (timestamp, log_text, repo, errors, warnings, diagnosis, total_lines, error_count, warning_count,user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?)
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

    incident_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return incident_id

def get_all_incidents():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM incidents ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_incident(incident_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM incidents WHERE id = ?', (incident_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_feedback(incident_id, rating):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE incidents SET feedback = ? WHERE id = ?',
        (rating, incident_id)
    )
    conn.commit()
    conn.close()
def create_user(name, username, email, password):
    conn = get_connection()
    cursor = conn.cursor()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    api_key = secrets.token_urlsafe(32)
    try:
        cursor.execute(
            'INSERT INTO users (name, username, email, api_key, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (name, username, email, api_key, password_hash, datetime.now().isoformat())
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"id": user_id, "name": name, "username": username, "email": email, "api_key": api_key}
    except sqlite3.IntegrityError as e:
        conn.close()
        if 'username' in str(e):
            return {"error": "Username already taken"}
        return {"error": "Email already registered"}
    
def verify_user(login, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (login, login))
    row = cursor.fetchone()
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
    cursor.execute('SELECT * FROM users WHERE api_key = ?', (api_key,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_incidents(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM incidents WHERE user_id = ? ORDER BY timestamp DESC',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def migrate_add_reset_token_columns():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'reset_token' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN reset_token TEXT')
    if 'reset_token_expiry' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN reset_token_expiry TEXT')

    conn.commit()
    conn.close()
    
    
def set_reset_token(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    token = secrets.token_urlsafe(32)
    expiry = (datetime.now() + timedelta(hours=1)).isoformat()

    cursor.execute(
        'UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE email = ?',
        (token, expiry, email)
    )
    conn.commit()
    conn.close()
    return token


def get_user_by_reset_token(token):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE reset_token = ?', (token,))
    row = cursor.fetchone()
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
        'UPDATE users SET reset_token = NULL, reset_token_expiry = NULL WHERE id = ?',
        (user_id,)
    )
    conn.commit()
    conn.close()
    
if __name__ == '__main__':
    init_db()