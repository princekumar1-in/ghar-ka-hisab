import streamlit as st
import pandas as pd
from datetime import datetime
import re

# 1. Page Config & Strict Layout CSS
st.set_page_config(
    page_title="Financial Ledger Architecture", 
    layout="wide", 
    initial_sidebar_state="expanded"
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
    img[src*="streamlit"], div[class*="viewerBadge"], [className*="viewerBadge"] {
        display: none !important;
    }
    iframe {display: none !important;}
    
    [data-testid="stSidebar"] {
        background-color: #11151c;
    }
    [data-testid="stSidebarCollapseButton"] {
        background-color: #1e222b;
        color: white;
    }
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
    .email-link:hover {
        background-color: #ff4b4b;
        color: white !important;
    }
    </style>
"""
st.markdown(absolute_clean_style, unsafe_allow_html=True)

# Password strength criteria checker
def check_password_strength(password):
    if len(password) < 6:
        return False, "Password must be at least 6 characters long!"
    if not re.search("[A-Z]", password):
        return False, "Password must contain at least one uppercase letter!"
    if not re.search("[0-9]", password):
        return False, "Password must contain at least one digit!"
    if not re.search("[_@#$]", password):
        return False, "Password must contain at least one special character (_ @ # $)!"
    return True, "Strong Password!"

# 2. Database Core Realignment
if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "PRINCE": {
            "password": "AdminPassword@123", 
            "role": "Admin", 
            "type": "Multiple",
            "sec_qst": "What is your pet name?",
            "sec_ans": "prince",
            "two_step_pin": "9999"
        },
        "JAYRAM": {
            "password": "UserPassword@123", 
            "role": "User", 
            "type": "Single",
            "sec_qst": "What is your favorite city?",
            "sec_ans": "delhi",
            "two_step_pin": "1234"
        }
    }

if "ledger_entries" not in st.session_state:
    st.session_state.ledger_entries = []

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "temp_user" not in st.session_state:
    st.session_state.temp_user = None

# --- AUTHENTICATION MODULE ---
if st.session_state.logged_in_user is None:
    st.title(" FINANCIAL LEDGER ARCHITECTURE")
    auth_mode = st.radio("Choose Action:", ["Sign In", "Create New Account / Register"], horizontal=True)
    st.markdown("---")

    if auth_mode == "Sign In":
        if st.session_state.temp_user is None:
            st.subheader("🔒 Step 1: Account Login")
            username_input = st.text_input("Username").strip()
            password_input = st.text_input("Password", type="password")
            
            if st.button("PROCEED TO VERIFICATION", use_container_width=True):
                # FIXED: Case-insensitive precise database match to fix "Wrong Password" bug
                matched_user = None
                for u in st.session_state.users_db:
                    if u.strip().upper() == username_input.strip().upper():
                        matched_user = u
                        break
                        
                if matched_user:
                    if str(st.session_state.users_db[matched_user]["password"]) == str(password_input):
                        st.session_state.temp_user = matched_user
                        st.rerun()
                    else:
                        st.error("🔒 Invalid Password. Please try again.")
                else:
                    st.error(f"👤 User '{username_input}' not found.")
            
            with st.expander("🔑 Forgot Password via Security Question?"):
                f_user = st.text_input("Enter Username:", key="f_u").strip()
                
                # Case-insensitive check for forgot password too
                f_matched = None
                for u in st.session_state.users_db:
                    if u.strip().upper() == f_user.strip().upper():
                        f_matched = u
                        break
                        
                if f_matched:
                    st.info(f"Question: {st.session_state.users_db[f_matched]['sec_qst']}")
                    f_ans = st.text_input("Enter Answer:", key="f_a").lower().strip()
                    if st.button("Verify & Reveal Password", use_container_width=True):
                        if f_ans == st.session_state.users_db[f_matched]['sec_ans']:
                            st.success(f"🔑 Your Password is: **{st.session_state.users_db[f_matched]['password']}**")
                        else:
                            st.error("Galat Answer! Kripya sahi answer dalein.")
                elif f_user:
                    st.error("User not found.")
        else:
            st.subheader(f"🛡️ Step 2: 2-Step Verification for {st.session_state.temp_user}")
            pin_input = st.text_input("Enter 4-Digit Security PIN", type="password", max_chars=4)
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("VERIFY & SIGN IN", use_container_width=True):
                    target_pin = st.session_state.users_db[st.session_state.temp_user].get("two_step_pin", "1234")
                    if str(pin_input) == str(target_pin):
                        st.session_state.logged_in_user = st.session_state.temp_user
                        st.session_state.user_role = st.session_state.users_db[st.session_state.temp_user]["role"]
                        st.session_state.temp_user = None
                        st.rerun()
                    else:
                        st.error("Galat Security Code/PIN!")
            with col_b2:
                if st.button("Back to Login", use_container_width=True):
                    st.session_state.temp_user = None
                    st.rerun()

    else:
        st.subheader("✨ Register New Secured Account")
        new_username = st.text_input("Choose Username").strip()
        new_password = st.text_input("Choose Password", type="password")
        
        if new_password:
            is_strong, msg = check_password_strength(new_password)
            if is_strong: st.success(f"🔒 {msg}")
            else: st.warning(f"⚠️ {msg}")
                
        confirm_password = st.text_input("Confirm Password", type="password")
        
        st.markdown("#### Setup System Recovery Controls:")
        s_qst = st.selectbox("Select Security Question:", [
            "What is your pet name?",
            "What is your favorite city?",
            "What was your first school name?"
        ])
        s_ans = st.text_input("Security Answer").lower().strip()
        t_pin = st.text_input("Set 4-Digit 2-Step PIN (Numeric Only)", type="password", max_chars=4)
        
        account_type = st.radio("Account Type:", ["Single User Account", "Multiple Accounts (Family/Admin)"])
        
        if st.button("REGISTER & CREATE SECURE ACCOUNT", use_container_width=True):
            if not new_username or not new_password or not s_ans or not t_pin:
                st.error("Sabhhi fields ko bharna mandatory hai!")
            elif new_username.upper() in [u.upper() for u in st.session_state.users_db]:
                st.error("Ye username pehle se register hai!")
            elif new_password != confirm_password:
                st.error("Passwords match nahi ho rahe hain!")
            elif not check_password_strength(new_password)[0]:
                st.error("Kripya pehle password ko rules ke mutabik STRONG banayein!")
            elif not t_pin.isdigit() or len(t_pin) != 4:
                st.error("2-Step PIN sirf 4 digits ka numeric code hona chahiye!")
            else:
                role = "Admin" if account_type == "Multiple Accounts (Family/Admin)" else "User"
                st.session_state.users_db[new_username] = {
                    "password": new_password, 
                    "role": role,
                    "type": "Multiple" if "Multiple" in account_type else "Single",
                    "sec_qst": s_qst,
                    "sec_ans": s_ans,
                    "two_step_pin": t_pin
                }
                st.success(f"🎉 Account '{new_username}' successfully verify ho gaya hai! Ab 'Sign In' par jake login karein.")

# --- OPERATIONAL APPLICATION CORE ---
else:
    current_user = st.session_state.logged_in_user
    user_role = st.session_state.user_role

    # ==========================================
    # SIDEBAR CONTROLLER ARCHITECTURE
    # ==========================================
    with st.sidebar:
        st.markdown("### 👤 Dashboard Controller")
        
        with st.expander("⚙️ Account Settings"):
            st.write(f"Active User: **{current_user}**")
            new_pass = st.text_input("Change Password", type="password", key="p_up")
            if new_pass:
                is_st, msg_st = check_password_strength(new_pass)
                if not is_st: st.warning(msg_st)
                
            if st.button("Update Password", use_container_width=True):
                if new_pass and check_password_strength(new_pass)[0]:
                    st.session_state.users_db[current_user]["password"] = new_pass
                    st.success("Password Updated!")
                else:
                    st.error("Sahi aur strong password dalein!")
            
            st.markdown("---")
            if st.checkbox("⚠️ Self Delete My Account"):
                st.caption("Are you sure you want to permanently delete your account?")
                if st.button("Yes, Confirm Deletion", use_container_width=True):
                    if current_user == "PRINCE":
                        st.error("Main Admin Account cannot be deleted!")
                    else:
                        del st.session_state.users_db[current_user]
                        st.session_state.logged_in_user = None
                        st.session_state.user_role = None
                        st.rerun()

        st.markdown("---")

        # Admin controls for user databases
        if user_role == "Admin":
            st.markdown("### 👥 Manage Family Accounts")
            
            with st.expander("➕ Add Family Member"):
                mem_username = st.text_input("Member Username:", key="add_u").strip()
                mem_password = st.text_input("Member Password:", type="password", key="add_p")
                if st.button("Create Member Account", use_container_width=True):
                    if mem_username and mem_password:
                        # FIXED: Member database entry is linked explicitly to sync with Sign-In parameters
                        st.session_state.users_db[mem_username] = {
                            "password": mem_password, 
                            "role": "User", 
                            "type": "Single",
                            "sec_qst": "What is your pet name?",
                            "sec_ans": "default",
                            "two_step_pin": "1234" # Default 2-step PIN for created family members
                        }
                        st.success(f"Member '{mem_username}' added successfully!")
                        st.rerun()
            
            with st.expander("🗑️ Delete Member Account"):
                delete_user = st.selectbox("Select account to remove:", [u for u in st.session_state.users_db if u != "PRINCE"])
                if st.button("Remove Selected Account", use_container_width=True):
                    del st.session_state.users_db[delete_user]
                    st.warning(f"Successfully deleted {delete_user}")
                    st.rerun()
            
            st.markdown("---")

        # Log New Entry
        st.markdown("### 📝 Log New Entry")
        entry_date = st.date_input("Transaction Date", datetime.now())
        entry_type = st.selectbox("Type", ["Expense", "Revenue"])
        category = st.text_input("Category / Particulars")
        amount = st.number_input("Amount (INR)", min_value=0.0, step=1.0, value=1.0)
        
        if st.button("COMMIT TRANSACTION", use_container_width=True):
            if category.strip() == "":
                st.sidebar.error("Kripya Category / Particulars bharein!")
            else:
                new_transaction = {
                    "Date": entry_date.strftime("%Y-%m-%d"),
                    "Type": entry_type,
                    "Particulars": category,
                    "Amount (INR)": amount,
                    "Created By": current_user
                }
                st.session_state.ledger_entries.append(new_transaction)
                st.sidebar.success("Transaction Committed!")
                st.rerun()

        st.markdown("---")
        
        with st.expander("✉️ Help & Support"):
            st.write("**Architecture Support Desk**")
            st.write("Click below to directly send a support email:")
            email_html = '<a href="mailto:vermaji3216@gmail.com?subject=Ledger%20App%20Support%20Query" class="email-link">📧 Click to Mail: vermaji3216@gmail.com</a>'
            st.markdown(email_html, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔒 SECURE SIGN OUT", use_container_width=True):
            st.session_state.logged_in_user = None
            st.session_state.user_role = None
            st.rerun()

    # ==========================================
    # CENTRAL CONTROL PLATFORM
    # ==========================================
    st.title("📊 FINANCIAL LEDGER ARCHITECTURE")
    st.caption(f"Secure Session Active: **{current_user}**")
    st.markdown("---")

    df_entries = pd.DataFrame(st.session_state.ledger_entries)
    
    total_rev = 0.0
    total_exp = 0.0
    if not df_entries.empty:
        total_rev = df_entries[df_entries["Type"] == "Revenue"]["Amount (INR)"].sum()
        total_exp = df_entries[df_entries["Type"] == "Expense"]["Amount (INR)"].sum()
    
    net_bal = total_rev - total_exp

    st.markdown("### 🌐 Consolidated Family Network Balance (Account Summary view)")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric(label="🌍 TOTAL COMBINED REVENUE", value=f"₹{total_rev:,.2f}")
    with m_col2:
        st.metric(label="🔴 TOTAL COMBINED OUTFLOW", value=f"₹{total_exp:,.2f}")
    with m_col3:
        st.metric(label="📈 NET NETWORK BALANCE", value=f"₹{net_bal:,.2f}")

    st.markdown("---")
    st.markdown("### 🔎 Select Account View")

    if user_role == "Admin":
        distinct_users = ["All Family Records", "My Entries Only"] + [u for u in st.session_state.users_db if u != "PRINCE"]
        view_choice = st.selectbox("Choose whose dashboard to view:", distinct_users)
        
        st.subheader(f"👤 Ledger Dashboard: {view_choice}")
        
        if df_entries.empty:
            st.info("No records inside your dashboard yet.")
        else:
            if view_choice == "All Family Records":
                display_df = df_entries
            elif view_choice == "My Entries Only":
                display_df = df_entries[df_entries["Created By"] == current_user]
            else:
                display_df = df_entries[df_entries["Created By"] == view_choice]
                
            if display_df.empty:
                st.info(f"No records found for selection: {view_choice}")
            else:
                st.dataframe(display_df, use_container_width=True)
                
    else:
        st.subheader(f"👤 Ledger Dashboard: {current_user}")
        if df_entries.empty:
            st.info("No records inside your dashboard yet.")
        else:
            member_df = df_entries[df_entries["Created By"] == current_user]
            if member_df.empty:
                st.info("Aapne abhi tak koi transaction commit nahi kiya hai.")
            else:
                st.dataframe(member_df, use_container_width=True)
