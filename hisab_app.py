import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Page Config & CSS (Niche ke logos aur default buttons ko jad se hatane ke liye)
st.set_page_config(
    page_title="Financial Ledger Architecture", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Strict CSS to completely remove Streamlit footer, branding, and deploy buttons
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    div[data-testid="stStatusWidget"] {visibility: hidden;}
    /* Mobile sidebar toggle button matching dark theme */
    [data-testid="stSidebarCollapseButton"] {
        background-color: #1e222b;
        color: white;
    }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# 2. Database & State Initialization
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

# --- LOGIN SCREEN ---
if st.session_state.logged_in_user is None:
    st.title(" FINANCIAL LEDGER ARCHITECTURE")
    st.subheader("Secure Account Login")
    
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
            st.error("👤 User not found. Contact Admin to create your account.")

# --- MAIN DASHBOARD (LOGGED IN) ---
else:
    current_user = st.session_state.logged_in_user
    user_role = st.session_state.user_role

    # ==========================================
    # SIDEBAR CONTROLLER (Aapke UI ke mutabik exact features)
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

        # ADMIN ONLY: Manage Family Accounts (Ye section baki users ko nahi dikhega)
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

        # EVERYONE: Log New Entry (Ye Admin aur Jayram dono ko dikhega same aapki tarah)
        st.markdown("### 📝 Log New Entry")
        
        entry_date = st.date_input("Transaction Date", datetime.now())
        entry_type = st.selectbox("Type", ["Expense", "Revenue"])
        category = st.text_input("Category / Particulars")
        amount = st.number_input("Amount (INR)", min_value=0.0, step=1.0, value=1.0)
        
        if st.button("COMMIT TRANSACTION", use_container_width=True):
            if category.strip() == "":
                st.sidebar.error("Kripya Category / Particulars bharein!")
            else:
                # Save transaction entry
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
        
        # Help & Support Section
        with st.expander("ℹ️ Help & Support"):
            st.write("Financial Ledger System v2.0. Contact Prince for technical support.")

        st.markdown("---")
        # Secure Sign out Button
        if st.button("🔒 SECURE SIGN OUT", use_container_width=True):
            st.session_state.logged_in_user = None
            st.session_state.user_role = None
            st.rerun()

    # ==========================================
    # MAIN DASHBOARD SCREEN DISPLAY
    # ==========================================
    st.title("📊 FINANCIAL LEDGER ARCHITECTURE")
    st.caption(f"Secure Session Active: **{current_user}**")
    st.markdown("---")

    # Data Calculation logic
    df_entries = pd.DataFrame(st.session_state.ledger_entries)
    
    total_rev = 0.0
    total_exp = 0.0
    if not df_entries.empty:
        total_rev = df_entries[df_entries["Type"] == "Revenue"]["Amount (INR)"].sum()
        total_exp = df_entries[df_entries["Type"] == "Expense"]["Amount (INR)"].sum()
    
    net_bal = total_rev - total_exp

    # Display Top Metrics Panel
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

    # Filter rules for Admin vs Normal Users
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
        # For User (Jaise Jayram login karega toh direct ye dikhega)
        st.subheader(f"👤 Ledger Dashboard: {current_user}")
        if df_entries.empty:
            st.info("No records inside your dashboard yet.")
        else:
            member_df = df_entries[df_entries["Created By"] == current_user]
            if member_df.empty:
                st.info("Aapne abhi tak koi transaction commit nahi kiya hai.")
            else:
                st.dataframe(member_df, use_container_width=True)
