import os
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# Setup simple logging for the logger itself
logger = logging.getLogger(__name__)

# Define paths
BASE_DIR = Path(__file__).parent.parent.parent
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = LOGS_DIR / "chatbot_logs.db"
JSONL_PATH = LOGS_DIR / "chat_history.jsonl"

def init_db():
    """Initialize the SQLite database and create tables if they don't exist."""
    try:
        LOGS_DIR.mkdir(exist_ok=True)
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Create chat_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                brand TEXT,
                store_id TEXT,
                user_query TEXT,
                bot_response TEXT,
                prompt_tokens INTEGER,
                candidates_tokens INTEGER,
                total_tokens INTEGER,
                raw_metadata TEXT,
                feedback TEXT DEFAULT 'null'
            )
        ''')
        
        # Schema migration: Add feedback column if it doesn't exist
        cursor.execute("PRAGMA table_info(chat_logs)")
        columns = [col[1] for col in cursor.fetchall()]
        if "feedback" not in columns:
            cursor.execute("ALTER TABLE chat_logs ADD COLUMN feedback TEXT DEFAULT 'null'")
            logger.info("Chat logs schema updated with feedback column.")
        
        conn.commit()
        conn.close()
        logger.info(f"Logger initialized. DB: {DB_PATH}, JSONL: {JSONL_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def log_chat(
    session_id: str,
    user_query: str,
    bot_response: str,
    tokens: dict,
    brand: str = "mizumi",
    store_id: str = "onsite_default",
    metadata: dict = None
):
    """
    Log a chat interaction to both SQLite and JSONL.
    
    tokens: dict containing 'prompt_token_count', 'candidates_token_count', 'total_token_count'
    """
    timestamp = datetime.now().isoformat()
    
    # Prepare data for logs
    p_tokens = tokens.get("prompt_token_count", 0)
    c_tokens = tokens.get("candidates_token_count", 0)
    t_tokens = tokens.get("total_token_count", 0)
    
    log_entry = {
        "timestamp": timestamp,
        "session_id": session_id,
        "brand": brand,
        "store_id": store_id,
        "user_query": user_query,
        "bot_response": bot_response,
        "tokens": {
            "prompt": p_tokens,
            "candidates": c_tokens,
            "total": t_tokens
        },
        "metadata": metadata or {},
        "feedback": "null"
    }

    # 1. Save to JSONL (Raw backup)
    try:
        with open(JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to write to JSONL log: {e}")

    # 2. Save to SQLite (For analytics)
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_logs (
                timestamp, session_id, brand, store_id, user_query, 
                bot_response, prompt_tokens, candidates_tokens, 
                total_tokens, raw_metadata, feedback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, session_id, brand, store_id, user_query,
            bot_response, p_tokens, c_tokens, t_tokens,
            json.dumps(metadata or {}, ensure_ascii=False),
            "null"
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to write to SQLite log: {e}")

def update_feedback(session_id: str, bot_response: str, feedback: str):
    """Update the feedback for a specific bot response in the logs."""
    try:
        # Update SQLite
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        # Find the latest entry for this session and response
        cursor.execute('''
            UPDATE chat_logs
            SET feedback = ?
            WHERE id = (
                SELECT id FROM chat_logs 
                WHERE session_id = ? AND bot_response LIKE ? 
                ORDER BY timestamp DESC LIMIT 1
            )
        ''', (feedback, session_id, bot_response))
        conn.commit()
        conn.close()
        logger.info(f"Feedback updated: {feedback} for session {session_id}")
        
        # Note: updating JSONL is harder as it's an append-only format.
        # Usually, we rely on the DB for real analytics.
    except Exception as e:
        logger.error(f"Failed to update feedback: {e}")

# Initialize when module is imported
init_db()
