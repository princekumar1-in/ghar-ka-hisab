import streamlit as st
import pandas as pd
import hashlib
import re
import io
import urllib.request
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

def get_user_ip():
    try:
        return urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
    except Exception:
        return "127.0.0.1"

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def is_password_strong(password):
    if len(password) < 8: return False, "Password must be at least 8 characters long."
    if not re.search(r"[a-z]", password): return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[A-Z]", password): return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", password): return False, "Password must contain at least one number."
    return True, "Strong Password"

# --- SUPABASE DATA LAYER ---
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
        
        # Mapping dual translation compliance types to get precise cloud sums
        inc = df_filtered[df_filtered["type"].isin(["Income", "आय"])]["amount"].sum()
        exp = df_filtered[df_filtered["type"].isin(["Expense", "व्यय"])]["amount"].sum()
        return inc, exp, (inc - exp)
    except Exception:
        return 0, 0, 0

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(page_title="Professional Ledger", layout="wide", page_icon="💰")

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

# --- PRINCE: PURE DUAL DICTIONARY MATRIX L10N LAYER ---
LANG_DICT = {
    "English": {
        "title": "📊 FINANCIAL LEDGER ARCHITECTURE",
        "login_title": "🔒 SECURED LEDGER SYSTEM",
        "action_lbl": "Select Action:",
        "sign_in": "Sign In",
        "create_acc": "Create new Account",
        "forget_pass": "Forget Password",
        "username": "Username:",
        "password": "Password:",
        "reg_admin": "Register New Admin",
        "acc_mode": "Account Usage Mode:",
        "single_m": "Single User Mode",
        "multi_m": "Multiple Accounts Mode (Family/Team)",
        "btn_register": "REGISTER NOW",
        "btn_login": "SIGN IN",
        "sec_config": "🛡️ INITIAL SECURITY CONFIGURATION",
        "sec_q_lbl": "Choose a question (For password recovery):",
        "sec_a_lbl": "Enter Your Answer:",
        "pin_lbl": "Create 6-Digit PIN:",
        "btn_save_sec": "SAVE SECURITY PROTOCOLS",
        "gateway_title": "🛡️ 2-STEP VERIFICATION GATEWAY",
        "pin_entry_lbl": "Enter Your 2-Step PIN:",
        "btn_verify_pin": "VERIFY SECURE PIN & SAVE IP",
        "tab_dash": "🏠 Summary Dashboard",
        "tab_entry": "📝 General Entry",
        "tab_rec": "🔍 Ledger Statement",
        "tab_credit": "👥 Credit Ledger (Debts)",
        "net_matrix_title": "🌐 Consolidated Network Balance",
        "total_rev": "🌍 TOTAL REVENUE",
        "total_out": "🛑 TOTAL OUTFLOW",
        "net_bal_adj": "📈 NET BALANCE (Adjusted with Credit)",
        "active_node_lbl": "Active Account Dashboard:",
        "display_month": "Select Display Month:",
        "inc_stream": "🟩 INCOME STREAM",
        "exp_drain": "🟥 EXPENSE DRAIN",
        "net_balance": "🟦 NET BALANCE",
        "exp_analysis": "📊 Expense Distribution Analysis",
        "sys_control": "### ⚙️ System Control Center",
        "profile_sett": "👤 Account Profile Settings",
        "sec_check_lbl": "Verify Security Answer First:",
        "new_pass_lbl": "New Strong Password:",
        "btn_commit_pass": "Commit New Password",
        "new_pin_lbl": "New 2-Step PIN:",
        "btn_commit_pin": "Commit New PIN",
        "family_reg": "👥 Family Members Registry",
        "member_user": "Member Username:",
        "member_pass": "Member Password:",
        "btn_add_member": "Add Member Account",
        "log_tx_title": "### 📝 Log New Transaction Entry",
        "tx_date": "Transaction Date",
        "tx_type": "Transaction Type Mode",
        "tx_method": "Payment Method Protocol",
        "tx_cat": "Category / Particulars Label",
        "tx_amt": "Amount (INR)",
        "tx_desc": "Description / Notes",
        "btn_commit_tx": "COMMIT SECURE TRANSACTION RECORD",
        "cashbook_title": "### 🔍 General Cashbook Statements",
        "credit_title": "👥 Credit Accounts Directory (Udhaar)",
        "open_profile_exp": "➕ Open New Credit Account Profile",
        "ent_acc_name": "Enter Account Name (e.g. Ramesh Kumar, Verma Kirana Store):",
        "btn_create_profile": "CREATE PROFILE ACCOUNT",
        "select_profile": "🎯 Select Credit Profile Account to Open:",
        "p_statement_title": "Account Statement:",
        "p_given": "🔴 Credit Given (To Receive)",
        "p_taken": "<span>🟢</span> Credit Taken (To Pay)",
        "p_due_us": "🚨 NET STATUS (Balance Due to Us)",
        "p_owe": "🤝 NET STATUS (Balance We Owe)",
        "p_settled": "✅ NET STATUS (Settled)",
        "log_inside_ledger": "Log New Entry inside Ledger",
        "action_protocol": "Action Type Protocol",
        "remarks_lbl": "Transaction Particulars / Remarks:",
        "btn_submit_ledger": "SUBMIT TO LEDGER",
        "history_title": "#### 🕒 Transaction History Ledger Log",
        "btn_del": "Delete",
        "support_desk": "Support Desk:",
        "btn_signout": "🔒 SECURE SIGN OUT TERMINAL"
    },
    "Hindi": {
        "title": "📊 वित्तीय बहीखाता प्रणाली",
        "login_title": "🔒 सुरक्षित लॉगइन केंद्र",
        "action_lbl": "कार्य का चयन करें:",
        "sign_in": "प्रवेश करें",
        "create_acc": "नया खाता बनाएं",
        "forget_pass": "पासवर्ड भूल गए",
        "username": "उपयोगकर्ता नाम:",
        "password": "पासवर्ड (गुप्त कोड):",
        "reg_admin": "मुख्य प्रबंधक पंजीकरण",
        "acc_mode": "खाता उपयोग का प्रकार:",
        "single_m": "एकल उपयोगकर्ता मोड",
        "multi_m": "एकाधिक खाता मोड (परिवार/टीम)",
        "btn_register": "अभी सुरक्षित पंजीकृत करें",
        "btn_login": "सफलतापूर्वक प्रवेश करें",
        "sec_config": "🛡️ प्रारंभिक सुरक्षा विन्यास",
        "sec_q_lbl": "सुरक्षा प्रश्न चुनें (पासवर्ड रिकवरी के लिए):",
        "sec_a_lbl": "अपना गुप्त उत्तर दर्ज करें:",
        "pin_lbl": "६-अंकों का सुरक्षा पिन बनाएं:",
        "btn_save_sec": "सुरक्षा नियम सुरक्षित करें",
        "gateway_title": "🛡️ द्वि-चरण सत्यापन सुरक्षा द्वार",
        "pin_entry_lbl": "अपना ६-अंकों का पिन दर्ज करें:",
        "btn_verify_pin": "पिन सत्यापित करें एवं आईपी सुरक्षित करें",
        "tab_dash": "🏠 मुख्य सारांश",
        "tab_entry": "📝 सामान्य प्रविष्टि",
        "tab_rec": "🔍 बहीखाता विवरण",
        "tab_credit": "👥 ऋण खाता (उधार निर्देशिका)",
        "net_matrix_title": "🌐 समेकित कुल पारिवारिक संतुलन",
        "total_rev": "🌍 कुल सकल आय",
        "total_out": "🛑 कुल सकल व्यय",
        "net_bal_adj": "📈 शुद्ध शेष राशि (ऋण समायोजित)",
        "active_node_lbl": "सक्रिय खाता विवरण:",
        "display_month": "प्रदर्शन माह का चयन करें:",
        "inc_stream": "🟩 कुल प्राप्त आय",
        "exp_drain": "🟥 कुल किया गया व्यय",
        "net_balance": "🟦 शुद्ध शेष राशि",
        "exp_analysis": "📊 व्यय वितरण विश्लेषणात्मक चार्ट",
        "sys_control": "### ⚙️ मुख्य प्रणाली नियंत्रण केंद्र",
        "profile_sett": "👤 व्यक्तिगत खाता विन्यास settings",
        "sec_check_lbl": "पहले सुरक्षा प्रश्न का उत्तर सत्यापित करें:",
        "new_pass_lbl": "नया सुदृढ़ पासवर्ड:",
        "btn_commit_pass": "नया पासवर्ड लागू करें",
        "new_pin_lbl": "नया द्वि-चरण सुरक्षा पिन:",
        "btn_commit_pin": "नया पिन लागू करें",
        "family_reg": "👥 परिवार सदस्य खाता पंजीकरण",
        "member_user": "सदस्य का उपयोगकर्ता नाम:",
        "member_pass": "सदस्य का पासवर्ड:",
        "btn_add_member": "नया सदस्य खाता जोड़ें",
        "log_tx_title": "### 📝 नई वित्तीय प्रविष्टि दर्ज करें",
        "tx_date": "लेनदेन की तिथि",
        "tx_type": "लेनदेन का प्रकार",
        "tx_method": "भुगतान की पद्धति",
        "tx_cat": "श्रेणी या विवरण का नाम",
        "tx_amt": "धनराशि (भारतीय रुपया)",
        "tx_desc": "विवरण या विशेष टिप्पणी",
        "btn_commit_tx": "वित्तीय रिकॉर्ड बहीखाता में दर्ज करें",
        "cashbook_title": "### 🔍 सामान्य नकद बहीखाता विवरण",
        "credit_title": "👥 ऋण खाता विवरण (उधार खता)",
        "open_profile_exp": "➕ नया व्यक्तिगत ऋण खाता प्रोफ़ाइल खोलें",
        "ent_acc_name": "खाताधारक का पूरा नाम दर्ज करें (जैसे: रमेश कुमार, वर्मा किराना स्टोर):",
        "btn_create_profile": "नया ऋण खाता स्थापित करें",
        "select_profile": "🎯 विवरण देखने के लिए ऋण खाता प्रोफ़ाइल चुनें:",
        "p_statement_title": "व्यक्तिगत खाता विवरण:",
        "p_given": "🔴 दिया गया ऋण (हमें वापस लेना है)",
        "p_taken": "<span>🟢</span> लिया गया ऋण (हमें वापस देना है)",
        "p_due_us": "🚨 शुद्ध स्थिति (बाकी धनराशि जो हमें लेनी है)",
        "p_owe": "🤝 शुद्ध स्थिति (देय धनराशि जो हमें चुकानी है)",
        "p_settled": "✅ शुद्ध स्थिति (हिसाब बराबर)",
        "log_inside_ledger": "इस खाते के अंतर्गत नया लेनदेन दर्ज करें",
        "action_protocol": "कार्रवाई का प्रकार",
        "remarks_lbl": "लेनदेन का विशेष विवरण या टिप्पणी:",
        "btn_submit_ledger": "रिकॉर्ड खाते में सबमिट करें",
        "history_title": "#### 🕒 इस खाते का ऐतिहासिक बहीखाता लॉग",
        "btn_del": "हटाएं",
        "support_desk": "सहायता केंद्र:",
        "btn_signout": "🔒 सुरक्षित लॉगआउट कनेक्शन"
    }
}

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "two_fa_verified" not in st.session_state: st.session_state["two_fa_verified"] = False
if "username" not in st.session_state: st.session_state["username"] = ""
if "account_mode" not in st.session_state: st.session_state["account_mode"] = "Single"
if "trusted_ip_cache" not in st.session_state: st.session_state["trusted_ip_cache"] = None

# Pure Global Language state hook
if "app_lang" not in st.session_state: st.session_state["app_lang"] = "English"

# --- TOP LANGUAGE TOGGLE STRIP ---
lang_col1, lang_col2 = st.columns([8, 2])
with lang_col2:
    st.session_state["app_lang"] = st.selectbox("🌐 Language / भाषा", ["English", "Hindi"], index=0 if st.session_state["app_lang"] == "English" else 1)

TXT = LANG_DICT[st.session_state["app_lang"]]
user_current_ip = get_user_ip()

# --- PHASE 1: LOGIN CONTROL ---
if not st.session_state["logged_in"]:
    st.title(TXT["login_title"])
    st.markdown("---")
    auth_choice = st.radio(TXT["action_lbl"], [TXT["sign_in"], TXT["create_acc"], TXT["forget_pass"]], horizontal=True)
    col1, _ = st.columns([1, 2])
    with col1:
        if auth_choice == TXT["sign_in"]:
            st.subheader(TXT["sign_in"])
            username_input = st.text_input(TXT["username"]).strip().lower()
            password_input = st.text_input(TXT["password"], type="password")
            if st.button(TXT["btn_login"], use_container_width=True):
                success, mode = login_user(username_input, password_input)
                if success:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username_input
                    st.session_state["account_mode"] = mode
                    st.rerun()
                else: st.error("Invalid credentials / अमान्य विवरण")
                
        elif auth_choice == TXT["create_acc"]:
            st.subheader(TXT["reg_admin"])
            new_user = st.text_input(TXT["username"]).strip().lower()
            new_password = st.text_input(TXT["password"], type="password")
            mode_selection = st.selectbox(TXT["acc_mode"], [TXT["single_m"], TXT["multi_m"]])
            selected_mode = "Single" if mode_selection == TXT["single_m"] else "Multiple"
            if st.button(TXT["btn_register"], use_container_width=True):
                is_strong, pass_msg = is_password_strong(new_password)
                if not new_user or not new_password: st.error("Fields cannot be empty / रिक्त स्थान न छोड़ें")
                elif not is_strong: st.error(pass_msg)
                else:
                    success_reg, db_error_msg = add_user(new_user, new_password, selected_mode, "self")
                    if success_reg: st.success("Account created! Switch to Sign In / खाता निर्मित हुआ।")
                    else: st.error(f"❌ Rejection: {db_error_msg}")
                    
        elif auth_choice == TXT["forget_pass"]:
            st.subheader(TXT["forget_pass"])
            reset_user = st.text_input(TXT["username"]).strip().lower()
            if reset_user and user_exists(reset_user):
                assigned_q = get_user_question(reset_user)
                if assigned_q is None or assigned_q == "Not Set": st.error("Security not configured.")
                else:
                    st.info(f"Question: {assigned_q}")
                    user_ans = st.text_input(TXT["sec_a_lbl"], type="password")
                    st.markdown("---")
                    new_reset_pass = st.text_input(TXT["new_pass_lbl"], type="password")
                    if st.button("RESET PASSWORD", use_container_width=True):
                        if verify_security_answer(reset_user, user_ans):
                            update_user_password(reset_user, new_reset_pass)
                            st.success("Success!")
                        else: st.error("Incorrect!")
    st.markdown("---")
    st.stop()

# --- PHASE 2: SECURITY CHECKPOINT ---
current_user = st.session_state["username"]
user_mode = st.session_state["account_mode"]

if not check_user_security_setup(current_user):
    st.title(TXT["sec_config"])
    col_setup, _ = st.columns([1, 2])
    with col_setup:
        chosen_q = st.selectbox(TXT["sec_q_lbl"], SECURITY_QUESTIONS)
        answer_q = st.text_input(TXT["sec_a_lbl"], type="password")
        two_fa_code = st.text_input(TXT["pin_lbl"], type="password", max_chars=6)
        if st.button(TXT["btn_save_sec"], use_container_width=True):
            if not answer_q or not two_fa_code: st.error("Required!")
            else:
                save_security_setup(current_user, chosen_q, answer_q, two_fa_code)
                st.session_state["two_fa_verified"] = True
                st.session_state["trusted_ip_cache"] = user_current_ip
                st.rerun()
    st.stop()

if st.session_state["trusted_ip_cache"] == user_current_ip:
    st.session_state["two_fa_verified"] = True

if not st.session_state["two_fa_verified"]:
    st.title(TXT["gateway_title"])
    st.info(f"🌐 IP: `{user_current_ip}`")
    col_2fa, _ = st.columns([1, 2])
    with col_2fa:
        pin_entry = st.text_input(TXT["pin_entry_lbl"], type="password", max_chars=6)
        if st.button(TXT["btn_verify_pin"], use_container_width=True):
            res = supabase.table("users").select("two_fa_pin").eq("username", current_user).execute()
            if make_hashes(pin_entry) == res.data[0]["two_fa_pin"]:
                st.session_state["two_fa_verified"] = True
                st.session_state["trusted_ip_cache"] = user_current_ip
                st.rerun()
            else: st.error("Error!")
    st.stop()

# --- PHASE 3: MAIN NAVIGATION TABS ---
st.title(TXT["title"])
st.markdown(f"*Session: **{current_user.upper()}*** | 🌐 *IP: `{user_current_ip}`*")

main_tabs = st.tabs([TXT["tab_dash"], TXT["tab_entry"], TXT["tab_rec"], TXT["tab_credit"]])
df_all_data = get_user_transactions(current_user)

# Credit alignment engine matching locale strings
credit_given_types = ["Credit Given (To Receive)", "Credit Given (To Receive)", "उधार दिया (लेना है)"]
credit_taken_types = ["Credit Taken (To Pay)", "Credit Taken (To Pay)", "उधार लिया (देना है)"]

udhaar_net_balance = 0.0
if not df_all_data.empty:
    all_lena = df_all_data[df_all_data["type"].isin(credit_given_types)]["amount"].sum()
    all_dena = df_all_data[df_all_data["type"].isin(credit_taken_types)]["amount"].sum()
    udhaar_net_balance = all_lena - all_dena

# ==========================================
# TAB 1: SUMMARY DASHBOARD
# ==========================================
with main_tabs[0]:
    if user_mode == "Multiple":
        st.markdown(f"### {TXT['net_matrix_title']}")
        g_inc, g_exp, g_bal = get_global_summary_for_admin(current_user)
        g_final_bal = g_bal + udhaar_net_balance
        g_col1, g_col2, g_col3 = st.columns(3)
        g_col1.metric(TXT["total_rev"], f"₹{g_inc:,}")
        g_col2.metric(TXT["total_out"], f"₹{g_exp:,}")
        g_col3.metric(TXT["net_bal_adj"], f"₹{g_final_bal:,}")
        st.markdown("---")

    member_list = get_sub_accounts(current_user)
    view_target_user = current_user
    if user_mode == "Multiple" and member_list:
        selected_view = st.selectbox("Select Account Node:", ["Personal Only"] + [m.upper() for m in member_list])
        if selected_view != "Personal Only": view_target_user = selected_view.lower()

    df_target = get_user_transactions(view_target_user)
    st.markdown(f"### {TXT['active_node_lbl']} **{view_target_user.upper()}**")
    
    if not df_target.empty:
        df_target["date"] = pd.to_datetime(df_target["date"])
        df_target["Month"] = df_target["date"].dt.strftime('%B %Y')
        selected_month = st.selectbox(TXT["display_month"], df_target["Month"].unique(), key=f"m_{view_target_user}")
        df_filtered = df_target[df_target["Month"] == selected_month].copy()
        
        my_inc = df_filtered[df_filtered["type"].isin(["Income", "आय"])]["amount"].sum()
        my_exp = df_filtered[df_filtered["type"].isin(["Expense", "व्यय"])]["amount"].sum()
        t_lena = df_filtered[df_filtered["type"].isin(credit_given_types)]["amount"].sum()
        t_dena = df_filtered[df_filtered["type"].isin(credit_taken_types)]["amount"].sum()
        my_final_bal = (my_inc - my_exp) + (t_lena - t_dena)
        
        col1, col2, col3 = st.columns(3)
        col1.metric(TXT["inc_stream"], f"₹{my_inc:,}")
        col2.metric(TXT["exp_drain"], f"₹{my_exp:,}")
        col3.metric(TXT["net_balance"], f"₹{my_final_bal:,}")
        
        st.markdown("---")
        st.subheader(TXT["exp_analysis"])
        exp_df = df_filtered[df_filtered["type"].isin(["Expense", "व्यय"])]
        if not exp_df.empty:
            cat_totals = exp_df.groupby("category")["amount"].sum().reset_index()
            st.bar_chart(data=cat_totals, x="category", y="amount", color="#ff4b4b", use_container_width=True)
    else: st.info("No records inside this node yet.")

    st.markdown("---")
    st.markdown(TXT["sys_control"])
    menu_col1, menu_col2 = st.columns(2)
    with menu_col1:
        with st.expander(TXT["profile_sett"]):
            auth_ans = st.text_input(TXT["sec_check_lbl"], type="password", key="sett_ans")
            settings_new_pass = st.text_input(TXT["new_pass_lbl"], type="password", key="sett_p")
            if st.button(TXT["btn_commit_pass"], use_container_width=True):
                if verify_security_answer(current_user, auth_ans):
                    update_user_password(current_user, settings_new_pass)
                    st.success("Updated!")
    with menu_col2:
        if user_mode == "Multiple":
            with st.expander(TXT["family_reg"]):
                sub_name = st.text_input(TXT["member_user"]).strip().lower()
                sub_pass = st.text_input(TXT["member_pass"], type="password")
                if st.button(TXT["btn_add_member"], use_container_width=True):
                    if add_user(sub_name, sub_pass, "Single", current_user)[0]: st.success("Added!")

# ==========================================
# TAB 2: GENERAL ENTRY
# ==========================================
with main_tabs[1]:
    st.markdown(TXT["log_tx_title"])
    with st.form("entry_form", clear_on_submit=True):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            date_input = st.date_input(TXT["tx_date"], datetime.now())
            type_options = ["Expense", "Income"] if st.session_state["app_lang"] == "English" else ["व्यय", "आय"]
            type_input = st.selectbox(TXT["tx_type"], type_options)
            pay_method_input = st.selectbox(TXT["tx_method"], ["Cash", "Bank (Online/UPI)"])
        with f_col2:
            category_input = st.text_input(TXT["tx_cat"], value="") 
            amount_input = st.number_input(TXT["tx_amt"], min_value=1.0, step=1.0)
            notes_input = st.text_area(TXT["tx_desc"], value="")
        submit_btn = st.form_submit_button(TXT["btn_commit_tx"], use_container_width=True)

    if submit_btn:
        if not category_input.strip(): st.error("Error Parameters!")
        else:
            # Map type back to database schema standards symmetrically
            mapped_type = "Income" if type_input in ["Income", "आय"] else "Expense"
            today_str = datetime.now().strftime('%Y-%m-%d')
            selected_date_str = date_input.strftime('%Y-%m-%d')
            status_tag = "Auto" if today_str == selected_date_str else "Edited"
            save_transaction(current_user, selected_date_str, mapped_type, category_input.strip().title(), amount_input, pay_method_input, notes_input.strip(), status_tag)
            st.toast("Success!", icon="✅")
            st.rerun()

# ==========================================
# TAB 3: LEDGER STATEMENT
# ==========================================
with main_tabs[2]:
    st.markdown(TXT["cashbook_title"])
    if not df_all_data.empty:
        df_cash_only = df_all_data[df_all_data["type"].isin(["Income", "Expense"])].copy()
        if not df_cash_only.empty:
            df_cash_only["date"] = pd.to_datetime(df_cash_only["date"])
            df_cash_only["Month"] = df_cash_only["date"].dt.strftime('%B %Y')
            selected_month_rec = st.selectbox(TXT["display_month"], df_cash_only["Month"].unique(), key="cash_m_rec")
            df_filtered_rec = df_cash_only[df_cash_only["Month"] == selected_month_rec].copy()
            
            for index, row in df_filtered_rec.sort_values(by="date", ascending=False).iterrows():
                tag_color = "🟩 [Income]" if row['type'] == "Income" else "🟥 [Expense]"
                method_label = "🏪 Cash" if row['payment_method'] == "Cash" else "🏦 Bank"
                with st.expander(f"Date: {row['date'].strftime('%Y-%m-%d')} | {tag_color} | **{row['category']}** | {method_label} | **₹{row['amount']:,}**"):
                    st.markdown(f"**📝 Description:** *{row['notes']}*")
                    if st.button(TXT["btn_del"], key=f"del_c_{row['id']}", type="primary"):
                        delete_transaction(row['id'])
                        st.toast("Deleted!")
                        st.rerun()
        else: st.info("No Cash entries logged yet.")

# ==========================================
# TAB 4: CREDIT LEDGER (UDHAAR KHATA)
# ==========================================
with main_tabs[3]:
    st.header(TXT["credit_title"])
    with st.expander(TXT["open_profile_exp"]):
        new_account_name = st.text_input(TXT["ent_acc_name"]).strip().title()
        if st.button(TXT["btn_create_profile"], use_container_width=True, type="primary"):
            if new_account_name:
                save_transaction(current_user, datetime.now().strftime('%Y-%m-%d'), "Credit Account Initialized", new_account_name, 0.0, "Cash", "Account Opened Permanent", "Active Profile")
                st.success("Account Installed Successfully!")
                st.rerun()
                
    st.markdown("---")
    all_profiles = []
    if not df_all_data.empty:
        all_profiles = sorted(df_all_data[df_all_data["type"] == "Credit Account Initialized"]["category"].unique())
        
    if not all_profiles: st.info("No profiles found.")
    else:
        selected_person = st.selectbox(TXT["select_profile"], all_profiles)
        df_person_history = df_all_data[df_all_data["category"] == selected_person].copy()
        
        p_given = df_person_history[df_person_history["type"].isin(["Credit Given (To Receive)", "Udhaar Diya (Lena)"])]["amount"].sum()
        p_taken = df_person_history[df_person_history["type"].isin(["Credit Taken (To Pay)", "Udhaar Liya (Dena)"])]["amount"].sum()
        p_net_balance = p_given - p_taken
        
        st.markdown(f"### {TXT['p_statement_title']} **{selected_person.upper()}**")
        p_col1, p_col2, p_col3 = st.columns(3)
        p_col1.markdown(f"<div style='font-size:1.1em;'>{TXT['p_given']}: <b>₹{p_given:,}</b></div>", unsafe_allow_html=True)
        p_col2.markdown(f"<div style='font-size:1.1em;'>{TXT['p_taken']}: <b>₹{p_taken:,}</b></div>", unsafe_allow_html=True)
        
        if p_net_balance > 0: st.metric(TXT["p_due_us"], f"₹{abs(p_net_balance):,}")
        elif p_net_balance < 0: st.metric(TXT["p_owe"], f"₹{abs(p_net_balance):,}")
        else: st.metric(TXT["p_settled"], "₹0")
            
        st.markdown("---")
        st.markdown(f"➕ **{TXT['log_inside_ledger']} ({selected_person})**")
        with st.form(f"f_p_{selected_person}", clear_on_submit=True):
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                u_date = st.date_input("Date", datetime.now(), key=f"d_{selected_person}")
                protocol_options = ["Credit Given (To Receive)", "Credit Taken (To Pay)"] if st.session_state["app_lang"] == "English" else ["उधार दिया (लेना है)", "उधार लिया (देना है)"]
                u_type = st.selectbox(TXT["action_protocol"], protocol_options, key=f"t_{selected_person}")
            with sub_col2:
                u_amount = st.number_input(TXT["tx_amt"], min_value=1.0, step=1.0, key=f"a_{selected_person}")
                u_notes = st.text_input(TXT["remarks_lbl"], key=f"n_{selected_person}")
            
            if st.form_submit_button(TXT["btn_submit_ledger"], use_container_width=True):
                # Map systemic backend translation storage schemas
                db_credit_type = "Credit Given (To Receive)" if u_type in ["Credit Given (To Receive)", "उधार दिया (लेना है)"] else "Credit Taken (To Pay)"
                save_transaction(current_user, u_date.strftime('%Y-%m-%d'), db_credit_type, selected_person, u_amount, "Cash", u_notes, "Active Debt")
                st.toast("Saved!")
                st.rerun()
                
        st.markdown(TXT["history_title"])
        df_logs_only = df_person_history[df_person_history["type"].str.contains("Credit Given|Credit Taken|Udhaar")].copy()
        if not df_logs_only.empty:
            for idx, r_row in df_logs_only.sort_values(by="date", ascending=False).iterrows():
                log_tag = "🔴 Given" if "Given" in r_row["type"] or "Diya" in r_row["type"] else "🟢 Taken"
                with st.expander(f"Date: {r_row['date']} | {log_tag} | **₹{r_row['amount']:,}**"):
                    st.markdown(f"*{r_row['notes']}*")
                    if st.button(TXT["btn_del"], key=f"del_p_{r_row['id']}", type="primary"):
                        delete_transaction(r_row['id'])
                        st.toast("Removed!")
                        st.rerun()

st.markdown("---")
bot_col1, bot_col2 = st.columns(2)
with bot_col1: st.info(f"📧 **{TXT['support_desk']} vermaji3216@gmail.com**")
with bot_col2:
    if st.button(TXT["btn_signout"], use_container_width=True, type="primary"):
        st.session_state["logged_in"] = False
        st.session_state["two_fa_verified"] = False
        st.session_state["trusted_ip_cache"] = None
        st.rerun()
