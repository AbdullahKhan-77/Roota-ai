import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "debugai.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

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
            warning_count INTEGER
            feedback TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized.")

def save_incident(log_text, repo, errors, warnings, diagnosis, total_lines):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO incidents 
        (timestamp, log_text, repo, errors, warnings, diagnosis, total_lines, error_count, warning_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        log_text,
        repo,
        json.dumps(errors),
        json.dumps(warnings),
        diagnosis,
        total_lines,
        len(errors),
        len(warnings)
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
    
if __name__ == '__main__':
    init_db()