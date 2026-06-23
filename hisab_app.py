import streamlit as st
import pandas as pd
import hashlib
import re
import io
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from supabase import create_client, Client

# --- CLOUD DATABASE MASTER CONNECTION ---
SUPABASE_URL = "https://vdfmnzvtsvtnzduilgfo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZkZm1uenZ0c3Z0bnpkdWlsZ2ZvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIxMTA0NDMsImV4cCI6MjA5NzY4NjQ0M30.uSM9AM6lYGo8Q9NmpFSgrGR_osnBpXHjkROaCZjWrwg"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"⚠️ Supabase Connection Initialization Failed: {e}")

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def is_password_strong(password):
    if len(password) < 8: return False, "Password must be at least 8 characters long."
    if not re.search(r"[a-z]", password): return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[A-Z]", password): return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", password): return False, "Password must contain at least one number."
    return True, "Strong Password"

# --- SUPABASE DATA MATRIX LAYER ---
def add_user(username, password, account_mode, created_by="self"):
    try:
        data = {
            "username": username,
            "password": make_hashes(password),
            "account_mode": account_mode,
            "created_by": created_by,
            "sec_question": "Not Set",
            "sec_answer": "Not Set",
            "two_fa_pin": "Not Set"
        }
        supabase.table("users").insert(data).execute()
        return True, "Success"
    except Exception as e:
        return False, str(e)

def login_user(username, password):
    try:
        res = supabase.table("users").select("password, account_mode").eq("username", username).execute()
        if res.data:
            db_pass = res.data[0]["password"]
            db_mode = res.data[0]["account_mode"]
            return make_hashes(password) == db_pass, db_mode
        return False, None
    except Exception:
        return False, None

def check_user_security_setup(username):
    try:
        res = supabase.table("users").select("sec_question", "two_fa_pin").eq("username", username).execute()
        if res.data:
            return res.data[0]["sec_question"] != "Not Set" and res.data[0]["two_fa_pin"] != "Not Set"
        return False
    except Exception:
        return False

def save_security_setup(username, sec_q, sec_a, two_fa):
    try:
        update_data = {
            "sec_question": sec_q,
            "sec_answer": make_hashes(sec_a.strip().lower()),
            "two_fa_pin": make_hashes(two_fa)
        }
        supabase.table("users").update(update_data).eq("username", username).execute()
    except Exception as e:
        st.error(f"Security Save Error: {e}")

def user_exists(username):
    try:
        res = supabase.table("users").select("username").eq("username", username).execute()
        return len(res.data) > 0
    except Exception:
        return False

def verify_security_answer(username, answer):
    try:
        res = supabase.table("users").select("sec_answer").eq("username", username).execute()
        if res.data:
            return res.data[0]["sec_answer"] == make_hashes(answer.strip().lower())
        return False
    except Exception:
        return False

def get_user_question(username):
    try:
        res = supabase.table("users").select("sec_question").eq("username", username).execute()
        return res.data[0]["sec_question"] if res.data else None
    except Exception:
        return None

def update_user_password(username, new_password):
    try:
        supabase.table("users").update({"password": make_hashes(new_password)}).eq("username", username).execute()
    except Exception:
        pass

def update_user_2fa(username, new_2fa):
    try:
        supabase.table("users").update({"two_fa_pin": make_hashes(new_2fa)}).eq("username", username).execute()
    except Exception:
        pass

def delete_user_account(username):
    try:
        supabase.table("users").delete().eq("username", username).execute()
        supabase.table("transactions").delete().eq("username", username).execute()
    except Exception:
        pass

def get_sub_accounts(admin_username):
    try:
        res = supabase.table("users").select("username").eq("created_by", admin_username).execute()
        return [row["username"] for row in res.data] if res.data else []
    except Exception:
        return []

def save_transaction(username, date, t_type, category, amount, payment_method, notes, log_status):
    try:
        tx_data = {
            "username": username,
            "date": str(date),
            "type": t_type,
            "category": category,
            "amount": float(amount),
            "payment_method": payment_method,
            "notes": notes,
            "log_status": log_status
        }
        supabase.table("transactions").insert(tx_data).execute()
    except Exception as e:
        st.error(f"Transaction Save Error: {e}")

def get_user_transactions(username):
    try:
        res = supabase.table("transactions").select("id, date, type, category, amount, payment_method, notes, log_status").eq("username", username).execute()
        if res.data:
            return pd.DataFrame(res.data)
        return pd.DataFrame(columns=["id", "date", "type", "category", "amount", "payment_method", "notes", "log_status"])
    except Exception:
        return pd.DataFrame(columns=["id", "date", "type", "category", "amount", "payment_method", "notes", "log_status"])

def update_transaction(t_id, date, t_type, category, amount, payment_method, notes, log_status="Edited"):
    try:
        update_data = {
            "date": str(date),
            "type": t_type,
            "category": category,
            "amount": float(amount),
            "payment_method": payment_method,
            "notes": notes,
            "log_status": log_status
        }
        supabase.table("transactions").update(update_data).eq("id", t_id).execute()
    except Exception:
        pass

def delete_transaction(t_id):
    try:
        supabase.table("transactions").delete().eq("id", t_id).execute()
    except Exception:
        pass

def get_global_summary_for_admin(admin_username):
    try:
        subs = get_sub_accounts(admin_username)
        combined_users = list(subs) + [admin_username]
        
        res = supabase.table("transactions").select("type, amount, username").execute()
        if not res.data: return 0, 0, 0
        
        df = pd.DataFrame(res.data)
        df_filtered = df[df["username"].isin(combined_users)]
        
        if df_filtered.empty: return 0, 0, 0
        
        inc = df_filtered[df_filtered["type"] == "Income"]["amount"].sum()
        exp = df_filtered[df_filtered["type"] == "Expense"]["amount"].sum()
        return inc, exp, (inc - exp)
    except Exception:
        return 0, 0, 0

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(page_title="Professional Secure Ledger", layout="wide", page_icon="💰")

components.html("""
<script>
    function eraseLogosAndFixScroll() {
        var elements = window.parent.document.querySelectorAll('footer, header, .stDecoration, [data-testid="stStatusWidget"]');
        elements.forEach(function(el) { el.style.setProperty('display', 'none', 'important'); });
        var badges = window.parent.document.querySelectorAll('*');
        badges.forEach(function(node) {
            if(node.className && typeof node.className === 'string' && node.className.includes('viewerBadge')) {
                node.style.setProperty('display', 'none', 'important');
            }
        });
        window.parent.document.body.style.overscrollBehaviorY = 'contain';
        window.parent.document.documentElement.style.overscrollBehaviorY = 'contain';
    }
    setInterval(eraseLogosAndFixScroll, 50);
</script>
""", height=0)

st.markdown("""
    <style>
    header, footer, .stDecoration, [data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
    #MainMenu, .stAppDeployDropdown, button[title="View source code"] { display: none !important; }
    .stApp { padding-bottom: 30px !important; overscroll-behavior-y: contain !important; }
    div[data-testid="stConnectionStatus"] { display: none !important; }
    [class^="viewerBadge_"], [class*="viewerBadge"], [data-testid="stViewerBadge"] { display: none !important; visibility: hidden !important; }
    [data-testid="stSkeleton"] { background-color: #ffffff !important; opacity: 0 !important; }
    </style>
""", unsafe_allow_html=True)

MY_EMAIL = "vermaji3216@gmail.com"

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "two_fa_verified" not in st.session_state: st.session_state["two_fa_verified"] = False
if "username" not in st.session_state: st.session_state["username"] = ""
if "account_mode" not in st.session_state: st.session_state["account_mode"] = "Single"
if "session_expiry" not in st.session_state: st.session_state["session_expiry"] = None

if st.session_state["logged_in"] and st.session_state["session_expiry"]:
    if datetime.now() < st.session_state["session_expiry"]:
        st.session_state["two_fa_verified"] = True

SECURITY_QUESTIONS = [
    "What is the name of your first school?",
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "In which city or town were you born?"
]

# --- PHASE 1: LOGIN CONTROL ---
if not st.session_state["logged_in"]:
    st.title("🔒 SECURED LEDGER SYSTEM")
    st.markdown("---")
    auth_choice = st.radio("Select Action:", ["Sign In", "Create new Account", "Forget Password"], horizontal=True)
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
                    st.rerun()
                else: st.error("Invalid credentials.")
                    
        elif auth_choice == "Create new Account":
            st.subheader("📝 Register New Admin")
            new_user = st.text_input("Choose Unique Username:").strip().lower()
            new_password = st.text_input("Create Strong Password:", type="password")
            mode_selection = st.selectbox("Account Usage Mode:", ["Single User Mode", "Multiple Accounts Mode (Family/Team)"])
            selected_mode = "Single" if "Single" in mode_selection else "Multiple"
            if st.button("REGISTER NOW", use_container_width=True):
                is_strong, pass_msg = is_password_strong(new_password)
                if not new_user or not new_password: st.error("Fields cannot be empty!")
                elif not is_strong: st.error(pass_msg)
                else:
                    success_reg, db_error_msg = add_user(new_user, new_password, selected_mode, "self")
                    if success_reg: 
                        st.success("Account created! Switch to 'Sign In'.")
                    else: 
                        st.error(f"❌ Database Rejection: {db_error_msg}")
                        
        elif auth_choice == "Forget Password":
            st.subheader("🔄 Reset Password")
            reset_user = st.text_input("Enter Registered Username:").strip().lower()
            if reset_user and user_exists(reset_user):
                assigned_q = get_user_question(reset_user)
                if assigned_q is None or assigned_q == "Not Set": st.error("Security details not configured yet.")
                else:
                    st.info(f"**Question:** {assigned_q}")
                    user_ans = st.text_input("Your Secret Answer:", type="password")
                    st.markdown("---")
                    new_reset_pass = st.text_input("New Strong Password:", type="password")
                    confirm_reset_pass = st.text_input("Confirm New Password:", type="password")
                    if st.button("RESET PASSWORD", use_container_width=True):
                        is_strong, pass_msg = is_password_strong(new_reset_pass)
                        if new_reset_pass != confirm_reset_pass: st.error("Passwords mismatch!")
                        elif not is_strong: st.error(pass_msg)
                        elif verify_security_answer(reset_user, user_ans):
                            update_user_password(reset_user, new_reset_pass)
                            st.success("Password changed! Switch to 'Sign In'.")
                        else: st.error("Incorrect answer!")
            elif reset_user: st.error("Username not found.")
                
    st.markdown("---")
    st.info(f"📧 **Any problem please contact us:** **{MY_EMAIL}**")
    st.stop()

# --- PHASE 2: SECURITY SETUP / CHECKPOINT ---
current_user = st.session_state["username"]
user_mode = st.session_state["account_mode"]

if not check_user_security_setup(current_user):
    st.title("🛡️ INITIAL SECURITY CONFIGURATION")
    col_setup, _ = st.columns([1, 2])
    with col_setup:
        chosen_q = st.selectbox("Choose a question (For password recovery):", SECURITY_QUESTIONS)
        answer_q = st.text_input("Enter Your Answer:", type="password")
        two_fa_code = st.text_input("Create 6-Digit PIN:", type="password", max_chars=6)
        if st.button("SAVE SECURITY PROTOCOLS", use_container_width=True):
            if not answer_q or not two_fa_code: st.error("All fields are required!")
            elif not two_fa_code.isdigit() or len(two_fa_code) < 4: st.error("PIN must be numeric!")
            else:
                save_security_setup(current_user, chosen_q, answer_q, two_fa_code)
                st.session_state["two_fa_verified"] = True
                st.session_state["session_expiry"] = datetime.now() + timedelta(days=3)
                st.rerun()
    st.stop()

if not st.session_state["two_fa_verified"]:
    st.title("🛡️ 2-STEP VERIFICATION GATEWAY")
    col_2fa, _ = st.columns([1, 2])
    with col_2fa:
        pin_entry = st.text_input("Enter Your 2-Step PIN:", type="password", max_chars=6)
        trust_device = st.checkbox("Keep me logged in on this device for 3 days")
        if st.button("VERIFY SECURE PIN", use_container_width=True):
            res = supabase.table("users").select("two_fa_pin").eq("username", current_user).execute()
            db_pin = res.data[0]["two_fa_pin"] if res.data else ""
            if make_hashes(pin_entry) == db_pin:
                st.session_state["two_fa_verified"] = True
                if trust_device: st.session_state["session_expiry"] = datetime.now() + timedelta(days=3)
                st.toast("Access Cleared!")
                st.rerun()
            else: st.error("Invalid Security PIN!")
    st.markdown("---")
    if st.button("🔒 Cancel Sign In & Exit"):
        st.session_state["logged_in"] = False
        st.rerun()
    st.stop()

# --- PHASE 3: MAIN NAVIGATION TABS ARCHITECTURE ---
st.title("📊 FINANCIAL LEDGER ARCHITECTURE")
st.markdown(f"*Secure Session Active: **{current_user.upper()}***")

# PRINCE: Mobile navigation ko clean karne ke liye yahan main tabs system add kar diya ha
main_tabs = st.tabs(["🏠 Dashboard Matrix", "📝 Log New Entry", "🔍 Statement Records"])

# ==========================================
# TAB 1: DASHBOARD MATRIX & CONTROL CENTER
# ==========================================
with main_tabs[0]:
    if user_mode == "Multiple":
        st.markdown("### 🌐 Consolidated Network Matrix Balance")
        g_inc, g_exp, g_bal = get_global_summary_for_admin(current_user)
        g_col1, g_col2, g_col3 = st.columns(3)
        g_col1.metric("🌍 TOTAL COMBINED REVENUE", f"₹{g_inc:,}")
        g_col2.metric("🛑 TOTAL COMBINED OUTFLOW", f"₹{g_exp:,}")
        g_col3.metric("📈 NET NETWORK VALUE", f"₹{g_bal:,}")
        st.markdown("---")

    member_list = get_sub_accounts(current_user)
    view_target_user = current_user
    is_viewing_self = True

    if user_mode == "Multiple" and member_list:
        st.markdown("### 🔍 Select Dynamic Matrix Node View")
        options = ["My Personal Entries Only"] + [m.upper() for m in member_list]
        selected_view = st.selectbox("Choose view target parameters:", options, key="view_selector_dashboard")
        if selected_view != "My Personal Entries Only":
            view_target_user = selected_view.lower()
            is_viewing_self = False

    df_user = get_user_transactions(view_target_user)

    st.markdown(f"### 👤 Active Target Node Dashboard: **{view_target_user.upper()}**")
    if not df_user.empty:
        df_user["date"] = pd.to_datetime(df_user["date"])
        df_user["Month"] = df_user["date"].dt.strftime('%B %Y')
        selected_month = st.selectbox("Select Display Month Selector:", df_user["Month"].unique(), key=f"month_dash_{view_target_user}")
        df_filtered = df_user[df_user["Month"] == selected_month].copy()
        
        my_inc = df_filtered[df_filtered["type"] == "Income"]["amount"].sum()
        my_exp = df_filtered[df_filtered["type"] == "Expense"]["amount"].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("🟩 REVENUE STREAM", f"₹{my_inc:,}")
        col2.metric("🟥 OUTFLOW DRAIN", f"₹{my_exp:,}")
        col3.metric("🟦 NET BALANCED NODE", f"₹{(my_inc - my_exp):,}")
        
        st.markdown("---")
        st.subheader("📊 Expense Distribution Analysis Matrix")
        exp_df = df_filtered[df_filtered["type"] == "Expense"]
        if not exp_df.empty:
            cat_totals = exp_df.groupby("category")["amount"].sum().reset_index()
            st.bar_chart(data=cat_totals, x="category", y="amount", color="#ff4b4b", use_container_width=True)
        else: 
            st.info("No records match selection analytics.")
    else: 
        st.info("No records inside this dashboard node yet.")

    st.markdown("---")
    st.markdown("### ⚙️ System Control Center")
    menu_col1, menu_col2 = st.columns(2)

    with menu_col1:
        with st.expander("👤 Account Profile Settings"):
            auth_ans = st.text_input("Verify Secret Answer First:", type="password", key="sett_ans_check")
            st.markdown("---")
            settings_new_pass = st.text_input("New Strong Password:", type="password", key="settings_p")
            if st.button("Commit New Password", use_container_width=True):
                is_strong, pass_msg = is_password_strong(settings_new_pass)
                if not verify_security_answer(current_user, auth_ans): st.error("Incorrect Answer!")
                elif not is_strong: st.error(pass_msg)
                else:
                    update_user_password(current_user, settings_new_pass)
                    st.success("Password updated successfully!")
            st.markdown("---")
            settings_new_2fa = st.text_input("New 2-Step PIN:", type="password", max_chars=6, key="settings_2fa")
            if st.button("Commit New PIN", use_container_width=True):
                if not verify_security_answer(current_user, auth_ans): st.error("Incorrect Answer!")
                elif not settings_new_2fa.isdigit() or len(settings_new_2fa) < 4: st.error("Invalid pin.")
                else:
                    update_user_2fa(current_user, settings_new_2fa)
                    st.success("PIN updated successfully!")
            
            st.markdown("---")
            st.markdown("**Danger Zone Area**")
            settings_del_pin = st.text_input("Enter 2-Step PIN To Confirm Deletion:", type="password", max_chars=6, key="settings_del_p")
            if st.button("❗ DELETE MY ACCOUNT PERMANENTLY", type="primary", use_container_width=True):
                res = supabase.table("users").select("two_fa_pin").eq("username", current_user).execute()
                db_pin = res.data[0]["two_fa_pin"] if res.data else ""
                
                if not verify_security_answer(current_user, auth_ans): st.error("Incorrect Secret Recovery Answer!")
                elif make_hashes(settings_del_pin) != db_pin: st.error("Incorrect 2-Step Verification PIN!")
                else:
                    delete_user_account(current_user)
                    st.session_state["logged_in"] = False
                    st.session_state["two_fa_verified"] = False
                    st.rerun()

    with menu_col2:
        if user_mode == "Multiple":
            with st.expander("👥 Members Account Registry"):
                sub_name = st.text_input("Member Username:", key="sub_name_reg").strip().lower()
                sub_pass = st.text_input("Member Password:", type="password", key="sub_pass_reg")
                if st.button("Add Member", use_container_width=True):
                    is_strong, pass_msg = is_password_strong(sub_pass)
                    if sub_name and sub_pass:
                        if not is_strong: st.error(pass_msg)
                        elif add_user(sub_name, sub_pass, "Single", current_user)[0]:
                            st.success("Member account activated!")
                            st.rerun()
                        else: st.error("Username already registered.")
            
            if member_list:
                with st.expander("🗑️ Delete Member Account"):
                    to_delete = st.selectbox("Select Account To Delete:", member_list)
                    if st.button("CONFIRM Delete Account", type="primary", use_container_width=True):
                        delete_user_account(to_delete)
                        st.success("Account database wiped out!")
                        st.rerun()

# ==========================================
# TAB 2: LOG NEW TRANSACTION ENTRY FORM
# ==========================================
with main_tabs[1]:
    st.markdown("### 📝 Log New Transaction Entry")
    with st.form("entry_form", clear_on_submit=True):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            date_input = st.date_input("Transaction Date", datetime.now())
            type_input = st.selectbox("Accounting Type", ["Expense", "Income"])
            pay_method_input = st.selectbox("Payment Method", ["Cash", "Bank (Online/UPI)"])
        with f_col2:
            category_input = st.text_input("Category / Particulars Label", value="") 
            amount_input = st.number_input("Amount (INR)", min_value=1.0, step=1.0)
            notes_input = st.text_area("Add Description / Note (Karan)", value="")
            
        submit_btn = st.form_submit_button("COMMIT SECURE TRANSACTION RECORD", use_container_width=True)

    if submit_btn:
        if not category_input.strip(): st.error("Valid label designation required.")
        else:
            today_str = datetime.now().strftime('%Y-%m-%d')
            selected_date_str = date_input.strftime('%Y-%m-%d')
            status_tag = "Auto" if today_str == selected_date_str else "Edited"
            save_transaction(current_user, selected_date_str, type_input, category_input.strip().title(), amount_input, pay_method_input, notes_input.strip(), status_tag)
            st.toast("Logged permanently!", icon="✅")
            st.success("Record submitted successfully to cloud node!")

# ==========================================
# TAB 3: STATEMENT RECORDS & EXCEL GENERATOR
# ==========================================
with main_tabs[2]:
    st.markdown("### 🔍 Live Statement Ledger Records")
    
    # Backup trigger engine at top of records
    df_all_backup = get_user_transactions(current_user)
    if not df_all_backup.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_all_backup.to_excel(writer, index=False, sheet_name='Ledger Export')
        buffer.seek(0)
        st.download_button(
            label="📥 DOWNLOAD ALL MY DATA TO EXCEL SHEET (.XLSX)",
            data=buffer,
            file_name=f"hisab_backup_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            key="excel_download_btn"
        )
        st.markdown("---")

    member_list_records = get_sub_accounts(current_user)
    view_target_user_rec = current_user
    is_viewing_self_rec = True

    if user_mode == "Multiple" and member_list_records:
        options_rec = ["My Personal Entries Only"] + [m.upper() for m in member_list_records]
        selected_view_rec = st.selectbox("Choose data target nodes to audit:", options_rec, key="view_selector_records")
        if selected_view_rec != "My Personal Entries Only":
            view_target_user_rec = selected_view_rec.lower()
            is_viewing_self_rec = False

    df_user_rec = get_user_transactions(view_target_user_rec)

    if not df_user_rec.empty:
        df_user_rec["date"] = pd.to_datetime(df_user_rec["date"])
        df_user_rec["Month"] = df_user_rec["date"].dt.strftime('%B %Y')
        selected_month_rec = st.selectbox("Select Display Month Selector:", df_user_rec["Month"].unique(), key=f"month_rec_{view_target_user_rec}")
        df_filtered_rec = df_user_rec[df_user_rec["Month"] == selected_month_rec].copy()
        
        st.markdown(f"Showing statement for: **{view_target_user_rec.upper()}** ({selected_month_rec})")
        
        for index, row in df_filtered_rec.sort_values(by="date", ascending=False).iterrows():
            tag_color = "🟩 [Income]" if row['type'] == "Income" else "🟥 [Expense]"
            method_label = "🏪 Cash" if row['payment_method'] == "Cash" else "🏦 Bank"
            entry_note = row['notes'] if row['notes'] else "No description."
            
            with st.expander(f"Date: {row['date'].strftime('%Y-%m-%d')} | {tag_color} | **{row['category']}** | {method_label} | **₹{row['amount']:,}**"):
                st.markdown(f"**📝 Notes:** *{entry_note}*")
                st.markdown(f"**Status Tag:** `[{row['log_status']}]`")
                
                if is_viewing_self_rec:
                    st.markdown("---")
                    edit_col, delete_col = st.columns(2)
                    with edit_col:
                        if st.button("✏️ Edit Entry", key=f"btn_ed_{row['id']}", use_container_width=True):
                            st.session_state[f"show_edit_{row['id']}"] = True
                    with delete_col:
                        if st.button("🗑️ Delete Entry", key=f"btn_del_{row['id']}", type="primary", use_container_width=True):
                            delete_transaction(row['id'])
                            st.toast("Wiped out!")
                            st.rerun()
                    
                    if f"show_edit_{row['id']}" in st.session_state and st.session_state[f"show_edit_{row['id']}"]:
                        st.markdown("---")
                        edit_cat = st.text_input("New Category Name:", value=row['category'], key=f"in_cat_{row['id']}")
                        edit_amt = st.number_input("New Amount (INR):", value=float(row['amount']), key=f"in_amt_{row['id']}")
                        edit_type = st.selectbox("New Type:", ["Expense", "Income"], index=0 if row['type'] == "Expense" else 1, key=f"in_type_{row['id']}")
                        edit_method = st.selectbox("New Method:", ["Cash", "Bank (Online/UPI)"], index=0 if row['payment_method'] == "Cash" else 1, key=f"in_meth_{row['id']}")
                        edit_notes = st.text_area("New Notes:", value=row['notes'], key=f"in_note_{row['id']}")
                        
                        save_col, cancel_col = st.columns(2)
                        with save_col:
                            if st.button("Commit Changes", key=f"save_ed_{row['id']}", use_container_width=True):
                                update_transaction(row['id'], row['date'].strftime('%Y-%m-%d'), edit_type, edit_cat.title(), edit_amt, edit_method, edit_notes, "Edited")
                                st.session_state[f"show_edit_{row['id']}"] = False
                                st.rerun()
                        with cancel_col:
                            if st.button("Drop Token", key=f"cancel_ed_{row['id']}", use_container_width=True):
                                st.session_state[f"show_edit_{row['id']}"] = False
                                st.rerun()
                else:
                    st.markdown("<span style='color: #888; font-size: 0.85em;'>🔒 Member Entry (Read-Only Mode)</span>", unsafe_allow_html=True)
    else:
        st.info("No transaction statements logged inside this node frame yet.")

st.markdown("---")

# --- FOOTER TERMINAL CONNECTION ---
bot_col1, bot_col2 = st.columns(2)
with bot_col1:
    st.info(f"📧 **Any problem please contact us:**\n\n📩 **{MY_EMAIL}**")
with bot_col2:
    if st.button("🔒 SECURE TERMINAL SIGN OUT CONNECTION", use_container_width=True, type="primary", key="signout_footer_btn"):
        st.session_state["logged_in"] = False
        st.session_state["two_fa_verified"] = False
        st.rerun()
