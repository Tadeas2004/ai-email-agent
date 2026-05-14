import sqlite3
import json
from datetime import datetime


def init_db():
    """
    Initializes the SQLite database and creates the emails table 
    if it does not already exist.
    """
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gmail_id TEXT UNIQUE,
            email TEXT,
            summary TEXT,
            category TEXT,
            priority TEXT,
            priority_reason TEXT,
            actions TEXT,
            confidence REAL,
            sentiment TEXT,
            actionability TEXT,
            requires_response INTEGER,
            follow_up_needed INTEGER,
            deadline TEXT,
            entities TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def is_email_processed(gmail_id: str) -> bool:
    """Checks if this email has already been analyzed and stored."""
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM emails WHERE gmail_id = ?", (gmail_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def save_email(gmail_id: str, email: str, result: dict):
    """
    Saves the normalized AI analysis results into the SQLite database.
    Handles defensive type checking for schema robustness.
    """
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Extract priority level and reason safely from the normalized dictionary
    priority_field = result.get("priority", "low")
    if isinstance(priority_field, dict):
        priority_level = priority_field.get("level", "low")
        priority_reason = priority_field.get("reason", "No reason provided.")
    else:
        priority_level = str(priority_field)
        priority_reason = result.get("priority_reason", "No reason provided.")

    # Extract actions/action_items list safely
    actions_list = result.get("actions") or result.get("action_items") or []

    cursor.execute("""
        INSERT OR IGNORE INTO emails (
            gmail_id, email, summary, category, priority, priority_reason,
            actions, confidence, sentiment, actionability,
            requires_response, follow_up_needed, deadline, entities, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        gmail_id,
        email,
        result.get("summary", ""),
        result.get("category", ""),
        priority_level,
        priority_reason,
        json.dumps(actions_list),
        result.get("confidence", 0.0),
        result.get("sentiment", ""),
        result.get("actionability", ""),
        1 if result.get("requires_response") else 0,
        1 if result.get("follow_up_needed") else 0,
        result.get("deadline"),
        json.dumps(result.get("entities", {})),
        timestamp
    ))
    conn.commit()
    conn.close()


def get_history(limit: int = 20) -> list[dict]:
    """Fetches past email analysis records sorted by the latest timestamp."""
    conn = sqlite3.connect("emails.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM emails ORDER BY timestamp DESC LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    for row in rows:
        try:
            row["actions"] = json.loads(row["actions"])
        except (json.JSONDecodeError, TypeError):
            row["actions"] = []
        try:
            row["entities"] = json.loads(row["entities"])
        except (json.JSONDecodeError, TypeError):
            row["entities"] = {}
        row["requires_response"] = bool(row.get("requires_response"))
        row["follow_up_needed"] = bool(row.get("follow_up_needed"))
    return rows

def get_latest_email_record() -> dict | None:
    """Returns the single most recently added database record as a dictionary."""
    conn = sqlite3.connect("emails.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM emails ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        record = dict(row)
        
        try:
            record["actions"] = json.loads(record["actions"])
        except (json.JSONDecodeError, TypeError):
            record["actions"] = []
            
        try:
            record["entities"] = json.loads(record["entities"])
        except (json.JSONDecodeError, TypeError):
            record["entities"] = {}
            
        return record
        
    return None