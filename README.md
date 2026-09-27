# ExpenseMate

ExpenseMate is a local personal expense manager built with Streamlit and SQLite.

## Currency display

Choose `$`, `€`, `£`, or `₨` from the sidebar. The selected symbol is saved in the
local database and used for displayed amounts, budget alerts, and chart labels.
This changes the display symbol only; it does not convert transaction amounts
or fetch exchange rates.

## Database location

By default, the SQLite database is `expensemate.db` beside `database.py`. Set
`EXPENSEMATE_DB_PATH` to use another database file.

## Tests

Run the test suite with `pytest -q`.