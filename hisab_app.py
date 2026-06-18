import streamlit as st
import pandas as pd
import os
import sqlite3
import hashlib
from datetime import datetime

# --- DATABASE SETUP ---
DB_FILE = "users_db.db"
DATA_FOLDER = "User_Data"

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_password):
    if make_hashes(password) == hashed_password:
        return True
    return False

def add_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, make_hashes(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    if data:
        return check_hashes(password, data[0])
    return False

init_db()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Personal Ledger Pro", layout="wide", page_icon="💰")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# --- AUTHENTICATION UI ---
if not st.session_state["logged_in"]:
    st.title("🔒 SECURED LEDGER SYSTEM")
    st.markdown("---")
    
    auth_choice = st.radio("Select Action:", ["Sign In", "Create Account"], horizontal=True)
    
    col1, _ = st.columns([1, 2])
    
    with col1:
        if auth_choice == "Sign In":
            st.subheader("🔑 Sign In")
            username = st.text_input("Username:").strip()
            password = st.text_input("Password:", type="password")
            if st.button("SIGN IN", use_container_width=True):
                if login_user(username, password):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.toast(f"Welcome back! 👋")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
                    
        elif auth_choice == "Create Account":
            st.subheader("📝 Register New Account")
            new_user = st.text_input("Choose Username:").strip()
            new_password = st.text_input("Create Password:", type="password")
            confirm_password = st.text_input("Confirm Password:", type="password")
            
            if st.button("REGISTER NOW", use_container_width=True):
                if not new_user or not new_password:
                    st.error("Fields cannot be empty!")
                elif new_password != confirm_password:
                    st.error("Passwords do not match!")
                else:
                    if add_user(new_user, new_password):
                        st.success("Account created successfully! Please switch to 'Sign In' tab.")
                    else:
                        st.error("Username already exists! Choose another.")
                        
    st.stop()

# --- MAIN APP LOGIC ---
current_user = st.session_state["username"]
st.title(f"📊 FINANCIAL DASHBOARD")

USER_DATA_FILE = os.path.join(DATA_FOLDER, f"ledger_{current_user}.csv")

if not os.path.exists(USER_DATA_FILE):
    df = pd.DataFrame(columns=["Date", "Type", "Category", "Amount"])
    df.to_csv(USER_DATA_FILE, index=False)

# --- SIDEBAR: ENTRY FORM ---
st.sidebar.subheader(f"👤 Active User: {current_user.title()}")
with st.sidebar.form("entry_form", clear_on_submit=True):
    date_input = st.date_input("Transaction Date", datetime.now())
    type_input = st.selectbox("Transaction Type", ["Expense", "Income"])
    category_input = st.text_input("Category / Particulars", placeholder="e.g., Fuel, Market, Seeds")
    amount_input = st.number_input("Amount (INR)", min_value=1, step=1)
    submit_btn = st.form_submit_button("SAVE TRANSACTION", use_container_width=True)

if submit_btn:
    if not category_input.strip():
        st.sidebar.error("Please enter a valid category name!")
    else:
        clean_category = category_input.strip().title()
        new_data = pd.DataFrame([[date_input, type_input, clean_category, amount_input]], 
                                columns=["Date", "Type", "Category", "Amount"])
        new_data.to_csv(USER_DATA_FILE, mode='a', header=False, index=False)
        st.toast(f"Saved: {clean_category} - ₹{amount_input}", icon="✅")
        st.rerun()

# --- MAIN DASHBOARD DATA ---
df_load = pd.read_csv(USER_DATA_FILE)

if not df_load.empty:
    df_load["Date"] = pd.to_datetime(df_load["Date"])
    df_load["Month"] = df_load["Date"].dt.strftime('%B %Y')
    
    all_months = df_load["Month"].unique()
    selected_month = st.selectbox("📅 Select Billing Month:", all_months)
    
    df_filtered = df_load[df_load["Month"] == selected_month].copy()
    
    # Calculations
    total_income = df_filtered[df_filtered["Type"] == "Income"]["Amount"].sum()
    total_expense = df_filtered[df_filtered["Type"] == "Expense"]["Amount"].sum()
    net_balance = total_income - total_expense
    
    # --- METRIC CARDS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("🟩 TOTAL INCOME", f"₹{total_income:,}")
    col2.metric("🟥 TOTAL EXPENSE", f"₹{total_expense:,}")
    col3.metric("🟦 NET SAVINGS", f"₹{net_balance:,}")
    
    st.markdown("---")
    
    # --- DATA TABLES & CHARTS ---
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📝 Monthly Statements")
        df_display = df_filtered[["Date", "Type", "Category", "Amount"]].copy()
        df_display["Date"] = df_display["Date"].dt.strftime('%Y-%m-%d')
        st.dataframe(df_display.sort_values(by="Date", ascending=False), use_container_width=True, hide_index=True)
        
    with col_right:
        st.subheader("🍩 Expense Distribution")
        exp_df = df_filtered[df_filtered["Type"] == "Expense"]
        if not exp_df.empty:
            cat_totals = exp_df.groupby("Category")["Amount"].sum().reset_index()
            st.bar_chart(data=cat_totals, x="Category", y="Amount", color="#ff4b4b", use_container_width=True)
        else:
            st.info("No expenses recorded for this month.")
else:
    st.info("No historical data available. Use the sidebar menu to log your first transaction.")

# --- LOGOUT BUTTON ---
st.sidebar.markdown("---")
if st.sidebar.button("🔒 SECURE LOGOUT", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.rerun()
