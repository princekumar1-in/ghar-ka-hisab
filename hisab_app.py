import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- PRODUCTION STORAGE ---
STABLE_DB_CORE = "ledger_system_final_v1.db"

def init_db_safely():
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, account_mode TEXT, created_by TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, date TEXT, type TEXT, category TEXT, amount REAL, log_status TEXT)''')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_user(username, password, account_mode, created_by="self"):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(username, password, account_mode, created_by) VALUES (?,?,?,?)', 
                  (username, make_hashes(password), account_mode, created_by))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT password, account_mode FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    if data:
        return hashlib.sha256(str.encode(password)).hexdigest() == data[0], data[1]
    return False, None

def user_exists(username):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    return data is not None

def update_user_password(username, new_password):
    conn = sqlite3.connect(STABLE_DB_CORE)
    c = conn.cursor()
    c.execute('UPDATE users SET password = ? WHERE username = ?', (make_hashes(new_password), username))
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

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "account_mode" not in st.session_state:
    st.session_state["account_mode"] = "Single"

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
                    st.toast("Access Granted!")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
                    
        elif auth_choice == "Create Master Account":
            st.subheader("📝 Register Master Admin")
            new_user = st.text_input("Choose Username:").strip().lower()
            new_password = st.text_input("Create Password:", type="password")
            mode_selection = st.selectbox("Account Usage Mode:", ["Single User Mode", "Multiple Accounts Mode (Family/Team)"])
            selected_mode = "Single" if "Single" in mode_selection else "Multiple"
            
            if st.button("REGISTER NOW", use_container_width=True):
                if not new_user or not new_password:
                    st.error("Fields cannot be empty!")
                else:
                    if add_user(new_user, new_password, selected_mode, "self"):
                        st.success("Master account deployed! Click 'Sign In' above.")
                    else:
                        st.error("Username already taken!")
                        
        elif auth_choice == "Forget Password":
            st.subheader("🔄 Reset Account Password")
            reset_user = st.text_input("Enter Your Registered Username:").strip().lower()
            new_reset_pass = st.text_input("Enter New Password:", type="password")
            confirm_reset_pass = st.text_input("Confirm New Password:", type="password")
            
            if st.button("RESET PASSWORD", use_container_width=True):
                if not reset_user or not new_reset_pass:
                    st.error("Fields cannot be empty!")
                elif new_reset_pass != confirm_reset_pass:
                    st.error("Passwords do not match!")
                else:
                    if user_exists(reset_user):
                        update_user_password(reset_user, new_reset_pass)
                        st.success("Password recovered! Switch to 'Sign In'.")
                    else:
                        st.error("Username does not exist.")
    st.stop()

# --- MAIN SYSTEM ---
current_user = st.session_state["username"]
user_mode = st.session_state["account_mode"]

st.title("📊 FINANCIAL LEDGER ARCHITECTURE")
st.markdown(f"*Logged in as: **{current_user.upper()}** ({user_mode} Mode)*")

st.sidebar.subheader("👤 Dashboard Controller")

with st.sidebar.expander("⚙️ Account Settings"):
    st.markdown("**Modify Credentials**")
    settings_new_pass = st.text_input("New Secure Password:", type="password", key="settings_p")
    if st.button("Update Password", use_container_width=True):
        if settings_new_pass.strip():
            update_user_password(current_user, settings_new_pass)
            st.success("Password updated!")
        else:
            st.error("Password string cannot be empty.")
            
    st.markdown("---")
    st.markdown("**Danger Zone**")
    if st.button("❗ DELETE MY ACCOUNT PERMANENTLY", type="primary", use_container_width=True):
        delete_user_account(current_user)
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.rerun()

if user_mode == "Multiple":
    st.sidebar.markdown("---")
    st.sidebar.markdown("**👥 Manage Family Accounts**")
    
    with st.sidebar.expander("➕ Add Family Member"):
        sub_name = st.text_input("Member Username:").strip().lower()
        sub_pass = st.text_input("Member Password:", type="password")
        if st.button("Create Member Account"):
            if sub_name and sub_pass:
                if add_user(sub_name, sub_pass, "Single", current_user):
                    st.success(f"Account for '{sub_name}' active!")
                else:
                    st.error("Member name already exists.")
                    
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
df_user = get_user_transactions(current_user)

if user_mode == "Multiple":
    st.subheader("🌐 Consolidated Family Network Balance (Admin Summary view)")
    g_inc, g_exp, g_bal = get_global_summary_for_admin(current_user)
    g_col1, g_col2, g_col3 = st.columns(3)
    g_col1.metric("🌍 TOTAL COMBINED REVENUE", f"₹{g_inc:,}")
    g_col2.metric("🛑 TOTAL COMBINED OUTFLOW", f"₹{g_exp:,}")
    g_col3.metric("📈 NET NETWORK VALUE", f"₹{g_bal:,}")
    st.markdown("---")

st.subheader("👤 Your Personal Secure Ledger Dashboard")
if not df_user.empty:
    df_user["date"] = pd.to_datetime(df_user["date"])
    df_user["Month"] = df_user["date"].dt.strftime('%B %Y')
    
    all_months = df_user["Month"].unique()
    selected_month = st.selectbox("Select Display Billing Month:", all_months)
    
    df_filtered = df_user[df_user["Month"] == selected_month].copy()
    
    my_inc = df_filtered[df_filtered["type"] == "Income"]["amount"].sum()
    my_exp = df_filtered[df_filtered["type"] == "Expense"]["amount"].sum()
    my_bal = my_inc - my_exp
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🟩 YOUR INCOME", f"₹{my_inc:,}")
    col2.metric("🟥 YOUR EXPENSE", f"₹{my_exp:,}")
    col3.metric("🟦 YOUR NET BALANCE", f"₹{my_bal:,}")
    
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📝 Live Statement Ledger")
        for index, row in df_filtered.sort_values(by="date", ascending=False).iterrows():
            tag_color = "🟢" if row['log_status'] == "Auto" else "🟠"
            
            # Mobile Clean UI Row Display
            st.markdown(f"""
            **📅 {row['date'].strftime('%Y-%m-%d')}** | {tag_color} *[{row['log_status']}]* **Category:** {row['category']} ({row['type']})  
            **Amount:** `₹{row['amount']:,}`
            """)
            
            # Simple Clean Buttons Side-by-Side
            edit_col, delete_col = st.columns(2)
            
            with edit_col:
                if st.button("✏️ Edit", key=f"btn_ed_{row['id']}", use_container_width=True):
                    st.session_state[f"show_edit_{row['id']}"] = True
            
            with delete_col:
                if st.button("🗑️ Delete", key=f"btn_del_{row['id']}", type="primary", use_container_width=True):
                    delete_transaction(row['id'])
                    st.toast("Entry wiped out!")
                    st.rerun()
            
            # Modal/Pop-up System for Editing when clicked
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

# --- LOGOUT ---
st.sidebar.markdown("---")
if st.sidebar.button("🔒 SECURE SIGN OUT", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["account_mode"] = "Single"
    st.rerun()
