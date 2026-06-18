import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Page Config & Strongest CSS (Streamlit Branding aur Icons ko permanent gayab karne ke liye)
st.set_page_config(
    page_title="Financial Ledger Architecture", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Ultra-strict CSS script to eliminate the bottom right icons, headers, and deploy banners
hide_everything_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none !important;}
    div[data-testid="stStatusWidget"] {visibility: hidden !important;}
    footer:after {content:''; display:none !important;}
    [data-testid="stSidebarCollapseButton"] {
        background-color: #1e222b;
        color: white;
    }
    /* Hiding the streamlit footer watermark completely */
    span div img {display: none !important;}
    iframe {display: none !important;}
    </style>
"""
st.markdown(hide_everything_style, unsafe_allow_html=True)

# 2. Permanent In-Memory Database Simulation
if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "PRINCE": {"password": "adminpassword", "role": "Admin"},
        "JAYRAM": {"password": "123", "role": "User"}
    }

if "ledger_entries" not in st.session_state:
    st.session_state.ledger_entries = []

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

if "user_role" not in st.session_state:
    st.session_state.user_role = None

# --- AUTHENTICATION INTERFACE (LOGIN / REGISTER / FORGOT PASSWORD) ---
if st.session_state.logged_in_user is None:
    st.title(" FINANCIAL LEDGER ARCHITECTURE")
    
    # Login aur Registration ko handle karne ke liye simple Toggle Button
    auth_mode = st.radio("Choose Action:", ["Sign In", "Create New Account / Register"], horizontal=True)
    st.markdown("---")

    if auth_mode == "Sign In":
        st.subheader("🔒 Secure Account Login")
        username_input = st.text_input("Username").strip()
        password_input = st.text_input("Password", type="password")
        
        if st.button("SECURE SIGN IN", use_container_width=True):
            if username_input in st.session_state.users_db:
                if st.session_state.users_db[username_input]["password"] == password_input:
                    st.session_state.logged_in_user = username_input
                    st.session_state.user_role = st.session_state.users_db[username_input]["role"]
                    st.rerun()
                else:
                    st.error("🔒 Invalid Password. Please try again.")
            else:
                st.error(f"👤 User '{username_input}' not found. Toggle above to register a new account!")
        
        # Forgot Password Option
        with st.expander("🔑 Forgot Password?"):
            forgot_user = st.text_input("Enter your Username to recover:", key="forgot_u").strip()
            if st.button("Recover Password", use_container_width=True):
                if forgot_user in st.session_state.users_db:
                    recovered_pass = st.session_state.users_db[forgot_user]["password"]
                    st.success(f"🔑 Your Password is: **{recovered_pass}**")
                else:
                    st.error("Username not found in architecture database.")

    else:
        st.subheader("✨ Register New Ledger Account")
        new_username = st.text_input("Choose Username (e.g., Jayram1)").strip()
        new_password = st.text_input("Choose Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        if st.button("REGISTER & CREATE ACCOUNT", use_container_width=True):
            if not new_username or not new_password:
                st.error("Fields cannot be empty!")
            elif new_username in st.session_state.users_db:
                st.error("This username already exists. Choose a different one.")
            elif new_password != confirm_password:
                st.error("Passwords do not match!")
            else:
                # Naya User humesha default 'User' role ke sath register hoga
                st.session_state.users_db[new_username] = {"password": new_password, "role": "User"}
                st.success(f"🎉 Account successfully created for '{new_username}'! Now switch to 'Sign In' tab above to log in.")

# --- MAIN CONTROLLER SYSTEM (AFTER SUCCESSFUL LOGIN) ---
else:
    current_user = st.session_state.logged_in_user
    user_role = st.session_state.user_role

    # ==========================================
    # SIDEBAR CONTROL PANEL
    # ==========================================
    with st.sidebar:
        st.markdown("### 👤 Dashboard Controller")
        
        with st.expander("⚙️ Account Settings"):
            st.write(f"Secure Active User: **{current_user}**")
            new_pass = st.text_input("Change Password", type="password", key="pwd_update")
            if st.button("Update Password", use_container_width=True):
                if new_pass:
                    st.session_state.users_db[current_user]["password"] = new_pass
                    st.success("Password Updated!")

        st.markdown("---")

        # Admin exclusive management tools
        if user_role == "Admin":
            st.markdown("### 👥 Manage Family Accounts")
            
            with st.expander("➕ Add Family Member"):
                mem_username = st.text_input("Member Username:", key="add_u")
                mem_password = st.text_input("Member Password:", type="password", key="add_p")
                if st.button("Create Member Account", use_container_width=True):
                    if mem_username and mem_password:
                        st.session_state.users_db[mem_username] = {"password": mem_password, "role": "User"}
                        st.success(f"Account '{mem_username}' Created!")
                        st.rerun()
            
            with st.expander("🗑️ Delete Member Account"):
                delete_user = st.selectbox("Select account to remove:", [u for u in st.session_state.users_db if u != "PRINCE"])
                if st.button("Remove Account", use_container_width=True):
                    del st.session_state.users_db[delete_user]
                    st.warning(f"Removed {delete_user}")
                    st.rerun()
            
            st.markdown("---")

        # Universal Entry Form (Sabhhi users ke liye available)
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
        
        with st.expander("ℹ️ Help & Support"):
            st.write("Financial Ledger System v2.5. Contact Admin for core database assistance.")

        st.markdown("---")
        if st.button("🔒 SECURE SIGN OUT", use_container_width=True):
            st.session_state.logged_in_user = None
            st.session_state.user_role = None
            st.rerun()

    # ==========================================
    # WORKSPACE / DASHBOARD MONITOR
    # ==========================================
    st.title("📊 FINANCIAL LEDGER ARCHITECTURE")
    st.caption(f"Secure Session Active: **{current_user}**")
    st.markdown("---")

    # Math calculations for total balance sheets
    df_entries = pd.DataFrame(st.session_state.ledger_entries)
    
    total_rev = 0.0
    total_exp = 0.0
    if not df_entries.empty:
        total_rev = df_entries[df_entries["Type"] == "Revenue"]["Amount (INR)"].sum()
        total_exp = df_entries[df_entries["Type"] == "Expense"]["Amount (INR)"].sum()
    
    net_bal = total_rev - total_exp

    # Dashboard Metrics Viewports
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
        view_choice = st.selectbox("Choose whose dashboard to view:", ["All Family Records", "My Entries Only"])
        st.subheader(f"👤 Ledger Dashboard: {current_user if view_choice == 'My Entries Only' else 'All Members'}")
        
        if df_entries.empty:
            st.info("No records inside your dashboard yet.")
        else:
            display_df = df_entries[df_entries["Created By"] == current_user] if view_choice == "My Entries Only" else df_entries
            if display_df.empty:
                st.info("No records found.")
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
