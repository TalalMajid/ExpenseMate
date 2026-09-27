"""Unit tests for the data access layer (database.py)."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import database as db


def make_test_conn():
    """Create an in-memory database, isolated from the real expensemate.db."""
    conn = db.get_connection(":memory:")
    db.init_db(conn)
    return conn


def test_add_and_get_transaction():
    conn = make_test_conn()
    categories = db.get_categories(conn)
    food_id = categories[0][0]

    db.add_transaction(conn, "expense", 50.0, food_id, "2026-09-13", "Groceries")
    rows = db.get_transactions(conn)

    assert len(rows) == 1
    assert rows[0][1] == "expense"
    assert rows[0][2] == 50.0


def test_delete_transaction():
    conn = make_test_conn()
    categories = db.get_categories(conn)
    food_id = categories[0][0]

    db.add_transaction(conn, "expense", 20.0, food_id, "2026-09-13", "Snacks")
    transaction_id = db.get_transactions(conn)[0][0]

    db.delete_transaction(conn, transaction_id)
    assert len(db.get_transactions(conn)) == 0


def test_update_transaction():
    conn = make_test_conn()
    categories = db.get_categories(conn)
    food_id = next(category_id for category_id, name in categories if name == "Food")
    salary_id = next(category_id for category_id, name in categories if name == "Salary")

    db.add_transaction(conn, "expense", 20.0, food_id, "2026-09-13", "Snacks")
    transaction_id = db.get_transactions(conn)[0][0]

    db.update_transaction(
        conn, transaction_id, "income", 75.5, salary_id, "2026-09-14", "Refund"
    )
    updated = db.get_transactions(conn)[0]

    assert updated == (transaction_id, "income", 75.5, "Salary", "2026-09-14", "Refund")


def test_application_settings_persist_between_connections(tmp_path):
    db_path = tmp_path / "expensemate.db"
    conn = db.get_connection(db_path)
    db.init_db(conn)

    assert db.get_setting(conn, "currency_symbol", "$") == "$"
    db.set_setting(conn, "currency_symbol", "€")
    conn.close()

    reopened_conn = db.get_connection(db_path)
    db.init_db(reopened_conn)
    assert db.get_setting(reopened_conn, "currency_symbol", "$") == "€"
    reopened_conn.close()