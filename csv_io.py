"""CSV import/export for ExpenseMate transactions."""

import sqlite3
from pathlib import Path
from typing import Union

import pandas as pd
import database as db


def export_transactions_csv(
    conn: sqlite3.Connection,
    filepath: Union[str, Path],
) -> None:
    """Write all transactions to a CSV file."""
    rows = db.get_transactions(conn)
    df = pd.DataFrame(rows, columns=["id", "type", "amount", "category", "date", "note"])
    df.to_csv(filepath, index=False)


def import_transactions_csv(
    conn: sqlite3.Connection,
    filepath: Union[str, Path],
) -> int:
    """Read a CSV of transactions and insert each row into the database.

    Expected columns: type, amount, category, date, note (id is ignored/regenerated).
    Returns the number of rows imported.
    """
    df = pd.read_csv(filepath)
    categories = {name: cid for cid, name in db.get_categories(conn)}

    count = 0
    for _, row in df.iterrows():
        category_id = categories.get(row["category"])
        if category_id is None:
            db.add_category(conn, row["category"])
            categories = {name: cid for cid, name in db.get_categories(conn)}
            category_id = categories[row["category"]]

        db.add_transaction(
            conn,
            type_=row["type"],
            amount=float(row["amount"]),
            category_id=category_id,
            date=str(row["date"]),
            note=row.get("note", ""),
        )
        count += 1
    return count