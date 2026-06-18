import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Page Config & Custom CSS (Logo/Footer hatane aur layout clean rakhne ke liye)
st.set_page_config(
    page_title="Financial Ledger Architecture", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Niche wale logos, default hamburger menu aur footer ko hide karne ki CSS
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    /* Mobile par sidebar toggler ko thoda handle karne ke liye */
    [data-testid="stSidebarCollapseButton"] {
        background-color: #1e222b;
        color: white;
    }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# 2. Database & State Initialize (Ghar ke sadasyo aur entry ka records)
if "users_db" not in st.session_state:
    st.session_state.users_db = {
        "PRINCE": {"password": "adminpassword", "role": "Admin"},
        "Jayram": {"password": "Vermaji#!", "role": "User"}
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

# --- MAIN SYSTEM (LOGGED IN) ---
else:
    current_user = st.session_state.logged_in_user
    user_role = st.session_state.user_role

    # ==========================================
    # SIDEBAR SETUP (Dynamic Layout as per image)
    # ==========================================
    with st.sidebar:
        st.markdown(f"### 👤 {user_role} Controller")
        
        with st.expander("⚙️ Account Settings"):
            st.write(f"Logged in as: **{current_user}**")
            # Change password feature basic block
            new_pass = st.text_input("New Password", type="password", key="chg_pass")
            if st.button("Update Pass"):
                st.session_state.users_db[current_user]["password"] = new_pass
                st.success("Updated!")

        st.markdown("---")

        # PRIVILEGED CONTROLS: Ye section sirf PRINCE (Admin) ko dikhega, dusro ke mobile me automatic chhup jayega
        if user_role == "Admin":
            st.markdown("### 👥 Manage Family Accounts")
            
            with st.expander("➕ Add Family Member"):
                new_mem_user = st.text_input("Member Username:", key="new_user")
                new_mem_pass = st.text_input("Member Password:", type="password", key="new_pass")
                if st.button("Create Member Account", use_container_width=True):
                    if new_mem_user and new_mem_pass:
                        st.session_state.users_db[new_mem_user] = {"password": new_mem_pass, "role": "User"}
                        st.success(f"Account for {new_mem_user} created!")
                        st.rerun()
            
            with st.expander("🗑️ Delete Member Account"):
                delete_target = st.selectbox("Select account to remove:", [u for u in st.session_state.users_db if u != "PRINCE"])
                if st.button("Remove Account", use_container_width=True):
                    del st.session_state.users_db[delete_target]
                    st.sidebar.warning(f"Removed {delete_target}")
                    st.rerun()
            
            st.markdown("---")

        # UNIVERSAL CONTROLS: Ye "Log New Entry" section Admin aur baki sabhi users dono ko dikhega!
        st.markdown("### 📝 Log New Entry")
        
        entry_date = st.date_input("Transaction Date", datetime.now())
        entry_type = st.selectbox("Type", ["Expense", "Revenue"])
        category = st.text_input("Category / Particulars", placeholder="e.g., Grocery, Petrol, Advance")
        amount = st.number_input("Amount (INR)", min_value=0.0, step=1.0, value=1.0)
        
        if st.button("COMMIT TRANSACTION", use_container_width=True):
            if category == "":
                st.sidebar.error("Kripya Particulars bharein!")
            else:
                # Naye record ko save karna database me
                new_record = {
                    "Date": entry_date.strftime("%Y-%m-%d"),
                    "Type": entry_type,
                    "Particulars": category,
                    "Amount (INR)": amount,
                    "Created By": current_user
                }
                st.session_state.ledger_entries.append(new_record)
                st.sidebar.success("Transaction Committed successfully!")
                st.rerun()

        st.markdown("---")
        with st.expander("ℹ️ Help & Support"):
            st.write("For any technical issues, reach out to the network architecture manager.")

        if st.button("🔒 SECURE SIGN OUT", use_container_width=True):
            st.session_state.logged_in_user = None
            st.session_state.user_role = None
            st.rerun()

    # ==========================================
    # MAIN DASHBOARD AREA (As per image 1000007832.jpg)
    # ==========================================
    st.title("📊 FINANCIAL LEDGER ARCHITECTURE")
    st.caption(f"Secure Session Active: *{current_user}*")
    st.markdown("---")

    # Data Calculations
    df_entries = pd.DataFrame(st.session_state.ledger_entries)
    
    total_rev = 0.0
    total_exp = 0.0
    
    if not df_entries.empty:
        total_rev = df_entries[df_entries["Type"] == "Revenue"]["Amount (INR)"].sum()
        total_exp = df_entries[df_entries["Type"] == "Expense"]["Amount (INR)"].sum()
    
    net_network_bal = total_rev - total_exp

    # Display Top Metrics Panel (Only for Admin View or calculated dynamically)
    st.markdown("### 🌐 Consolidated Family Network Balance (Account Summary view)")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric(label="🌍 TOTAL COMBINED REVENUE", value=f"₹{total_rev:,.2f}")
    with m_col2:
        st.metric(label="🔴 TOTAL COMBINED OUTFLOW", value=f"₹{total_exp:,.2f}")
    with m_col3:
        st.metric(label="📈 NET NETWORK BALANCE", value=f"₹{net_network_bal:,.2f}")

    st.markdown("---")
    st.markdown("### 🔎 Select Account View")

    # Dashboard display logic based on role
    if user_role == "Admin":
        view_choice = st.selectbox("Choose whose dashboard to view:", ["All Family Records", "My Entries Only"])
        st.subheader(f"👤 Ledger Dashboard: {current_user if view_choice == 'My Entries Only' else 'All Members'}")
        
        if df_entries.empty:
            st.info("No records inside your dashboard yet.")
        else:
            if view_choice == "My Entries Only":
                display_df = df_entries[df_entries["Created By"] == current_user]
            else:
                display_df = df_entries
                
            if display_df.empty:
                st.info("No records found for this selection.")
            else:
                st.dataframe(display_df, use_container_width=True)
                
    else:
        # Agar koi normal family member (jaise Jayram) login karta hai
        st.subheader(f"👤 Ledger Dashboard: {current_user}")
        if df_entries.empty:
            st.info("No records inside your dashboard yet.")
        else:
            # Privacy protection: Sadasya sirf apni entry dekh payega, dusro ki nahi
            member_df = df_entries[df_entries["Created By"] == current_user]
            if member_df.empty:
                st.info("Aapne abhi tak koi transaction commit nahi kiya hai.")
            else:
                st.dataframe(member_df, use_container_width=True)
                
