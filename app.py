"""ExpenseMate — Streamlit UI (presentation layer).

Run with: streamlit run app.py
"""

import streamlit as st
import plotly.express as px
from datetime import date

import database as db
import analytics
import csv_io

st.set_page_config(page_title="ExpenseMate", layout="centered")
conn = db.get_connection()
db.init_db(conn)

st.title("💰 ExpenseMate")

tab_add, tab_view, tab_budget, tab_analytics, tab_csv = st.tabs(
    ["Add Transaction", "View Transactions", "Budgets", "Analytics", "Import / Export"]
)

categories = db.get_categories(conn)
category_names = [name for _, name in categories]
category_lookup = {name: cid for cid, name in categories}

with tab_add:
    st.subheader("Add a transaction")
    t_type = st.selectbox("Type", ["expense", "income"])
    amount = st.number_input("Amount", min_value=0.0, step=1.0)
    category = st.selectbox("Category", category_names)
    t_date = st.date_input("Date", value=date.today())
    note = st.text_input("Note (optional)")
    if st.button("Add"):
        db.add_transaction(conn, t_type, amount, category_lookup[category], str(t_date), note)
        st.success("Transaction added.")

with tab_view:
    st.subheader("All transactions")
    rows = db.get_transactions(conn)
    st.dataframe(rows, use_container_width=True)

with tab_budget:
    st.subheader("Set a monthly budget")
    b_category = st.selectbox("Category", category_names, key="budget_category")
    b_month = st.text_input("Month (YYYY-MM)", value=date.today().strftime("%Y-%m"))
    b_limit = st.number_input("Budget limit", min_value=0.0, step=10.0)
    if st.button("Save budget"):
        db.set_budget(conn, category_lookup[b_category], b_month, b_limit)
        st.success("Budget saved.")

    st.divider()
    st.subheader("Budget alerts")
    alerts = analytics.check_budget_alerts(conn, b_month)
    if alerts:
        for a in alerts:
            st.warning(a)
    else:
        st.info("No categories are near their budget limit yet.")

with tab_analytics:
    st.subheader("Spending by category")
    df = analytics.transactions_to_dataframe(conn)
    if not df.empty:
        summary = analytics.category_summary(df)
        if not summary.empty:
            fig = px.pie(summary, names="category", values="amount")
            st.plotly_chart(fig, use_container_width=True)

        totals = analytics.monthly_totals(df)
        col1, col2, col3 = st.columns(3)
        col1.metric("Income", f"{totals['income']:.2f}")
        col2.metric("Expenses", f"{totals['expense']:.2f}")
        col3.metric("Balance", f"{totals['balance']:.2f}")
    else:
        st.info("Add some transactions to see analytics.")

with tab_csv:
    st.subheader("Export")
    if st.button("Export to CSV"):
        csv_io.export_transactions_csv(conn, "transactions_export.csv")
        st.success("Exported to transactions_export.csv")

    st.subheader("Import")
    uploaded = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded is not None:
        with open("temp_import.csv", "wb") as f:
            f.write(uploaded.getbuffer())
        count = csv_io.import_transactions_csv(conn, "temp_import.csv")
        st.success(f"Imported {count} transactions.")