"""UI-level regression tests for currency selection and CSV import/export."""

from pathlib import Path
import sys

from streamlit.testing.v1 import AppTest

sys.path.append(str(Path(__file__).parent.parent))

import database as db


def test_currency_selection_and_csv_controls_persist(tmp_path, monkeypatch):
    db_path = tmp_path / "expensemate.db"
    monkeypatch.setenv("EXPENSEMATE_DB_PATH", str(db_path))

    app = AppTest.from_file(
        str(Path(__file__).parent.parent / "app.py"),
        default_timeout=15,
    ).run()
    assert not app.exception

    app.selectbox[0].set_value("€").run()
    assert not app.exception
    conn = db.get_connection(db_path)
    assert db.get_setting(conn, "currency_symbol", "$") == "€"
    conn.close()

    app.radio[0].set_value("Add Transaction").run()
    assert any(item.label == "Amount (€)" for item in app.number_input)
    app.radio[0].set_value("Budgets").run()
    assert any(item.label == "Budget limit (€)" for item in app.number_input)

    app.radio[0].set_value("Import/Export").run()
    assert len(app.get("download_button")) == 1
    app.radio[0].set_value("Dashboard").run()
    app.radio[0].set_value("Import/Export").run()
    assert len(app.get("download_button")) == 1

    csv_contents = (
        b"type,amount,category,date,note\n"
        b"expense,12.5,Food,2026-09-25,Coffee\n"
    )
    app.file_uploader[0].set_value(
        ("transactions.csv", csv_contents, "text/csv")
    ).run()
    import_button = next(
        button for button in app.button if button.label == "Import transactions"
    )
    assert not import_button.disabled

    import_button.click().run()
    assert not app.exception
    conn = db.get_connection(db_path)
    assert len(db.get_transactions(conn)) == 1
    conn.close()

    import_button = next(
        button for button in app.button if button.label == "Import transactions"
    )
    import_button.click().run()
    conn = db.get_connection(db_path)
    assert len(db.get_transactions(conn)) == 1
    conn.close()

    import_button = next(
        button for button in app.button if button.label == "Import transactions"
    )
    assert import_button.disabled
    assert any("already been imported" in element.value for element in app.info)
    assert len(app.get("download_button")) == 1

    different_csv = (
        b"type,amount,category,date,note\n"
        b"expense,7.5,Food,2026-09-26,Tea\n"
    )
    app.file_uploader[0].set_value(
        ("transactions.csv", different_csv, "text/csv")
    ).run()
    import_button = next(
        button for button in app.button if button.label == "Import transactions"
    )
    assert not import_button.disabled

    import_button.click().run()
    conn = db.get_connection(db_path)
    assert len(db.get_transactions(conn)) == 2
    conn.close()

    app.radio[0].set_value("Transactions").run()
    assert any("€12.50" in item.value for item in app.markdown)
    assert any("€7.50" in item.value for item in app.markdown)
