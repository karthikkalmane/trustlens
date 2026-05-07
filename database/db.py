"""
Database module using SQLite (compatible schema with MySQL).
Tables: users, analysis_history, price_history
"""
import sqlite3, json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config


def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            analyses_count INTEGER DEFAULT 0
        )
    """)

    # Analysis history
    c.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            url TEXT NOT NULL,
            product_name TEXT,
            platform TEXT,
            risk_score REAL,
            risk_label TEXT,
            sentiment_score REAL,
            price_deviation REAL,
            seller_rating REAL,
            review_count INTEGER,
            avg_rating REAL,
            spam_score REAL,
            features_json TEXT,
            xai_json TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Price history
    c.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_hash INTEGER,
            url TEXT,
            platform TEXT,
            product_name TEXT,
            price REAL,
            recorded_at TEXT
        )
    """)

    # Guest analysis count (by IP session key)
    c.execute("""
        CREATE TABLE IF NOT EXISTS guest_sessions (
            session_key TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0,
            last_used TEXT
        )
    """)

    conn.commit()
    conn.close()


# ─── User Auth ────────────────────────────────────────────────────────
def create_user(username, email, password):
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO users (username, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
        """, (username.strip(), email.strip().lower(),
              generate_password_hash(password),
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return False, "Username already taken."
        return False, "Email already registered."
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?",
                       (email.strip().lower(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_password(email, password):
    user = get_user_by_email(email)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def increment_user_count(user_id):
    conn = get_db()
    conn.execute("UPDATE users SET analyses_count = analyses_count + 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


# ─── Guest Session ────────────────────────────────────────────────────
def get_guest_count(session_key):
    conn = get_db()
    row = conn.execute("SELECT count FROM guest_sessions WHERE session_key = ?",
                       (session_key,)).fetchone()
    conn.close()
    return row["count"] if row else 0


def increment_guest_count(session_key):
    conn = get_db()
    existing = conn.execute("SELECT count FROM guest_sessions WHERE session_key = ?",
                            (session_key,)).fetchone()
    if existing:
        conn.execute("UPDATE guest_sessions SET count = count + 1, last_used = ? WHERE session_key = ?",
                     (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session_key))
    else:
        conn.execute("INSERT INTO guest_sessions (session_key, count, last_used) VALUES (?, 1, ?)",
                     (session_key, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


# ─── Analysis History ─────────────────────────────────────────────────
def save_analysis(url, result, user_id=None):
    conn = get_db()
    f = result.get("features", {})
    xai = result.get("explanation", {})
    bot = result.get("bot_detection", {})
    c = conn.execute("""
        INSERT INTO analysis_history
        (user_id, url, product_name, platform, risk_score, risk_label,
         sentiment_score, price_deviation, seller_rating, review_count,
         avg_rating, spam_score, features_json, xai_json, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        url,
        result.get("product_name","Unknown"),
        result.get("platform","Unknown"),
        result.get("risk_score",0),
        result.get("risk_label","Unknown"),
        f.get("sentiment_score",0),
        f.get("price_deviation",0),
        f.get("seller_rating",0),
        f.get("review_count",0),
        f.get("avg_rating",0),
        bot.get("spam_score",0),
        json.dumps(f),
        json.dumps(xai),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def get_user_history(user_id, limit=50):
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM analysis_history WHERE user_id = ?
        ORDER BY timestamp DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_history(limit=50):
    conn = get_db()
    rows = conn.execute("""
        SELECT ah.*, u.username FROM analysis_history ah
        LEFT JOIN users u ON ah.user_id = u.id
        ORDER BY ah.timestamp DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_record(record_id, user_id=None):
    conn = get_db()
    if user_id:
        conn.execute("DELETE FROM analysis_history WHERE id=? AND user_id=?",
                     (record_id, user_id))
    else:
        conn.execute("DELETE FROM analysis_history WHERE id=?", (record_id,))
    conn.commit()
    conn.close()
