"""Data access layer for ExpenseMate.

All direct database reads/writes should go through this module only,
per the Layered architecture decided for this project.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Union

DB_PATH = Path(__file__).parent / "expensemate.db"


def get_connection(
    db_path: Optional[Union[str, Path]] = None,
) -> sqlite3.Connection:
    """Open (or create) the SQLite database file and return a connection."""
    resolved_db_path = (
        db_path
        if db_path is not None
        else os.environ.get("EXPENSEMATE_DB_PATH", DB_PATH)
    )
    conn = sqlite3.connect(resolved_db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables if they don't already exist, and seed default categories."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            month TEXT NOT NULL,
            limit_amount REAL NOT NULL,
            UNIQUE(category_id, month),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()

    default_categories = ["Food", "Transport", "Rent", "Utilities", "Entertainment", "Salary", "Other"]
    for name in default_categories:
        add_category(conn, name)


def add_category(conn: sqlite3.Connection, name: str) -> None:
    """Add a category if it doesn't already exist."""
    conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
    conn.commit()


def get_categories(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    """Return all categories as (id, name) tuples."""
    return conn.execute("SELECT id, name FROM categories ORDER BY name").fetchall()


def add_transaction(
    conn: sqlite3.Connection,
    type_: str,
    amount: float,
    category_id: int,
    date: str,
    note: str = "",
) -> None:
    """Insert a new income or expense transaction."""
    conn.execute(
        "INSERT INTO transactions (type, amount, category_id, date, note) VALUES (?, ?, ?, ?, ?)",
        (type_, amount, category_id, date, note),
    )
    conn.commit()


def get_transactions(
    conn: sqlite3.Connection,
) -> list[tuple[int, str, float, str, str, Optional[str]]]:
    """Return all transactions joined with their category name."""
    return conn.execute("""
        SELECT t.id, t.type, t.amount, c.name, t.date, t.note
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        ORDER BY t.date DESC
    """).fetchall()


def delete_transaction(conn: sqlite3.Connection, transaction_id: int) -> None:
    """Remove a transaction by id."""
    conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()


def update_transaction(
    conn: sqlite3.Connection,
    transaction_id: int,
    type_: str,
    amount: float,
    category_id: int,
    date: str,
    note: str = "",
) -> None:
    """Update an existing income or expense transaction."""
    conn.execute(
        """
        UPDATE transactions
        SET type = ?, amount = ?, category_id = ?, date = ?, note = ?
        WHERE id = ?
        """,
        (type_, amount, category_id, date, note, transaction_id),
    )
    conn.commit()


def set_budget(
    conn: sqlite3.Connection,
    category_id: int,
    month: str,
    limit_amount: float,
) -> None:
    """Create or update a budget for a category in a given month (format 'YYYY-MM')."""
    conn.execute("""
        INSERT INTO budgets (category_id, month, limit_amount) VALUES (?, ?, ?)
        ON CONFLICT(category_id, month) DO UPDATE SET limit_amount = excluded.limit_amount
    """, (category_id, month, limit_amount))
    conn.commit()


def get_budgets(
    conn: sqlite3.Connection,
    month: str,
) -> list[tuple[int, str, float]]:
    """Return all budgets for a given month, joined with category name."""
    return conn.execute("""
        SELECT b.id, c.name, b.limit_amount
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        WHERE b.month = ?
    """, (month,)).fetchall()


def get_setting(conn: sqlite3.Connection, key: str, default: str) -> str:
    """Return a stored application setting, or its default when unset."""
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?",
        (key,),
    ).fetchone()
    return default if row is None else row[0]


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Create or replace an application setting."""
    conn.execute(
        """
        INSERT INTO app_settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    conn.commit()