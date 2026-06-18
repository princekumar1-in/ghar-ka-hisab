import streamlit as st
import pandas as pd
from datetime import datetime
import re

# 1. Page Config & Strict Layout CSS (Logos permanent block)
st.set_page_config(
    page_title="Financial Ledger Architecture", 
    layout="wide", 
    initial_sidebar_state="collapsed" # Mobile friendly initial state
)

absolute_clean_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none !important;}
    div[data-testid="stStatusWidget"] {visibility: hidden !important;}
    
    footer, div[data-testid="stDecoration"], .st-emotion-cache-1pxn4b9, .st-emotion-cache-12galv2 {
        display: none !important;
        visibility: hidden !important;
    }
    img[src*="streamlit"], div[class*="viewerBadge"] {
        display: none !important;
    }
    iframe {display: none !important;}
    
    /* Email link styling */
    .email-link {
        color: #ff4b4b !important;
        text-decoration: none;
        font-weight: bold;
        border: 1px solid #ff4b4b;
        padding: 5px 10px;
        border-radius: 5px;
        display: inline-block;
        margin-top: 5px;
    }
    </style>
"""
st.markdown(absolute_clean_style, unsafe_allow_html=True)

# Password strength helper
def check_password_strength(password):
    if len(password) < 6:
        return False, "Password must be at least 6 characters long!"
    if not re.search("[A-Z]", password):
        return False, "Password must contain at least one uppercase letter!"
    if not re.search("[0-9]", password):
        return False, "Password must contain at least one digit!"
    return True, "Strong Password!"

# 2. Centralizing Persistent Storage Map
if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "PRINCE": {"password": "AdminPassword@123", "role": "Admin", "type": "Multiple", "sec_qst": "What is your pet name?", "sec_ans": "prince", "two_step_pin": "9999"},
        "JAYRAM": {"password": "UserPassword@123", "role": "User", "type": "Single", "sec_qst": "What is your favorite city?", "sec_ans": "delhi", "two_step_pin": "1234"}
    }

if "ledger_entries" not in st.session_state:
    st.session_state.ledger_entries = []

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "temp_user" not in st.session_state:
    st.session_state.temp_user = None

# --- AUTHENTICATION SHIELD ---
if st.session_state.logged_in_user is None:
    st.title(" FINANCIAL LEDGER ARCHITECTURE")
    auth_mode = st.radio("Choose Action:", ["Sign In", "Create New Account / Register"], horizontal=True)
    st.markdown("---")

    if auth_mode == "Sign In":
        if st.session_state.temp_user is None:
            st.subheader("🔒 Step 1: Account Login")
            username_input = st.text_input("Username").strip()
            password_input = st.text_input("Password", type="password").strip()
            
            if st.button("PROCEED TO VERIFICATION", use_container_width=True):
                matched_user = None
                for u in st.session_state.users_db:
                    if str(u).strip().upper() == str(username_input).upper():
                        matched_user = u
                        break
                        
                if matched_user:
                    db_password = str(st.session_state.users_db[matched_user]["password"]).strip()
                    if db_password == password_input:
                        st.session_state.temp_user = matched_user
                        st.rerun()
                    else:
                        st.error("🔒 Invalid Password. Please try again.")
                else:
                    st.error(f"👤 User '{username_input}' not found. If you are a new user, register first using the option above.")
            
            with st.expander("🔑 Forgot Password via Security Question?"):
                f_user = st.text_input("Enter Username:", key="f_u").strip()
                f_matched = None
                for u in st.session_state.users_db:
                    if u.strip().upper() == f_user.upper(): f_matched = u; break
                if f_matched:
                    st.info(f"Question: {st.session_state.users_db[f_matched]['sec_qst']}")
                    f_ans = st.text_input("Enter Answer:", key="f_a").lower().strip()
                    if st.button("Verify & Reveal Password", use_container_width=True):
                        if f_ans == st.session_state.users_db[f_matched]['sec_ans']:
                            st.success(f"🔑 Your Password is: **{st.session_state.users_db[f_matched]['password']}**")
                        else: st.error("Galat Answer!")
        else:
            st.subheader(f"🛡️ Step 2: 2-Step Verification Code")
            pin_input = st.text_input("Enter 4-Digit Security PIN", type="password", max_chars=4).strip()
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("VERIFY & SIGN IN", use_container_width=True):
                    target_pin = str(st.session_state.users_db[st.session_state.temp_user].get("two_step_pin", "1234")).strip()
                    if pin_input == target_pin:
                        st.session_state.logged_in_user = st.session_state.temp_user
                        st.session_state.user_role = st.session_state.users_db[st.session_state.temp_user]["role"]
                        st.session_state.temp_user = None
                        st.rerun()
                    else: st.error("Galat Security PIN!")
            with col_b2:
                if st.button("Back", use_container_width=True): st.session_state.temp_user = None; st.rerun()

    else:
        st.subheader("✨ Register New Secured Account")
        new_username = st.text_input("Choose Username").strip()
        new_password = st.text_input("Choose Password", type="password").strip()
        confirm_password = st.text_input("Confirm Password", type="password").strip()
        
        s_qst = st.selectbox("Select Security Question:", ["What is your pet name?", "What is your favorite city?"])
        s_ans = st.text_input("Security Answer").lower().strip()
        t_pin = st.text_input("Set 4-Digit 2-Step PIN", type="password", max_chars=4).strip()
        account_type = st.radio("Account Type:", ["Single User Account", "Multiple Accounts (Family/Admin)"])
        
        if st.button("REGISTER & CREATE SECURE ACCOUNT", use_container_width=True):
            if not new_username or not new_password or not s_ans or not t_pin:
                st.error("Sabhhi fields ko bharna mandatory hai!")
            elif new_username.upper() in [u.upper() for u in st.session_state.users_db]:
                st.error("Ye username pehle se register hai!")
            elif new_password != confirm_password:
                st.error("Passwords match nahi ho rahe hain!")
            else:
                role = "Admin" if account_type == "Multiple Accounts (Family/Admin)" else "User"
                st.session_state.users_db[new_username] = {
                    "password": new_password, "role": role, "type": "Multiple" if "Multiple" in account_type else "Single",
                    "sec_qst": s_qst, "sec_ans": s_ans, "two_step_pin": t_pin
                }
                st.success(f"🎉 Account '{new_username}' Created! Go to 'Sign In' tab now.")

# --- OPERATIONAL APPLICATION MAIN WORKSPACE ---
else:
    current_user = st.session_state.logged_in_user
    user_role = st.session_state.user_role

    st.title("📊 FINANCIAL LEDGER ARCHITECTURE")
    st.caption(f"Secure Session Active: **{current_user}** | Role: **{user_role}**")
    
    # MOBILE STABLE VIEW: Dashboard View aur Entry Systems ko Tabs me daal diya taaki arrow ka locha hi khatam!
    if user_role == "Admin":
        view_tab, entry_tab, config_tab, support_tab = st.tabs(["📊 View Ledgers", "📝 Log New Entry", "👥 Manage Family", "⚙️ Support & Settings"])
    else:
        view_tab, entry_tab, support_tab = st.tabs(["📊 View Ledgers", "📝 Log New Entry", "⚙️ Support & Settings"])

    # --- TAB 1: DASHBOARD DISPLAY ---
    with view_tab:
        df_entries = pd.DataFrame(st.session_state.ledger_entries)
        total_rev = df_entries[df_entries["Type"] == "Revenue"]["Amount (INR)"].sum() if not df_entries.empty else 0.0
        total_exp = df_entries[df_entries["Type"] == "Expense"]["Amount (INR)"].sum() if not df_entries.empty else 0.0
        net_bal = total_rev - total_exp

        st.markdown("#### 🌐 Consolidated Family Balance Sheet")
        m1, m2, m3 = st.columns(3)
        m1.metric("🌍 TOTAL REVENUE", f"₹{total_rev:,.2f}")
        m2.metric("🔴 TOTAL OUTFLOW", f"₹{total_exp:,.2f}")
        m3.metric("📈 NET BALANCE", f"₹{net_bal:,.2f}")
        st.markdown("---")

        st.markdown("### 🔎 Select Account View")
        if user_role == "Admin":
            distinct_users = ["All Family Records", "My Entries Only"] + [u for u in st.session_state.users_db if u != "PRINCE"]
            view_choice = st.selectbox("Choose whose dashboard to view:", distinct_users)
            
            if df_entries.empty: st.info("No records inside dashboard yet.")
            else:
                if view_choice == "All Family Records": display_df = df_entries
                elif view_choice == "My Entries Only": display_df = df_entries[df_entries["Created By"] == current_user]
                else: display_df = df_entries[df_entries["Created By"] == view_choice]
                st.dataframe(display_df, use_container_width=True)
        else:
            if df_entries.empty: st.info("No records found.")
            else:
                member_df = df_entries[df_entries["Created By"] == current_user]
                st.dataframe(member_df, use_container_width=True)

    # --- TAB 2: LOG NEW ENTRY (Ab mobile par samne dikhega bina side kiye!) ---
    with entry_tab:
        st.subheader("📝 Log New Transaction Entry")
        with st.form("main_entry_form", clear_on_submit=True):
            entry_date = st.date_input("Transaction Date", datetime.now())
            entry_type = st.selectbox("Type", ["Expense", "Revenue"])
            category = st.text_input("Category / Particulars")
            amount = st.number_input("Amount (INR)", min_value=0.0, step=1.0, value=1.0)
            
            if st.form_submit_button("COMMIT TRANSACTION", use_container_width=True):
                if category.strip() == "": st.error("Kripya Category / Particulars bharein!")
                else:
                    st.session_state.ledger_entries.append({
                        "Date": entry_date.strftime("%Y-%m-%d"), "Type": entry_type,
                        "Particulars": category, "Amount (INR)": amount, "Created By": current_user
                    })
                    st.success("Transaction Successfully Committed!")
                    st.rerun()

    # --- TAB 3: ADMIN CONTROLS (Only for admin) ---
    if user_role == "Admin" and "config_tab" in locals():
        with config_tab:
            st.subheader("👥 Manage Family Database Connections")
            col_add, col_del = st.columns(2)
            
            with col_add:
                st.markdown("#### ➕ Add New Member")
                with st.form("admin_add_member"):
                    m_u = st.text_input("Username:").strip()
                    m_p = st.text_input("Password:", type="password").strip()
                    if st.form_submit_button("Register Member Account"):
                        if m_u and m_p:
                            st.session_state.users_db[m_u] = {"password": m_p, "role": "User", "type": "Single", "sec_qst": "What is your pet name?", "sec_ans": "default", "two_step_pin": "1234"}
                            st.success(f"User '{m_u}' registered permanently!")
                            st.rerun()
            
            with col_del:
                st.markdown("#### 🗑️ Remove Member")
                delete_user = st.selectbox("Select account to remove:", [u for u in st.session_state.users_db if u != "PRINCE"])
                if st.button("Remove Account Profile", use_container_width=True):
                    del st.session_state.users_db[delete_user]
                    st.warning(f"Deleted {delete_user}")
                    st.rerun()

    # --- TAB 4: SUPPORT & LOGOUT SETTINGS ---
    with support_tab:
        st.subheader("⚙️ System Control Desk")
        
        # Self account deletion with strict short text confirmation
        st.markdown("---")
        if st.checkbox("⚠️ Self Delete My Account"):
            st.caption("Are you sure you want to permanently delete your account?")
            if st.button("Yes, Confirm Deletion", use_container_width=True):
                if current_user == "PRINCE": st.error("Admin cannot be deleted!")
                else:
                    del st.session_state.users_db[current_user]
                    st.session_state.logged_in_user = None; st.session_state.user_role = None; st.rerun()
                    
        st.markdown("---")
        st.markdown("#### ✉️ Technical Assistance Desk")
        email_html = '<a href="mailto:vermaji3216@gmail.com?subject=Ledger%20Support" class="email-link">📧 Click to Mail: vermaji3216@gmail.com</a>'
        st.markdown(email_html, unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("🔒 SECURE SIGN OUT FROM ARCHITECTURE", use_container_width=True):
            st.session_state.logged_in_user = None; st.session_state.user_role = None; st.rerun()
