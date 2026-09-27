"""Integration tests: verify two real modules work correctly together
(no in-memory fakes standing in for a collaborator, unlike the unit tests)."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import analytics
import database as db


def test_budget_alert_reflects_real_database_state():
    """analytics.check_budget_alerts() must correctly read data that
    database.py actually wrote — this crosses the business logic /
    data access boundary, so it is an integration test, not a unit test."""
    conn = db.get_connection(":memory:")
    db.init_db(conn)
    food_id = next(cid for cid, name in db.get_categories(conn) if name == "Food")
    db.set_budget(conn, food_id, "2026-09-16", 100.0)
    db.add_transaction(conn, "expense", 95.0, food_id, "2026-09-16", "Weekly shop")
    alerts = analytics.check_budget_alerts(conn, "2026-09-16")
    assert len(alerts) == 1
    assert "Food" in alerts[0]


def test_no_alert_when_under_budget():
    """Same integration path, opposite case: spending well under budget
    must NOT trigger an alert."""
    conn = db.get_connection(":memory:")
    db.init_db(conn)
    food_id = next(cid for cid, name in db.get_categories(conn) if name == "Food")
    db.set_budget(conn, food_id, "2026-09-16", 100.0)
    db.add_transaction(conn, "expense", 20.0, food_id, "2026-09-16", "Snacks")
    assert analytics.check_budget_alerts(conn, "2026-09-16") == []


def test_budget_alert_uses_selected_currency_symbol():
    conn = db.get_connection(":memory:")
    db.init_db(conn)
    food_id = next(cid for cid, name in db.get_categories(conn) if name == "Food")
    db.set_budget(conn, food_id, "2026-09-16", 100.0)
    db.add_transaction(conn, "expense", 95.0, food_id, "2026-09-16", "Weekly shop")

    alerts = analytics.check_budget_alerts(conn, "2026-09-16", "€")

    assert len(alerts) == 1
    assert "€95.00" in alerts[0]
    assert "€100.00" in alerts[0]