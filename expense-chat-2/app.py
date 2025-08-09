# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from db import init_db, add_user, get_user, add_transaction, get_transactions, delete_transaction, update_transaction, calculate_totals


# Init DB
init_db()

st.set_page_config(page_title="Income & Expense Tracker", layout="centered")
st.title("💬 Income & Expense Tracker")

# --- Session state defaults ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "menu" not in st.session_state:
    st.session_state.menu = None

# --- Authentication UI (login/signup) ---
def auth_ui():
    st.subheader("Login or Sign up")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Login**")
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            user = get_user(login_user.strip(), login_pass)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.session_state.username = user[1]
                st.session_state.menu = None
                st.rerun()  # reload to show main menu
            else:
                st.error("Invalid username or password")
    with col2:
        st.markdown("**Sign up**")
        su_user = st.text_input("New username", key="su_user")
        su_pass = st.text_input("New password", type="password", key="su_pass")
        if st.button("Create account"):
            if not su_user or not su_pass:
                st.error("Enter both username and password")
            else:
                try:
                    add_user(su_user.strip(), su_pass)
                    st.success("Account created! Please login using the left form.")
                except Exception as e:
                    st.error("Username already exists. Choose another.")

# --- Main menu UI (on main page) ---
def main_menu():
    st.subheader(f"Welcome, {st.session_state.username}!")
    # Show quick totals
    total_income, total_expense, savings = calculate_totals(st.session_state.user_id)
    st.metric("Total Income", f"₹{total_income:.2f}", delta=None)
    st.metric("Total Expense", f"₹{total_expense:.2f}", delta=None)
    st.metric("Savings", f"₹{savings:.2f}", delta=None)

    # menu buttons in a row
    c1, c2, c3, c4 = st.columns([1,1,1,1])
    if c1.button("➕ Add Income"):
        st.session_state.menu = "add_income"
    if c2.button("➖ Add Expense"):
        st.session_state.menu = "add_expense"
    if c4.button("📊 View Transactions"):
        st.session_state.menu = "view"

    st.markdown("---")

    # Menu actions
    if st.session_state.menu == "add_income":
        with st.form("form_income", clear_on_submit=True):
            amt = st.number_input("Amount", min_value=0.0, format="%.2f")
            cat = st.text_input("Category (e.g., Salary, Bonus)")
            date = st.date_input("Date (optional)")
            submitted = st.form_submit_button("Save Income")
            if submitted:
                date_str = date.isoformat() if date else None
                add_transaction(st.session_state.user_id, float(amt), cat.strip() or "income", "income", date_str)
                st.success("Income added")
    elif st.session_state.menu == "add_expense":
        with st.form("form_expense", clear_on_submit=True):
            amt = st.number_input("Amount", min_value=0.0, format="%.2f", key="exp_amt")
            cat = st.text_input("Category (e.g., Food, Rent)", key="exp_cat")
            date = st.date_input("Date (optional)", key="exp_date")
            submitted = st.form_submit_button("Save Expense")
            if submitted:
                date_str = date.isoformat() if date else None
                add_transaction(st.session_state.user_id, float(amt), cat.strip() or "others", "expense", date_str)
                st.success("Expense added")

    elif st.session_state.menu == "view":
        rows = get_transactions(st.session_state.user_id)
        if not rows:
            st.info("No transactions yet.")
        else:
            # build DataFrame
            df = pd.DataFrame(rows, columns=["id","amount","category","type","date"])
            # show summary
            total_income = df[df["type"]=="income"]["amount"].sum()
            total_expense = df[df["type"]=="expense"]["amount"].sum()
            savings = total_income - total_expense
            st.write(f"**Total Income:** ₹{total_income:.2f}   &nbsp;&nbsp; **Total Expense:** ₹{total_expense:.2f}   &nbsp;&nbsp; **Savings:** ₹{savings:.2f}")

            # show table (hide id column if you want)
            st.dataframe(df[["amount","category","type","date"]], use_container_width=True)

            # Edit/Delete controls for each row
            st.markdown("### Manage transactions")
            for r in rows:
                tid, amt, cat, ttype, date = r
                cols = st.columns([2,2,2,1,1])
                cols[0].write(f"₹{amt:.2f}")
                cols[1].write(cat)
                cols[2].write(ttype)
                # Edit button opens an in-place form:
                if cols[3].button("Edit", key=f"edit_{tid}"):
                    with st.form(f"edit_form_{tid}"):
                        new_amt = st.number_input("Amount", value=float(amt), min_value=0.0, format="%.2f", key=f"edit_amt_{tid}")
                        new_cat = st.text_input("Category", value=cat, key=f"edit_cat_{tid}")
                        new_type = st.selectbox("Type", options=["income","expense"], index=0 if ttype=="income" else 1, key=f"edit_type_{tid}")
                        new_date = st.date_input("Date", key=f"edit_date_{tid}")
                        if st.form_submit_button("Save", key=f"save_{tid}"):
                            add_date = new_date.isoformat() if new_date else None
                            update_transaction(tid, new_amt, new_cat.strip() or "others", new_type, add_date)
                            st.success("Updated")
                            st.rerun()
                if cols[4].button("Delete", key=f"del_{tid}"):
                    delete_transaction(tid)
                    st.success("Deleted")
                    st.rerun()

            # Chart: monthly income vs expense
            df["date"] = pd.to_datetime(df["date"])
            df["month"] = df["date"].dt.to_period("M").astype(str)
            monthly = df.groupby(["month", "type"])["amount"].sum().reset_index()

            if not monthly.empty:
                fig = px.pie(
                    monthly,
                    names="type",  # category (Income/Expense)
                    values="amount",  # size of slices
                    title="Monthly Income vs Expense"
                )
                st.plotly_chart(fig, use_container_width=True)

    # Logout button on main menu
    st.markdown("---")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.menu = None
        st.experimental_rerun()

# --- show auth UI if not logged in ---
if not st.session_state.logged_in:
    auth_ui()
else:
    main_menu()