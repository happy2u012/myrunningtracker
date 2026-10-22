import streamlit as st

# MUST be the absolute first Streamlit execution command
st.set_page_config(page_title="My Running Tracker", page_icon="🏃", layout="wide")

# --- CSS Injection to Hide GitHub Icons, Streamlit Menu, and Footer ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .viewerBadge_container__1QS1Y {display: none !important;}
    input[type="password"] {-webkit-text-security: square;}
    </style>
""", unsafe_allow_html=True)

import pandas as pd
import helpers
import matplotlib.pyplot as plt

# --- Load Cloud Google Sheets Data safely as structured dataframes ---
@st.cache_data(ttl=0)
def load_cloud_data():
    try:
        users_url = st.secrets["connections"]["gsheets"]["users_url"]
        runs_url = st.secrets["connections"]["gsheets"]["runs_url"]
        
        df_u = pd.read_csv(users_url, on_bad_lines='skip')
        df_r = pd.read_csv(runs_url, on_bad_lines='skip')
    except Exception as e:
        st.error(f"Spreadsheet connection error. Details: {e}")
        df_u = pd.DataFrame(columns=["runner", "password"])
        df_r = pd.DataFrame(columns=["runner", "date", "distance", "duration"])
        
    df_u.columns = [c.lower().strip() for c in df_u.columns]
    df_r.columns = [c.lower().strip() for c in df_r.columns]
    
    if "runner" not in df_u.columns: df_u = pd.DataFrame(columns=["runner", "password"])
    if "runner" not in df_r.columns: df_r = pd.DataFrame(columns=["runner", "date", "distance", "duration"])
        
    return df_u, df_r

df_users, df_runs = load_cloud_data()

# --- Individual Account Authentication Prompt Logic ---
def check_user_login():
    if "logged_in_user" not in st.session_state:
        st.session_state.logged_in_user = None
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    if st.session_state.logged_in_user is not None:
        return True

    st.title("🔒 Running Tracker Account Login")
    
    login_id = st.text_input("Username / ID").strip()
    login_pw = st.text_input("Password", type="password")
    
    if st.button("Login", use_container_width=True):
        # 1. Check against Master Admin Credentials from Secrets
        admin_id = st.secrets["admin"]["master_id"]
        admin_pw = st.secrets["admin"]["master_password"]
        
        if login_id == admin_id and login_pw == admin_pw:
            st.session_state.logged_in_user = login_id
            st.session_state.is_admin = True
            st.success("Welcome back, System Master Admin!")
            st.rerun()
            
        # 2. If not admin, check regular user sheet rows
        user_match = df_users[df_users["runner"].astype(str).str.strip() == login_id]
        if not user_match.empty and str(user_match.iloc[0]["password"]).strip() == login_pw:
            st.session_state.logged_in_user = login_id
            st.session_state.is_admin = False
            st.success(f"Welcome back, {login_id}!")
            st.rerun()
        else:
            st.error("Invalid username or password configuration.")
            
    return False

if not check_user_login():
    st.stop()

current_user = st.session_state.logged_in_user
is_admin = st.session_state.is_admin

# Sidebar Logout Component
with st.sidebar:
    st.write(f"Logged in as: **{current_user}** " + ("(Admin ⚙️)" if is_admin else ""))
    if st.button("Log Out"):
        st.session_state.logged_in_user = None
        st.session_state.is_admin = False
        st.rerun()

# Dynamically formulate tabs depending on Admin access clearance level
if is_admin:
    tab1, tab2, tab3 = st.tabs(["📊 My Running Records", "🏆 Global Leaderboard & Export", "⚙️ Admin Management Console"])
else:
    tab1, tab2 = st.tabs(["📊 My Running Records", "🏆 Global Leaderboard & Export"])

# --- Tab 1: Private Records Management (Isolated) ---
with tab1:
    st.header(f"👟 Track Records for {current_user}")
    
    my_records = df_runs[df_runs["runner"].astype(str).str.strip() == current_user].sort_values(by="date")
    if my_records.empty: 
        st.info("No running history found on your profile yet. Add rows directly to your shared Google Sheet tab.")
    else:
        formatted_my_data = []
        for idx, (_, r) in enumerate(my_records.iterrows(), 1):
            try:
                r_pace = helpers.calculate_run_pace(float(r['distance']), str(r['duration']))
                formatted_my_data.append({
                    "No.": idx, "Date": r["date"], "Distance": f"{r['distance']} km", "Duration": r["duration"], "Pace": r_pace
                })
            except:
                pass
        st.dataframe(formatted_my_data, use_container_width=True, hide_index=True)

# --- Tab 2: Shared Leaderboard & Multi-Page PDF Reporting ---
with tab2:
    st.header("🏆 Family Comparison Leaderboard")
    valid_runs = df_runs.dropna(subset=["runner", "distance", "duration"])
    
    if valid_runs.empty:
        st.info("No leaderboard entries recorded across profiles.")
    else:
        stats = helpers.calculate_stats_dataframe(valid_runs)
        for user, s in stats.items():
            with st.expander(f"👤 Runner Account: {user}", expanded=True):
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total Runs", f"{s['Total Days']} Days")
                m2.metric("Cumulative Distance", f"{s['Total Distance (km)']} km")
                m3.metric("Total Duration", s['Total Time'])
                m4.metric("Average Distance", f"{s['Avg Distance (km)']} km")
                m5.metric("Average Pace", s['Avg Pace'])
                
                st.write("---")
                col_table, col_chart = st.columns()
                user_records = valid_runs[valid_runs["runner"].astype(str).str.strip() == user].sort_values(by="date")
                
                with col_table:
                    st.write("#### 🗓️ Log Sheets")
                    if user_records.empty: 
                        st.info("This user has no activity logs tracked.")
                    else:
                        formatted_table_data = []
                        for idx, (_, run) in enumerate(user_records.iterrows(), 1):
                            formatted_table_data.append({
                                "No.": idx, "Date": run["date"], "Distance": f"{run['distance']} km",
                                "Duration": run["duration"], "Pace": helpers.calculate_run_pace(float(run['distance']), str(run['duration']))
                            })
                        st.dataframe(formatted_table_data, use_container_width=True, hide_index=True)
                        
                with col_chart:
                    st.write("#### 📊 Mileage Bar Chart")
                    if user_records.empty: 
                        st.info("No graph plots available.")
                    else:
                        fig, ax = plt.subplots(figsize=(6, max(2.5, len(user_records) * 0.4)))
                        labels = [str(run['date']) for _, run in user_records.iterrows()] + ["TOTAL"]
                        distances = [float(run['distance']) for _, run in user_records.iterrows()] + [s['Total Distance (km)']]
                        colors = ['#a6c8e0'] * len(user_records) + ['#1f4e79']
                        
                        bars = ax.barh(labels, distances, color=colors, height=0.6)
                        ax.set_xlabel("Distance (km)", fontsize=9, fontweight='bold')
                        ax.invert_yaxis()
                        ax.spines['top'].set_visible(False)
                        ax.spines['right'].set_visible(False)
                        
                        for bar in bars:
                            width = bar.get_width()
                            ax.text(width + (max(distances) * 0.02), bar.get_y() + bar.get_height()/2, 
                                    f"{width:.1f}k", va='center', ha='left', fontsize=8, fontweight='bold')
                        st.pyplot(fig)
                        plt.close(fig)

        st.subheader("📥 Export Data Reports")
        csv_data = helpers.make_csv(stats)
        try:
            pdf_data = helpers.make_pdf_dataframe(stats, valid_runs)
            pdf_ready = True
        except Exception as e:
            st.error(f"Failed to generate PDF: {e}")
            pdf_ready = False
            
        down_col1, down_col2 = st.columns(2)
        with down_col1:
            st.download_button(label="Download CSV", data=csv_data, file_name="running_comparison.csv", mime="text/csv")
        with down_col2:
            if pdf_ready:
                st.download_button(label="Download PDF", data=pdf_data, file_name="running_comparison.pdf", mime="application/pdf")

# --- Tab 3: Exclusive Admin Management Console ---
if is_admin:
    with tab3:
        st.header("⚙️ Master Admin Control Console")
        st.warning("Any structural operations executed here are logged straight to your underlying storage.")
        
        adm_opt = st.radio("Select Administrative Task", ["Manage User Accounts", "Override Running Log Records"], horizontal=True)
        
        if adm_opt == "Manage User Accounts":
            st.subheader("Add / Remove Runner Accounts")
            st.info("💡 To add or completely remove user rows securely, please adjust the rows in your linked Google Sheet 'users' tab.")
            
            st.write("#### Current Accounts Registered in System:")
            st.dataframe(df_users, use_container_width=True, hide_index=True)
            
        elif adm_opt == "Override Running Log Records":
            st.subheader("Global Logs Override Sheet")
            st.info("💡 To overwrite distances, dates, or remove incorrect run items entirely, edit the 'running_data' tab in your shared Google Sheet.")
            
            st.write("#### Current Log Entry Database Rows:")
            st.dataframe(df_runs, use_container_width=True, hide_index=True)
            