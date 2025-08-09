# db.py
import sqlite3
import hashlib
from typing import Optional, List, Tuple

DB_FILE = "finance.db"

def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    # users table (password stored hashed)
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)
    # unified transactions table stores both income and expense
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('income','expense')),
        date TEXT DEFAULT (DATE('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    conn.close()

# password hashing (sha256)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(username: str, password: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    hashed = hash_password(password)
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return user_id

def get_user(username: str, password: str) -> Optional[Tuple]:
    conn = get_conn()
    c = conn.cursor()
    hashed = hash_password(password)
    c.execute("SELECT id, username FROM users WHERE username = ? AND password = ?", (username, hashed))
    row = c.fetchone()
    conn.close()
    return row

# Transactions
def add_transaction(user_id: int, amount: float, category: str, t_type: str, date: str = None) -> int:
    """
    t_type must be 'income' or 'expense'
    date optional (YYYY-MM-DD). If None, DB default date will be used.
    Returns inserted transaction id.
    """
    conn = get_conn()
    c = conn.cursor()
    if date:
        c.execute(
            "INSERT INTO transactions (user_id, amount, category, type, date) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, t_type, date)
        )
    else:
        c.execute(
            "INSERT INTO transactions (user_id, amount, category, type) VALUES (?, ?, ?, ?)",
            (user_id, amount, category, t_type)
        )
    conn.commit()
    tid = c.lastrowid
    conn.close()
    return tid

def get_transactions(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, amount, category, type, date FROM transactions WHERE user_id = ? ORDER BY date DESC, id DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def delete_transaction(tx_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()

def update_transaction(tx_id: int, amount: float, category: str, t_type: str, date: str = None):
    conn = get_conn()
    c = conn.cursor()
    if date:
        c.execute("UPDATE transactions SET amount = ?, category = ?, type = ?, date = ? WHERE id = ?", (amount, category, t_type, date, tx_id))
    else:
        c.execute("UPDATE transactions SET amount = ?, category = ?, type = ? WHERE id = ?", (amount, category, t_type, tx_id))
    conn.commit()
    conn.close()

def calculate_totals(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT IFNULL(SUM(amount),0) FROM transactions WHERE user_id = ? AND type = 'income'", (user_id,))
    total_income = c.fetchone()[0] or 0
    c.execute("SELECT IFNULL(SUM(amount),0) FROM transactions WHERE user_id = ? AND type = 'expense'", (user_id,))
    total_expense = c.fetchone()[0] or 0
    conn.close()
    savings = total_income - total_expense
    return total_income, total_expense, savings