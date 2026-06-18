import streamlit as st
import pandas as pd
import os
import sqlite3
import hashlib
from datetime import datetime

# --- DATABASE SETUP (For Multi-Accounts) ---
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

# Initialize Database
init_db()

st.set_page_config(page_title="Prince Hisab-Kitab Pro", layout="wide")

# --- SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# --- LOGIN / REGISTER UI ---
if not st.session_state["logged_in"]:
    st.title("🔒 PRINCE HISAB-KITAB SECURED SYSTEM")
    st.markdown("---")
    
    # Login aur Register ke liye do tabs banaye hain
    choice = st.radio("Option Chunein:", ["Login (Pehle se Account hai)", "Register (Naya Account Banayein)"], horizontal=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if choice == "Login (Pehle se Account hai)":
            st.subheader("🔑 LOGIN")
            username = st.text_input("Username / Apna Naam:")
            password = st.text_input("Password:", type="password")
            if st.button("LOGIN"):
                if login_user(username, password):
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.success(f"Welcome back, {username}! 👋")
                    st.rerun()
                else:
                    st.error("❌ Galat Username ya Password!")
                    
        elif choice == "Register (Naya Account Banayein)":
            st.subheader("📝 CREATE ACCOUNT")
            new_user = st.text_input("Naya Username Chunein:")
            new_password = st.text_input("Naya Password Banayein:", type="password")
            confirm_password = st.text_input("Password Dobara Dalein:", type="password")
            
            if st.button("REGISTER NOW"):
                if not new_user.strip() or not new_password.strip():
                    st.error("⚠️ Username aur Password khaali nahi ho sakta!")
                elif new_password != confirm_password:
                    st.error("❌ Dono Passwords match nahi kar rahe!")
                else:
                    success = add_user(new_user.strip(), new_password)
                    if success:
                        st.success("🎉 Account kamyabi se ban gaya! Ab upar 'Login' option select karke login karein.")
                    else:
                        st.error("⚠️ Ye Username pehle se kisi ne le rakha hai! Kuch naya try karein.")
                        
    st.stop() # Login hone tak aage ka code nahi chalega

# --- MAIN DASHBOARD (Sahi Login ke Baad) ---
current_user = st.session_state["username"]
st.title(f"🏠 PRINCE GHAR KA HISAB-KITAB ({current_user.upper()})")

# Har user ki apni alag CSV file banegi
USER_DATA_FILE = os.path.join(DATA_FOLDER, f"hisab_{current_user}.csv")

if not os.path.exists(USER_DATA_FILE):
    df = pd.DataFrame(columns=["Date", "Type", "Category", "Amount"])
    df.to_csv(USER_DATA_FILE, index=False)

# --- DATA ENTRY FORM (SIDEBAR) ---
st.sidebar.header(f"👤 Account: {current_user}")
with st.sidebar.form("entry_form", clear_on_submit=True):
    date_input = st.date_input("Tarikh Chunein", datetime.now())
    type_input = st.selectbox("Type", ["Expense (Kharcha)", "Income (Kamai)"])
    category_input = st.text_input("Category / Kharch ya Kamai ka Naam", placeholder="e.g., Diesel, Narma Kamai, Kirana")
    amount_input = st.number_input("Amount (Rupees)", min_value=1, step=1)
    submit_btn = st.form_submit_button("SAVE HISAB")

if submit_btn:
    if category_input.strip() == "":
        st.sidebar.error("⚠️ Kripya Category ka naam zaroor likhein!")
    else:
        clean_category = category_input.strip().title()
        new_data = pd.DataFrame([[date_input, type_input, clean_category, amount_input]], 
                                columns=["Date", "Type", "Category", "Amount"])
        new_data.to_csv(USER_DATA_FILE, mode='a', header=False, index=False)
        st.success(f"'{clean_category}' ka hisab save ho gaya! 🚀")

# --- DATA PROCESSING & DASHBOARD ---
df_load = pd.read_csv(USER_DATA_FILE)

if not df_load.empty:
    df_load["Date"] = pd.to_datetime(df_load["Date"])
    df_load["Month"] = df_load["Date"].dt.strftime('%B %Y')
    
    all_months = df_load["Month"].unique()
    selected_month = st.selectbox("📅 Mahina Chunein:", all_months)
    
    df_filtered = df_load[df_load["Month"] == selected_month]
    
    inc = df_filtered[df_filtered["Type"] == "Income (Kamai)"]["Amount"].sum()
    exp = df_filtered[df_filtered["Type"] == "Expense (Kharcha)"]["Amount"].sum()
    bal = inc - exp
    
    # Dashboard Cards
    col1, col2, col3 = st.columns(3)
    col1.metric("🟩 KUL KAMAI (INCOME)", f"₹{inc:,}")
    col2.metric("🟥 KUL KHARCHA (EXPENSE)", f"₹{exp:,}")
    col3.metric("🟦 NET BALANCE (SAVINGS)", f"₹{bal:,}")
    
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("📊 Is Mahine ka Len-Den")
        st.dataframe(df_filtered[["Date", "Type", "Category", "Amount"]].sort_values(by="Date", ascending=False), use_container_width=True)
        
    with col_right:
        st.subheader("🍕 Kharchon ka Hisab")
        exp_df = df_filtered[df_filtered["Type"] == "Expense (Kharcha)"]
        if not exp_df.empty:
            cat_totals = exp_df.groupby("Category")["Amount"].sum()
            st.pie_chart(cat_totals)
        else:
            st.info("Is mahine koi kharcha nahi hai.")
else:
    st.info("Abhi koi data nahi hai. Sidebar se entry karein!")

# --- LOGOUT BUTTON ---
if st.sidebar.button("🔒 LOGOUT"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.rerun()
    