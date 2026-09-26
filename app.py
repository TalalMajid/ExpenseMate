"""ExpenseMate — Streamlit UI (presentation layer).

Run with: streamlit run app.py
"""

from datetime import date
import html
from pathlib import Path
import tempfile

import pandas as pd
import plotly.express as px
import streamlit as st

import analytics
import csv_io
import database as db


st.set_page_config(page_title="ExpenseMate", page_icon="💰", layout="wide")
st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    h1, h2, h3 { letter-spacing: -0.03em; }
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 14px;
        padding: 1rem 1.1rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
    }
    .money-positive { color: #4ade80; font-weight: 700; }
    .money-negative { color: #fb7185; font-weight: 700; }
    .money-neutral { color: #e2e8f0; font-weight: 700; }
    .summary-card {
        background: rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        margin-bottom: 1rem;
    }
    .summary-label { color: #9ca3af; font-size: 0.9rem; }
    .summary-value { font-size: 1.5rem; margin-top: 0.35rem; }
    .balance-value { font-size: 1.8rem; margin-top: 0.5rem; }
    section[data-testid="stSidebar"] { border-right: 1px solid rgba(148, 163, 184, 0.16); }
    </style>
    """,
    unsafe_allow_html=True,
)

conn = db.get_connection()
db.init_db(conn)
categories = db.get_categories(conn)
category_names = [name for _, name in categories]
category_lookup = {name: category_id for category_id, name in categories}


def money(amount: float) -> str:
    """Format all displayed monetary amounts consistently."""
    return f"${amount:,.2f}"


def money_markup(amount: float, kind: str = "neutral") -> str:
    """Return a colored, consistently formatted amount for Streamlit markdown."""
    class_name = {
        "income": "money-positive",
        "expense": "money-negative",
        "neutral": "money-neutral",
    }[kind]
    return f'<span class="{class_name}">{money(amount)}</span>'


def render_money_metric(label: str, amount: float, kind: str = "neutral") -> None:
    st.markdown(
        f'<div class="summary-card"><div class="summary-label">{html.escape(label)}</div>'
        f'<div class="summary-value">{money_markup(amount, kind)}</div></div>',
        unsafe_allow_html=True,
    )


def expense_frame(frame: pd.DataFrame, month: str | None = None) -> pd.DataFrame:
    expenses = frame[frame["type"] == "expense"]
    if month is not None:
        expenses = expenses[expenses["date"].astype(str).str.startswith(month)]
    return expenses


def render_budget_alerts(month: str) -> None:
    alerts = analytics.check_budget_alerts(conn, month)
    if alerts:
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("No budget alerts for this month.")


def budget_chart(frame: pd.DataFrame, month: str) -> None:
    budgets = db.get_budgets(conn, month)
    if not budgets:
        st.info("Set a budget to compare limits with actual spending.")
        return

    expenses = expense_frame(frame, month)
    actual_by_category = expenses.groupby("category")["amount"].sum().to_dict()
    comparison = pd.DataFrame(
        [
            {
                "Category": category,
                "Budget limit": limit_amount,
                "Actual spend": actual_by_category.get(category, 0.0),
            }
            for _, category, limit_amount in budgets
        ]
    )
    chart_data = comparison.melt(
        id_vars="Category",
        var_name="Type",
        value_name="Amount",
    )
    figure = px.bar(
        chart_data,
        x="Category",
        y="Amount",
        color="Type",
        barmode="group",
        color_discrete_map={"Budget limit": "#818cf8", "Actual spend": "#fb7185"},
    )
    figure.update_layout(
        template="plotly_dark",
        legend_title_text="",
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(title="Amount", tickprefix="$", tickformat=",.2f"),
        xaxis_title="",
        hoverlabel=dict(namelength=-1),
    )
    figure.update_traces(hovertemplate="%{x}<br>%{data.name}: $%{y:,.2f}<extra></extra>")
    st.plotly_chart(figure, width="stretch")


st.sidebar.title("💰 ExpenseMate")
page = st.sidebar.radio(
    "Navigate",
    [
        "Dashboard",
        "Add Transaction",
        "Transactions",
        "Budgets",
        "Analytics",
        "Import/Export",
    ],
    label_visibility="collapsed",
)
st.sidebar.caption("Personal finances, at a glance.")

st.title(page)
today = date.today()
current_month = today.strftime("%Y-%m")
transactions = analytics.transactions_to_dataframe(conn)
this_month = transactions[
    transactions["date"].astype(str).str.startswith(current_month)
]

if page == "Dashboard":
    st.caption(today.strftime("%B %Y"))
    lifetime_totals = analytics.monthly_totals(transactions)
    month_totals = analytics.monthly_totals(this_month)

    with st.container(border=True):
        balance_kind = "income" if lifetime_totals["balance"] >= 0 else "expense"
        st.subheader("Current balance")
        st.markdown(
            f'<div class="balance-value">'
            f'{money_markup(lifetime_totals["balance"], balance_kind)}</div>',
            unsafe_allow_html=True,
        )

    income_col, expense_col = st.columns(2)
    with income_col:
        render_money_metric("🟢 Income this month", month_totals["income"], "income")
    with expense_col:
        render_money_metric("🔴 Expenses this month", month_totals["expense"], "expense")

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.subheader("Top spending categories")
            top_categories = analytics.category_summary(expense_frame(transactions, current_month))
            top_categories = top_categories.sort_values("amount", ascending=False).head(3)
            if top_categories.empty:
                st.caption("No expenses recorded this month.")
            else:
                for _, row in top_categories.iterrows():
                    st.markdown(
                        f"{html.escape(str(row['category']))} · "
                        f"{money_markup(float(row['amount']), 'expense')}",
                        unsafe_allow_html=True,
                    )
    with right:
        with st.container(border=True):
            st.subheader("⚠️ Budget alerts")
            render_budget_alerts(current_month)

elif page == "Add Transaction":
    with st.container(border=True):
        st.subheader("Record a transaction")
        with st.form("add_transaction_form", clear_on_submit=True):
            transaction_type = st.selectbox("Type", ["expense", "income"])
            amount = st.number_input("Amount ($)", min_value=0.01, step=1.0, format="%.2f")
            category = st.selectbox("Category", category_names)
            transaction_date = st.date_input("Date", value=today)
            note = st.text_input("Note (optional)")
            submitted = st.form_submit_button("Add transaction", type="primary")
        if submitted:
            db.add_transaction(
                conn,
                transaction_type,
                amount,
                category_lookup[category],
                transaction_date.isoformat(),
                note,
            )
            st.success("Transaction added.")

elif page == "Transactions":
    st.subheader("Your transactions")
    rows = db.get_transactions(conn)
    if rows:
        parsed_dates = [date.fromisoformat(row[4]) for row in rows]
        min_date, max_date = min(parsed_dates), max(parsed_dates)
        filter_col, start_col, end_col = st.columns([1, 1, 1])
        with filter_col:
            category_filter = st.selectbox(
                "Category",
                ["All categories", *category_names],
            )
        with start_col:
            start_date = st.date_input("From", value=min_date, min_value=min_date, max_value=max_date)
        with end_col:
            end_date = st.date_input("To", value=max_date, min_value=min_date, max_value=max_date)

        if start_date > end_date:
            st.error("The start date must be on or before the end date.")
            filtered_rows = []
        else:
            filtered_rows = [
                row
                for row in rows
                if start_date <= date.fromisoformat(row[4]) <= end_date
                and (category_filter == "All categories" or row[3] == category_filter)
            ]

        if not filtered_rows:
            st.info("No transactions match these filters.")
        for transaction_id, transaction_type, amount, category, transaction_date, note in filtered_rows:
            with st.container(border=True):
                details, amount_col, edit_col, delete_col = st.columns([4, 1.5, 1, 1])
                with details:
                    st.markdown(
                        f"**{html.escape(category)}** · {transaction_date} · "
                        f"{html.escape(transaction_type.title())}"
                    )
                    if note:
                        st.caption(note)
                with amount_col:
                    kind = "income" if transaction_type == "income" else "expense"
                    st.markdown(
                        money_markup(amount, kind),
                        unsafe_allow_html=True,
                    )
                with edit_col:
                    if st.button("✏️ Edit", key=f"edit_{transaction_id}"):
                        st.session_state["editing_transaction"] = transaction_id
                        st.rerun()
                with delete_col:
                    if st.button("🗑️ Delete", key=f"delete_{transaction_id}"):
                        db.delete_transaction(conn, transaction_id)
                        st.success("Transaction deleted.")
                        st.rerun()

        edit_id = st.session_state.get("editing_transaction")
        transaction_to_edit = next((row for row in rows if row[0] == edit_id), None)
        if transaction_to_edit is not None:
            _, old_type, old_amount, old_category, old_date, old_note = transaction_to_edit
            with st.container(border=True):
                st.subheader("✏️ Edit transaction")
                with st.form(f"edit_transaction_{edit_id}"):
                    edited_type = st.selectbox(
                        "Type",
                        ["expense", "income"],
                        index=["expense", "income"].index(old_type),
                        key="edit_type",
                    )
                    edited_amount = st.number_input(
                        "Amount ($)",
                        min_value=0.01,
                        value=float(old_amount),
                        step=1.0,
                        format="%.2f",
                        key="edit_amount",
                    )
                    edited_category = st.selectbox(
                        "Category",
                        category_names,
                        index=category_names.index(old_category),
                        key="edit_category",
                    )
                    edited_date = st.date_input(
                        "Date",
                        value=date.fromisoformat(old_date),
                        key="edit_date",
                    )
                    edited_note = st.text_input("Note (optional)", value=old_note or "", key="edit_note")
                    save_edit, cancel_edit = st.columns(2)
                    with save_edit:
                        save = st.form_submit_button("Save changes", type="primary")
                    with cancel_edit:
                        cancel = st.form_submit_button("Cancel")
                if save:
                    db.update_transaction(
                        conn,
                        edit_id,
                        edited_type,
                        edited_amount,
                        category_lookup[edited_category],
                        edited_date.isoformat(),
                        edited_note,
                    )
                    del st.session_state["editing_transaction"]
                    st.success("Transaction updated.")
                    st.rerun()
                if cancel:
                    del st.session_state["editing_transaction"]
                    st.rerun()
    else:
        st.info("No transactions yet. Add one to get started.")

elif page == "Budgets":
    with st.container(border=True):
        st.subheader("Set a monthly budget")
        budget_date = st.date_input(
            "Budget month",
            value=today.replace(day=1),
            key="budget_month_date",
        )
        budget_month = budget_date.strftime("%Y-%m")
        budget_category = st.selectbox("Category", category_names, key="budget_category")
        budget_limit = st.number_input(
            "Budget limit ($)",
            min_value=0.01,
            step=10.0,
            format="%.2f",
        )
        if st.button("Save budget", type="primary"):
            db.set_budget(
                conn,
                category_lookup[budget_category],
                budget_month,
                budget_limit,
            )
            st.success("Budget saved.")

    st.subheader(f"⚠️ Budget alerts · {budget_month}")
    render_budget_alerts(budget_month)
    st.subheader(f"📊 Budget vs. actual · {budget_month}")
    budget_chart(transactions, budget_month)

elif page == "Analytics":
    st.subheader("📊 Spending insights")
    analytics_month = st.date_input(
        "Month",
        value=today.replace(day=1),
        key="analytics_month_date",
    ).strftime("%Y-%m")
    selected_month = transactions[
        transactions["date"].astype(str).str.startswith(analytics_month)
    ]
    totals = analytics.monthly_totals(selected_month)
    income_col, expense_col, balance_col = st.columns(3)
    with income_col:
        render_money_metric("🟢 Income", totals["income"], "income")
    with expense_col:
        render_money_metric("🔴 Expenses", totals["expense"], "expense")
    with balance_col:
        balance_kind = "income" if totals["balance"] >= 0 else "expense"
        render_money_metric("Balance", totals["balance"], balance_kind)

    chart_col, budget_col = st.columns(2)
    with chart_col:
        with st.container(border=True):
            st.subheader("Spending by category")
            summary = analytics.category_summary(selected_month)
            if summary.empty:
                st.info("No expenses recorded for this month.")
            else:
                pie = px.pie(summary, names="category", values="amount")
                pie.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=20, b=10))
                pie.update_traces(hovertemplate="%{label}: $%{value:,.2f}<extra></extra>")
                st.plotly_chart(pie, width="stretch")
    with budget_col:
        with st.container(border=True):
            st.subheader("Budget limit vs. actual")
            budget_chart(transactions, analytics_month)

elif page == "Import/Export":
    export_col, import_col = st.columns(2)
    with export_col:
        with st.container(border=True):
            st.subheader("Export")
            if st.button("Export transactions to CSV"):
                with tempfile.TemporaryDirectory(prefix="expensemate-export-") as temp_dir:
                    export_path = Path(temp_dir) / "transactions_export.csv"
                    csv_io.export_transactions_csv(conn, export_path)
                    export_data = export_path.read_bytes()
                st.download_button(
                    "Download CSV",
                    data=export_data,
                    file_name="transactions_export.csv",
                    mime="text/csv",
                )
    with import_col:
        with st.container(border=True):
            st.subheader("Import")
            uploaded = st.file_uploader("Choose a CSV file", type="csv")
            if uploaded is not None and st.button("Import transactions"):
                with tempfile.TemporaryDirectory(prefix="expensemate-import-") as temp_dir:
                    import_path = Path(temp_dir) / "transactions_import.csv"
                    import_path.write_bytes(uploaded.getvalue())
                    count = csv_io.import_transactions_csv(conn, import_path)
                st.success(f"Imported {count} transactions.")
