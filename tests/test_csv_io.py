"""Unit tests for CSV import/export (csv_io.py)."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import database as db
import csv_io


def test_export_then_import_roundtrip(tmp_path):
    conn = db.get_connection(":memory:")
    db.init_db(conn)
    categories = db.get_categories(conn)
    food_id = categories[0][0]
    db.add_transaction(conn, "expense", 15.0, food_id, "2026-09-13", "Coffee")

    csv_path = tmp_path / "export.csv"
    csv_io.export_transactions_csv(conn, csv_path)

    conn2 = db.get_connection(":memory:")
    db.init_db(conn2)
    count = csv_io.import_transactions_csv(conn2, csv_path)

    assert count == 1
    assert len(db.get_transactions(conn2)) == 1