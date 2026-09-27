"""Business logic layer for ExpenseMate: budget checks, alerts, and summaries."""

import sqlite3

import pandas as pd
import database as db


def transactions_to_dataframe(conn: sqlite3.Connection) -> pd.DataFrame:
    """Pull all transactions into a pandas DataFrame for analysis."""
    rows = db.get_transactions(conn)
    return pd.DataFrame(rows, columns=["id", "type", "amount", "category", "date", "note"])


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Total expense amount per category, for the pie/bar chart."""
    expenses = df[df["type"] == "expense"]
    return expenses.groupby("category", as_index=False)["amount"].sum()


def monthly_totals(df: pd.DataFrame) -> dict[str, float]:
    """Return total income, total expenses, and balance across all transactions."""
    income = df.loc[df["type"] == "income", "amount"].sum()
    expense = df.loc[df["type"] == "expense", "amount"].sum()
    return {"income": income, "expense": expense, "balance": income - expense}


def check_budget_alerts(
    conn: sqlite3.Connection,
    month: str,
    currency_symbol: str = "$",
) -> list[str]:
    """Compare this month's spending against each category's budget.

    Returns a list of human-readable alert strings for any category
    that has spent 90% or more of its budget.
    """
    df = transactions_to_dataframe(conn)
    df_month = df[df["date"].str.startswith(month) & (df["type"] == "expense")]
    spent_by_category = df_month.groupby("category")["amount"].sum().to_dict()

    alerts = []
    for budget_id, category_name, limit_amount in db.get_budgets(conn, month):
        spent = spent_by_category.get(category_name, 0)
        if limit_amount > 0 and spent / limit_amount >= 0.9:
            alerts.append(
                f"⚠ {category_name}: spent "
                f"{currency_symbol}{spent:,.2f} of "
                f"{currency_symbol}{limit_amount:,.2f} budget "
                f"({spent/limit_amount:.0%})"
            )
    return alerts