import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import re
import time
from datetime import datetime, timedelta

# --- PRODUCTION STORAGE ---
STABLE_DB_CORE = "ledger_system_secure_v2.db"

def init_db_safely():
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    # Users Table upgraded with security answers, 2FA pins, and account modes
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, account_mode TEXT, created_by TEXT,
                  sec_question TEXT, sec_answer TEXT, two_fa_pin TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, date TEXT, type TEXT, category TEXT, amount REAL, log_status TEXT)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Strict Password Validation Mix Policy
def is_password_strong(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[@_!#$%^&*()<>?/\|}{~:]", password):
        return False, "Password must contain at least one special character (e.g. @, #, $)."
    return True, "Strong Password"

def add_user(username, password, account_mode, sec_q, sec_a, two_fa, created_by="self"):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO users(username, password, account_mode, created_by, sec_question, sec_answer, two_fa_pin) 
                     VALUES (?,?,?,?,?,?,?)''', 
                  (username, make_hashes(password), account_mode, created_by, sec_q, make_hashes(sec_a.strip().lower()), make_hashes(two_fa)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT password, account_mode, two_fa_pin FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    if data:
        return hashlib.sha256(str.encode(password)).hexdigest() == data[0], data[1], data[2]
    return False, None, None

def user_exists(username):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data is not None

def verify_security_answer(username, answer):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT sec_answer FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    if data:
        return make_hashes(answer.strip().lower()) == data[0]
    return False

def get_user_question(username):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT sec_question FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data[0] if data else None

def update_user_password(username, new_password):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('UPDATE users SET password = ? WHERE username = ?', (make_hashes(new_password), username))
    conn.commit()
    conn.close()

def update_user_2fa(username, new_2fa):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('UPDATE users SET two_fa_pin = ? WHERE username = ?', (make_hashes(new_2fa), username))
    conn.commit()
    conn.close()

def delete_user_account(username):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE username = ?', (username,))
    c.execute('DELETE FROM transactions WHERE username = ?', (username,))
    conn.commit()
    conn.close()

def get_sub_accounts(admin_username):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE created_by = ?', (admin_username,))
    data = c.fetchall()
    conn.close()
    return [row[0] for row in data]

def save_transaction(username, date, t_type, category, amount, log_status):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('INSERT INTO transactions(username, date, type, category, amount, log_status) VALUES (?,?,?,?,?,?)',
              (username, date, t_type, category, amount, log_status))
    conn.commit()
    conn.close()

def get_user_transactions(username):
    conn = sqlite3.connect(STABLE_DB_CORE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, date, type, category, amount, log_status FROM transactions WHERE username = ?', (username,))
    rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["id", "date", "type", "category", "amount", "log_status"])

def update_transaction(t_id, date, t_type, category, amount, log_status="Edited"):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('UPDATE transactions SET date=?, type=?, category=?, amount=?, log_status=? WHERE id=?', 
              (date, t_type, category, amount, log_status, t_id))
    conn.commit()
    conn.close()

def delete_transaction(t_id):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('DELETE FROM transactions WHERE id = ?', (t_id,))
    conn.commit()
    conn.close()

def get_global_summary_for_admin(admin_username):
    subs = get_sub_accounts(admin_username)
    combined_users = list(subs)
    combined_users.append(admin_username)
    conn = sqlite3.connect(STABLE_DB_CORE)
    placeholders = ','.join('?' for _ in combined_users)
    try:
        query = f'SELECT type, amount FROM transactions WHERE username IN ({placeholders})'
        df = pd.read_sql_query(query, conn, params=combined_users)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    if df.empty:
        return 0, 0, 0
    inc = df[df["type"] == "Income"]["amount"].sum()
    exp = df[df["type"] == "Expense"]["amount"].sum()
    return inc, exp, (inc - exp)

init_db_safely()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Professional Ledger System", layout="wide", page_icon="💰")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    stDecoration {display:none !important;}
    [data-testid="stStatusWidget"] {display:none !important;}
    button[title="View source code"] {display: none !important;}
    .stAppDeployDropdown {display: none !important;}
    iframe[title="Manage app"] {display: none !important;}
    div[data-testid="stConnectionStatus"] {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

MY_EMAIL = "vermaji3216@gmail.com"

# Session Keys Initialization
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "two_fa_verified" not in st.session_state:
    st.session_state["two_fa_verified"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "account_mode" not in st.session_state:
    st.session_state["account_mode"] = "Single"

# SECURITY QUESTIONS POOL
SECURITY_QUESTIONS = [
    "What is the name of your first school?",
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "In which city or town were you born?"
]

# --- PHASE 1: LOGIN / AUTH CONTROL PANEL ---
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
                success, mode, hashed_pin = login_user(username_input, password_input)
                if success:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username_input
                    st.session_state["account_mode"] = mode
                    
                    # 3-Day device session logic checkpoint
                    session_key = f"expiry_{username_input}"
                    if session_key in st.sidebar.get_all_query_params or (session_key in st.session_state and st.session_state[session_key] > datetime.now()):
                        st.session_state["two_fa_verified"] = True
                    else:
                        st.session_state["two_fa_verified"] = False
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
                    
        elif auth_choice == "Create Master Account":
            st.subheader("📝 Register Master Admin")
            new_user = st.text_input("Choose Unique Username:").strip().lower()
            new_password = st.text_input("Create Strong Password:", type="password", help="Min 8 letters mixed with Uppercase, Numbers & Special symbols")
            
            st.markdown("---")
            st.markdown("**🛡️ Setup Security Recovery Protocol**")
            chosen_q = st.selectbox("Select a Security Question:", SECURITY_QUESTIONS)
            answer_q = st.text_input("Your Secret Answer:", type="password")
            
            st.markdown("---")
            st.markdown("**📱 Setup 2-Step Verification**")
            two_fa_code = st.text_input("Create 6-Digit 2-Step PIN:", type="password", max_chars=6)
            
            mode_selection = st.selectbox("Account Usage Mode:", ["Single User Mode", "Multiple Accounts Mode (Family/Team)"])
            selected_mode = "Single" if "Single" in mode_selection else "Multiple"
            
            if st.button("REGISTER SECURE SYSTEM", use_container_width=True):
                is_strong, pass_msg = is_password_strong(new_password)
                if not new_user or not new_password or not answer_q or not two_fa_code:
                    st.error("All parameters are mandatory!")
                elif not is_strong:
                    st.error(pass_msg)
                elif not two_fa_code.isdigit() or len(two_fa_code) < 4:
                    st.error("2-Step Verification code must be a secure numeric PIN!")
                else:
                    if add_user(new_user, new_password, selected_mode, chosen_q, answer_q, two_fa_code, "self"):
                        st.success("Master network safe node deployed! Click 'Sign In' above.")
                    else:
                        st.error("This Username is already taken! Try another one.")
                        
        elif auth_choice == "Forget Password":
            st.subheader("🔄 Emergency Password Reset")
            reset_user = st.text_input("Enter Registered Username:").strip().lower()
            
            if reset_user and user_exists(reset_user):
                assigned_q = get_user_question(reset_user)
                st.info(f"**Security Question:** {assigned_q}")
                user_ans = st.text_input("Provide Your Secret Answer:", type="password")
                st.markdown("---")
                new_reset_pass = st.text_input("New Strong Password:", type="password")
                confirm_reset_pass = st.text_input("Confirm New Password:", type="password")
                
                if st.button("RESET SECURE SYSTEM PASSWORD", use_container_width=True):
                    is_strong, pass_msg = is_password_strong(new_reset_pass)
                    if not user_ans or not new_reset_pass:
                        st.error("Input tokens are required.")
                    elif new_reset_pass != confirm_reset_pass:
                        st.error("Passwords mismatch!")
                    elif not is_strong:
                        st.error(pass_msg)
                    elif verify_security_answer(reset_user, user_ans):
                        update_user_password(reset_user, new_reset_pass)
                        st.success("Password reset complete! Go to 'Sign In' tab.")
                    else:
                        st.error("Security answer validation failed!")
            elif reset_user:
                st.error("Username index path not found.")
                
    st.markdown("---")
    with st.expander("📧 Need Help / Report Problem?"):
        email_url = f"mailto:{MY_EMAIL}?subject=Ledger%20App%20Support%20Request"
        st.link_button("📧 Send Email Support", email_url, use_container_width=True, type="secondary")
    st.stop()

# --- PHASE 2: TWO-FACTOR (2-STEP) VALIDATION GATEWAY ---
current_user = st.session_state["username"]
user_mode = st.session_state["account_mode"]

if not st.session_state["two_fa_verified"]:
    st.title("🛡️ 2-STEP VERIFICATION GATEWAY")
    st.subheader(f"Account: {current_user.upper()}")
    st.markdown("This device session requires a 2-Step validation token checkpoint pass.")
    
    col_2fa, _ = st.columns([1, 2])
    with col_2fa:
        pin_entry = st.text_input("Enter 6-Digit Secondary Pin:", type="password", max_chars=6)
        trust_device = st.checkbox("Keep me logged in on this device for 3 days")
        
        if st.button("VERIFY SECURE NODE", use_container_width=True):
            conn = sqlite3.connect(STABLE_DB_CORE)
            c = conn.cursor()
            c.execute('SELECT two_fa_pin FROM users WHERE username = ?', (current_user,))
            db_pin = c.fetchone()[0]
            conn.close()
            
            if make_hashes(pin_entry) == db_pin:
                st.session_state["two_fa_verified"] = True
                if trust_device:
                    # Session expires perfectly in 3 days frame
                    st.session_state[f"expiry_{current_user}"] = datetime.now() + timedelta(days=3)
                st.toast("Security Clearance Granted!")
                st.rerun()
            else:
                st.error("Invalid Security Verification Pin!")
                
    st.markdown("---")
    if st.button("🔒 Cancel Sign In & Exit"):
        st.session_state["logged_in"] = False
        st.rerun()
    st.stop()

# --- PHASE 3: LIVE SECURE ARCHITECTURE MAIN ENVIRONMENT ---
st.title("📊 FINANCIAL LEDGER ARCHITECTURE")
st.markdown(f"*Secure Session Active: **{current_user.upper()}** ({user_mode} Mode)*")

st.sidebar.subheader("👤 Dashboard Controller")

# Account settings with mandatory security question validation checks
with st.sidebar.expander("⚙️ Account Settings"):
    st.markdown("**Security Authentication**")
    auth_ans = st.text_input("Verify Secret Recovery Answer First:", type="password", key="sett_ans_check")
    
    st.markdown("---")
    st.markdown("**Modify Credentials**")
    settings_new_pass = st.text_input("New Strong Password:", type="password", key="settings_p")
    if st.button("Update System Password", use_container_width=True):
        is_strong, pass_msg = is_password_strong(settings_new_pass)
        if not verify_security_answer(current_user, auth_ans):
            st.error("Incorrect Secret Recovery Answer!")
        elif not is_strong:
            st.error(pass_msg)
        else:
            update_user_password(current_user, settings_new_pass)
            st.success("Password updated!")
            
    st.markdown("---")
    st.markdown("**Modify 2-Step Code**")
    settings_new_2fa = st.text_input("New 2-Step PIN:", type="password", max_chars=6, key="settings_2fa")
    if st.button("Update 2-Step PIN", use_container_width=True):
        if not verify_security_answer(current_user, auth_ans):
            st.error("Incorrect Secret Recovery Answer!")
        elif not settings_new_2fa.isdigit() or len(settings_new_2fa) < 4:
            st.error("Provide a valid secondary numerical pin structure.")
        else:
            update_user_2fa(current_user, settings_new_2fa)
            st.success("2-Step Code Changed!")

    st.markdown("---")
    st.markdown("**Danger Zone**")
    if st.button("❗ TERMINATE SYSTEM CORE", type="primary", use_container_width=True):
        if verify_security_answer(current_user, auth_ans):
            delete_user_account(current_user)
            st.session_state["logged_in"] = False
            st.session_state["two_fa_verified"] = False
            st.rerun()
        else:
            st.error("Security answer mismatch block triggered!")

member_list = []
if user_mode == "Multiple":
    st.sidebar.markdown("---")
    st.sidebar.markdown("**👥 Manage Family Accounts**")
    
    with st.sidebar.expander("➕ Add Family Member"):
        sub_name = st.text_input("Member Username:").strip().lower()
        sub_pass = st.text_input("Member Password:", type="password")
        
        st.markdown("<small>Member Security Presets</small>", unsafe_allow_html=True)
        sub_q = st.selectbox("Member recovery question:", SECURITY_QUESTIONS, key="sub_q_reg")
        sub_a = st.text_input("Member secret answer:", type="password", key="sub_a_reg")
        sub_pin = st.text_input("Member 2-Step PIN:", type="password", max_chars=6, key="sub_p_reg")
        
        if st.button("Create Member Account"):
            is_strong, pass_msg = is_password_strong(sub_pass)
            if sub_name and sub_pass and sub_a and sub_pin:
                if not is_strong:
                    st.error(pass_msg)
                elif add_user(sub_name, sub_pass, "Single", sub_q, sub_a, sub_pin, current_user):
                    st.success(f"Account for '{sub_name}' active!")
                    st.rerun()
                else:
                    st.error("Member name already exists.")
            else:
                st.error("All parameters are required!")
                    
    member_list = get_sub_accounts(current_user)
    if member_list:
        with st.sidebar.expander("🗑️ Delete Member Account"):
            to_delete = st.selectbox("Select Account:", member_list)
            if st.button("CONFIRM DELETE ACCOUNT", type="primary"):
                delete_user_account(to_delete)
                st.success("Account wiped out!")
                st.rerun()

# --- ENTRY FORM ---
st.sidebar.markdown("---")
st.sidebar.markdown("**📝 Log New Entry**")
with st.sidebar.form("entry_form", clear_on_submit=True):
    date_input = st.date_input("Transaction Date", datetime.now())
    type_input = st.selectbox("Type", ["Expense", "Income"])
    category_input = st.text_input("Category / Particulars", value="") 
    amount_input = st.number_input("Amount (INR)", min_value=1.0, step=1.0)
    submit_btn = st.form_submit_button("COMMIT TRANSACTION", use_container_width=True)

if submit_btn:
    if not category_input.strip():
        st.sidebar.error("Valid label designation required.")
    else:
        today_str = datetime.now().strftime('%Y-%m-%d')
        selected_date_str = date_input.strftime('%Y-%m-%d')
        status_tag = "Auto" if today_str == selected_date_str else "Edited"
        
        save_transaction(current_user, selected_date_str, type_input, category_input.strip().title(), amount_input, status_tag)
        st.toast(f"Logged permanently as [{status_tag}]!", icon="✅")
        st.rerun()

# --- RENDER DATA VISUALIZATIONS ---
if user_mode == "Multiple":
    st.subheader("🌐 Consolidated Family Network Balance (Admin Summary view)")
    g_inc, g_exp, g_bal = get_global_summary_for_admin(current_user)
    g_col1, g_col2, g_col3 = st.columns(3)
    g_col1.metric("🌍 TOTAL COMBINED REVENUE", f"₹{g_inc:,}")
    g_col2.metric("🛑 TOTAL COMBINED OUTFLOW", f"₹{g_exp:,}")
    g_col3.metric("📈 NET NETWORK VALUE", f"₹{g_bal:,}")
    st.markdown("---")

view_target_user = current_user
is_viewing_self = True

if user_mode == "Multiple" and member_list:
    st.subheader("🔍 Select Account View")
    options = ["My Entries Only"] + [m.upper() for m in member_list]
    selected_view = st.selectbox("Choose whose dashboard to view:", options)
    
    if selected_view != "My Entries Only":
        view_target_user = selected_view.lower()
        is_viewing_self = False

df_user = get_user_transactions(view_target_user)

st.subheader(f"👤 Ledger Dashboard: {view_target_user.upper()}")
if not df_user.empty:
    df_user["date"] = pd.to_datetime(df_user["date"])
    df_user["Month"] = df_user["date"].dt.strftime('%B %Y')
    
    all_months = df_user["Month"].unique()
    selected_month = st.selectbox("Select Display Billing Month:", all_months, key=f"month_{view_target_user}")
    
    df_filtered = df_user[df_user["Month"] == selected_month].copy()
    
    my_inc = df_filtered[df_filtered["type"] == "Income"]["amount"].sum()
    my_exp = df_filtered[df_filtered["type"] == "Expense"]["amount"].sum()
    my_bal = my_inc - my_exp
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🟩 INCOME", f"₹{my_inc:,}")
    col2.metric("🟥 EXPENSE", f"₹{my_exp:,}")
    col3.metric("🟦 NET BALANCE", f"₹{my_bal:,}")
    
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📝 Live Statement Ledger")
        for index, row in df_filtered.sort_values(by="date", ascending=False).iterrows():
            tag_color = "🟢" if row['log_status'] == "Auto" else "🟠"
            
            st.markdown(f"""
            **📅 {row['date'].strftime('%Y-%m-%d')}** | {tag_color} *[{row['log_status']}]* **Category:** {row['category']} ({row['type']})  
            **Amount:** `₹{row['amount']:,}`
            """)
            
            if is_viewing_self:
                edit_col, delete_col = st.columns(2)
                
                with edit_col:
                    if st.button("✏️ Edit", key=f"btn_ed_{row['id']}", use_container_width=True):
                        st.session_state[f"show_edit_{row['id']}"] = True
                
                with delete_col:
                    if st.button("🗑️ Delete", key=f"btn_del_{row['id']}", type="primary", use_container_width=True):
                        delete_transaction(row['id'])
                        st.toast("Entry wiped out!")
                        st.rerun()
                
                if f"show_edit_{row['id']}" in st.session_state and st.session_state[f"show_edit_{row['id']}"]:
                    with st.expander("🛠️ Update Entry Data", expanded=True):
                        edit_cat = st.text_input("New Category Name:", value=row['category'], key=f"in_cat_{row['id']}")
                        edit_amt = st.number_input("New Amount (INR):", value=float(row['amount']), key=f"in_amt_{row['id']}")
                        edit_type = st.selectbox("New Type:", ["Expense", "Income"], index=0 if row['type'] == "Expense" else 1, key=f"in_type_{row['id']}")
                        
                        save_col, cancel_col = st.columns(2)
                        with save_col:
                            if st.button("Save Changes", key=f"save_ed_{row['id']}", use_container_width=True):
                                update_transaction(row['id'], row['date'].strftime('%Y-%m-%d'), edit_type, edit_cat.title(), edit_amt, "Edited")
                                st.session_state[f"show_edit_{row['id']}"] = False
                                st.toast("Modified Safely!")
                                st.rerun()
                        with cancel_col:
                            if st.button("Cancel", key=f"cancel_ed_{row['id']}", use_container_width=True):
                                st.session_state[f"show_edit_{row['id']}"] = False
                                st.rerun()
            else:
                st.markdown("<span style='color: #888; font-size: 0.85em;'>🔒 Member Entry (Read-Only Mode)</span>", unsafe_allow_html=True)
                            
            st.markdown("<hr style='margin:1em 0px; border-color:#444;' />", unsafe_allow_html=True)
                
    with col_right:
        st.subheader("📊 Expense Distribution Analysis")
        exp_df = df_filtered[df_filtered["type"] == "Expense"]
        if not exp_df.empty:
            cat_totals = exp_df.groupby("category")["amount"].sum().reset_index()
            st.bar_chart(data=cat_totals, x="category", y="amount", color="#ff4b4b", use_container_width=True)
        else:
            st.info("No localized expenses found for this selection frame.")
else:
    st.info("No dynamic records locked inside your private node yet.")

# --- SIDEBAR EMAIL SUPPORT ---
st.sidebar.markdown("---")
with st.sidebar.expander("📧 Help & Support"):
    st.markdown("<small>Facing issues? Contact Support:</small>", unsafe_allow_html=True)
    email_url = f"mailto:{MY_EMAIL}?subject=Ledger%20Internal%20Support"
    st.link_button("📧 Email Support Desk", email_url, use_container_width=True)

# --- LOGOUT ---
st.sidebar.markdown("---")
if st.sidebar.button("🔒 SECURE SIGN OUT", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["two_fa_verified"] = False
    st.session_state["username"] = ""
    st.session_state["account_mode"] = "Single"
    st.rerun()
