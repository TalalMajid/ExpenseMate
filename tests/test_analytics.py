"""Unit tests for the business logic layer (analytics.py)."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import analytics


def test_category_summary():
    df = pd.DataFrame({
        "type": ["expense", "expense", "income"],
        "amount": [30.0, 20.0, 100.0],
        "category": ["Food", "Food", "Salary"],
    })
    summary = analytics.category_summary(df)
    food_total = summary.loc[summary["category"] == "Food", "amount"].iloc[0]
    assert food_total == 50.0


def test_monthly_totals():
    df = pd.DataFrame({
        "type": ["income", "expense"],
        "amount": [500.0, 200.0],
        "category": ["Salary", "Food"],
    })
    totals = analytics.monthly_totals(df)
    assert totals["income"] == 500.0
    assert totals["expense"] == 200.0
    assert totals["balance"] == 300.0