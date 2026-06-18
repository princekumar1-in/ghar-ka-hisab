import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import re
import io
from datetime import datetime, timedelta

# --- PRODUCTION STORAGE CORE ---
STABLE_DB_CORE = "ledger_system_secure_v3.db"

def init_db_safely():
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    # Updated Schema with payment_method and notes
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, account_mode TEXT, created_by TEXT,
                  sec_question TEXT, sec_answer TEXT, two_fa_pin TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, date TEXT, type TEXT, 
                  category TEXT, amount REAL, payment_method TEXT, notes TEXT, log_status TEXT)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def is_password_strong(password):
    if len(password) < 8: return False, "Password must be at least 8 characters."
    if not re.search(r"[a-z]", password): return False, "Must contain a lowercase letter."
    if not re.search(r"[A-Z]", password): return False, "Must contain an uppercase letter."
    if not re.search(r"[0-9]", password): return False, "Must contain a number."
    return True, "Strong Password"

def add_user(username, password, account_mode, created_by="self"):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, account_mode, created_by) VALUES (?,?,?,?)', 
                  (username, make_hashes(password), account_mode, created_by))
        conn.commit()
        return True
    except sqlite3.IntegrityError: return False
    finally: conn.close()

def login_user(username, password):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT password, account_mode FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    if data: return hashlib.sha256(str.encode(password)).hexdigest() == data[0], data[1]
    return False, None

def check_user_security_setup(username):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT sec_question, two_fa_pin FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data and data[0] is not None and data[1] is not None

def save_security_setup(username, sec_q, sec_a, two_fa):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('UPDATE users SET sec_question=?, sec_answer=?, two_fa_pin=? WHERE username=?',
              (sec_q, make_hashes(sec_a.strip().lower()), make_hashes(two_fa), username))
    conn.commit()
    conn.close()

def user_exists(username):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data is not None

def get_user_question(username):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT sec_question FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data[0] if data else None

def verify_security_answer(username, answer):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT sec_answer FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data and data[0] == make_hashes(answer.strip().lower())

def update_user_password(username, new_password):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('UPDATE users SET password = ? WHERE username = ?', (make_hashes(new_password), username))
    conn.commit()
    conn.close()

def get_sub_accounts(admin_username):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE created_by = ?', (admin_username,))
    data = c.fetchall()
    conn.close()
    return [row[0] for row in data]

def save_transaction(username, date, t_type, category, amount, payment_method, notes, log_status):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('''INSERT INTO transactions(username, date, type, category, amount, payment_method, notes, log_status) 
                 VALUES (?,?,?,?,?,?,?,?)''', (username, date, t_type, category, amount, payment_method, notes, log_status))
    conn.commit()
    conn.close()

def get_user_transactions(username):
    conn = sqlite3.connect(STABLE_DB_CORE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, date, type, category, amount, payment_method, notes, log_status FROM transactions WHERE username = ?', (username,))
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["id", "date", "type", "category", "amount", "payment_method", "notes", "log_status"])

def update_transaction(t_id, date, t_type, category, amount, payment_method, notes, log_status="Edited"):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('UPDATE transactions SET date=?, type=?, category=?, amount=?, payment_method=?, notes=?, log_status=? WHERE id=?', 
              (date, t_type, category, amount, payment_method, notes, log_status, t_id))
    conn.commit()
    conn.close()

def delete_transaction(t_id):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('DELETE FROM transactions WHERE id = ?', (t_id,))
    conn.commit()
    conn.close()

init_db_safely()

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(page_title="Professional Financial Ledger", layout="wide", page_icon="💰")

# --- HIGH INTENSITY HARDCORE FOOTER WIPE OUT CSS ---
st.markdown("""
    <style>
    header, footer, .stDecoration, [data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
    #MainMenu, .stAppDeployDropdown, button[title="View source code"] { display: none !important; }
    .stApp { padding-bottom: 0px !important; }
    div[class*="viewerBadge"] { display: none !important; visibility: hidden !important; }
    footer a, [class^="viewerBadge_"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# Cookie Engine Fallback Mock for Device Trust Persistence
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "two_fa_verified" not in st.session_state: st.session_state["two_fa_verified"] = False
if "username" not in st.session_state: st.session_state["username"] = ""
if "account_mode" not in st.session_state: st.session_state["account_mode"] = "Single"

# Core Local Storage Cookie Bypass simulation via runtime parameters
if "trusted_device_token" not in st.session_state:
    st.session_state["trusted_device_token"] = {}

# --- PHASE 1: LOGIN ENVIRONMENT ---
if not st.session_state["logged_in"]:
    st.title("🔒 SECURED LEDGER SYSTEM")
    st.markdown("---")
    auth_choice = st.radio("Select Action:", ["Sign In", "Create Master Account", "Forget Password"], horizontal=True)
    col1, _ = st.columns([1, 2])
    
    with col1:
        if auth_choice == "Sign In":
            st.subheader("🔑 Sign In")
            username_input = st.text_input("Username:").strip().lower()
            password_input = st.text_input("Password:", type="password")
            if st.button("SIGN IN", use_container_width=True):
                success, mode = login_user(username_input, password_input)
                if success:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username_input
                    st.session_state["account_mode"] = mode
                    
                    # Cookie Check Engine: Agar token validated hai aur expired nahi hua toh bypass 2FA
                    if username_input in st.session_state["trusted_device_token"]:
                        if datetime.now() < st.session_state["trusted_device_token"][username_input]:
                            st.session_state["two_fa_verified"] = True
                    st.rerun()
                else: st.error("Invalid credentials.")
        
        elif auth_choice == "Create Master Account":
            st.subheader("📝 Register Master Admin")
            new_user = st.text_input("Choose Username:").strip().lower()
            new_password = st.text_input("Create Password:", type="password")
            mode_selection = st.selectbox("Usage Mode:", ["Single User Mode", "Multiple Accounts Mode (Family)"])
            selected_mode = "Single" if "Single" in mode_selection else "Multiple"
            if st.button("REGISTER NOW", use_container_width=True):
                is_strong, msg = is_password_strong(new_password)
                if not new_user or not new_password: st.error("Fields cannot be empty!")
                elif not is_strong: st.error(msg)
                elif add_user(new_user, new_password, selected_mode): st.success("Account created! Switch to Sign In.")
                else: st.error("Username already taken!")
                
        elif auth_choice == "Forget Password":
            st.subheader("🔄 Reset Password")
            reset_user = st.text_input("Enter Username:").strip().lower()
            if reset_user and user_exists(reset_user):
                q = get_user_question(reset_user)
                if not q: st.error("Security questions not configured.")
                else:
                    st.info(f"**Question:** {q}")
                    ans = st.text_input("Answer:", type="password")
                    np = st.text_input("New Password:", type="password")
                    if st.button("RESET PASSWORD", use_container_width=True):
                        if verify_security_answer(reset_user, ans):
                            update_user_password(reset_user, np)
                            st.success("Password updated!")
                        else: st.error("Incorrect answer!")
    st.stop()

# --- PHASE 2: SECURITY SETUP & COOKIE VERIFICATION GATEWAY ---
current_user = st.session_state["username"]
user_mode = st.session_state["account_mode"]

if not check_user_security_setup(current_user):
    st.title("🛡️ INITIAL SECURITY CONFIGURATION")
    col_setup, _ = st.columns([1, 2])
    with col_setup:
        chosen_q = st.selectbox("Choose Recovery Question:", ["What is the name of your first school?", "What was the name of your first pet?", "In which city were you born?"])
        answer_q = st.text_input("Secret Answer:", type="password")
        two_fa_code = st.text_input("Create 2-Step PIN (Numeric):", type="password", max_chars=6)
        if st.button("SAVE PROTOCOLS", use_container_width=True):
            if not answer_q or not two_fa_code or not two_fa_code.isdigit(): st.error("Valid inputs required!")
            else:
                save_security_setup(current_user, chosen_q, answer_q, two_fa_code)
                st.session_state["two_fa_verified"] = True
                st.rerun()
    st.stop()

# 2FA GATEWAY INTERACTION
if not st.session_state["two_fa_verified"]:
    st.title("🛡️ 2-STEP VERIFICATION GATEWAY")
    col_2fa, _ = st.columns([1, 2])
    with col_2fa:
        pin_entry = st.text_input("Enter Your 2-Step PIN:", type="password", max_chars=6)
        trust_device = st.checkbox("Keep me logged in on this device for 3 days")
        if st.button("VERIFY SECURE PIN", use_container_width=True):
            conn = sqlite3.connect(STABLE_DB_CORE)
            c = conn.cursor()
            c.execute('SELECT two_fa_pin FROM users WHERE username = ?', (current_user,))
            db_pin = c.fetchone()[0]
            conn.close()
            if make_hashes(pin_entry) == db_pin:
                st.session_state["two_fa_verified"] = True
                if trust_device:
                    # Persistent Simulation Engine: Token validated up to 3 Days inside Cookie runtime tracking
                    st.session_state["trusted_device_token"][current_user] = datetime.now() + timedelta(days=3)
                st.rerun()
            else: st.error("Invalid Security Verification PIN!")
    st.stop()

# --- PHASE 3: LIVE DASHBOARD & EXCEL BACKUP ENGINE ---
st.title("📊 FINANCIAL LEDGER ARCHITECTURE")
st.markdown(f"*Secure Session Active: **{current_user.upper()}***")

# EXCEL BACKUP GENERATION UTILITY BUTTON
df_all_backup = get_user_transactions(current_user)
if not df_all_backup.empty:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_all_backup.to_excel(writer, index=False, sheet_name='Ledger Backup')
    buffer.seek(0)
    st.download_button(
        label="📥 DOWNLOAD WHOLE DATA TO EXCEL (.XLSX)",
        data=buffer,
        file_name=f"ledger_backup_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )

st.markdown("---")

# --- TRANSACTION ENTRY FORM WITH CASH/BANK & NOTES ---
st.markdown("### 📝 Log New Transaction Entry")
with st.form("entry_form", clear_on_submit=True):
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        date_input = st.date_input("Transaction Date", datetime.now())
        type_input = st.selectbox("Accounting Type", ["Expense", "Income"])
        payment_method = st.selectbox("Payment Method Designation", ["Cash", "Bank (Online/UPI)"])
    with f_col2:
        category_input = st.text_input("Category / Particulars Label") 
        amount_input = st.number_input("Amount (INR)", min_value=1.0, step=1.0)
        notes_input = st.text_area("Add Custom Description / Note (Wajah)", value="", help="Yahan entry ka kaaran likhein")
        
    submit_btn = st.form_submit_button("COMMIT SECURE TRANSACTION RECORD", use_container_width=True)

if submit_btn:
    if not category_input.strip(): st.error("Valid designation required.")
    else:
        today_str = datetime.now().strftime('%Y-%m-%d')
        selected_date_str = date_input.strftime('%Y-%m-%d')
        status_tag = "Auto" if today_str == selected_date_str else "Edited"
        save_transaction(current_user, selected_date_str, type_input, category_input.strip().title(), amount_input, payment_method, notes_input.strip(), status_tag)
        st.toast("Transaction logged permanently!", icon="✅")
        st.rerun()

st.markdown("---")

# --- RENDER DATABASE VIEWS ---
df_user = get_user_transactions(current_user)

if not df_user.empty:
    df_user["date"] = pd.to_datetime(df_user["date"])
    df_user["Month"] = df_user["date"].dt.strftime('%B %Y')
    selected_month = st.selectbox("Select Display Billing Month Selector:", df_user["Month"].unique())
    
    df_filtered = df_user[df_user["Month"] == selected_month].copy()
    
    # Financial Stats Metric Rows
    inc = df_filtered[df_filtered["type"] == "Income"]["amount"].sum()
    exp = df_filtered[df_filtered["type"] == "Expense"]["amount"].sum()
    st.columns(3)[0].metric("🟩 TOTAL INCOME", f"₹{inc:,}")
    st.columns(3)[1].metric("🟥 TOTAL EXPENSE", f"₹{exp:,}")
    st.columns(3)[2].metric("🟦 NET BALANCE", f"₹{(inc-exp):,}")
    
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("📝 Statement Ledger Records")
        for idx, row in df_filtered.sort_values(by="date", ascending=False).iterrows():
            tag = "🟢" if row['type'] == "Income" else "🟥"
            method_badge = "🏪 Cash" if row['payment_method'] == "Cash" else "🏦 Bank"
            
            st.markdown(f"""
            {tag} **{row['date'].strftime('%Y-%m-%d')}** | **{row['category']}** | **Method:** `{method_badge}` | **Amount:** `₹{row['amount']:,}` *[{row['log_status']}]*
            """)
            
            # HIDDEN NOTE CONTAINER ICON LOGIC
            note_text = row['notes'] if row['notes'] else "No special remarks added."
            with st.expander("📝 View Entry Secret Note / Karan"):
                st.caption(f"**Description:** {note_text}")
                
            edit_col, delete_col = st.columns(2)
            with edit_col:
                if st.button("✏️ Edit Entry Tokens", key=f"ed_{row['id']}", use_container_width=True):
                    st.session_state[f"show_edit_{row['id']}"] = True
            with delete_col:
                if st.button("🗑️ Wipe Out Record", key=f"del_{row['id']}", type="primary", use_container_width=True):
                    delete_transaction(row['id'])
                    st.toast("Entry wiped out!")
                    st.rerun()
                    
            if f"show_edit_{row['id']}" in st.session_state and st.session_state[f"show_edit_{row['id']}"]:
                with st.expander("🛠️ Update Row Parameters", expanded=True):
                    e_cat = st.text_input("Edit Category:", value=row['category'], key=f"e_cat_{row['id']}")
                    e_amt = st.number_input("Edit Amount:", value=float(row['amount']), key=f"e_amt_{row['id']}")
                    e_type = st.selectbox("Edit Type:", ["Expense", "Income"], index=0 if row['type']=="Expense" else 1, key=f"e_ty_{row['id']}")
                    e_meth = st.selectbox("Edit Method:", ["Cash", "Bank (Online/UPI)"], index=0 if row['payment_method']=="Cash" else 1, key=f"e_me_{row['id']}")
                    e_note = st.text_area("Edit Note:", value=row['notes'], key=f"e_no_{row['id']}")
                    
                    if st.button("Save Row Modifications", key=f"sv_{row['id']}"):
                        update_transaction(row['id'], row['date'].strftime('%Y-%m-%d'), e_type, e_cat.title(), e_amt, e_meth, e_note, "Edited")
                        st.session_state[f"show_edit_{row['id']}"] = False
                        st.rerun()
            st.markdown("<hr style='margin:0.8em 0; border-color:#333;' />", unsafe_allow_html=True)
            
    with col_right:
        st.subheader("📊 Expense Chart Metric Matrix")
        exp_df = df_filtered[df_filtered["type"] == "Expense"]
        if not exp_df.empty:
            st.bar_chart(data=exp_df.groupby("category")["amount"].sum().reset_index(), x="category", y="amount", color="#ff4b4b", use_container_width=True)
else:
    st.info("No records inside your dashboard dashboard matrix yet.")

st.markdown("---")
if st.button("🔒 SECURE CONNECTION TERMINATION SIGN OUT", use_container_width=True, type="primary"):
    st.session_state["logged_in"] = False
    st.session_state["two_fa_verified"] = False
    st.rerun()
