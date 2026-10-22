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

from streamlit_gsheets import GSheetsConnection
import pandas as pd
import helpers
import matplotlib.pyplot as plt

# --- Initialize Live Google Sheets Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Read active databases
df_users = conn.read(worksheet="users", ttl=0)
df_runs = conn.read(worksheet="running_data", ttl=0)

# Build structure safeguards for empty sheets
if df_users.empty or len(df_users.columns) < 2:
    df_users = pd.DataFrame(columns=["runner", "password"])
if df_runs.empty or len(df_runs.columns) < 4:
    df_runs = pd.DataFrame(columns=["runner", "date", "distance", "duration"])

# --- Individual Account Authentication Prompt Logic ---
def check_user_login():
    if "logged_in_user" not in st.session_state:
        st.session_state.logged_in_user = None

    if st.session_state.logged_in_user is not None:
        return True

    st.title("🔒 Running Tracker Account Login")
    
    login_id = st.text_input("Username / ID").strip()
    login_pw = st.text_input("Password", type="password")
    
    col_login, col_reg = st.columns(2)
    with col_login:
        if st.button("Login", use_container_width=True):
            # Check user credentials from the live Google Sheet dataframe rows
            user_match = df_users[df_users["runner"] == login_id]
            if not user_match.empty and str(user_match.iloc[0]["password"]) == login_pw:
                st.session_state.logged_in_user = login_id
                st.success(f"Welcome back, {login_id}!")
                st.rerun()
            else:
                st.error("Invalid username or password configuration.")
                
    with col_reg:
        with st.popover("Create New Account", use_container_width=True):
            reg_id = st.text_input("New Runner ID").strip()
            reg_pw = st.text_input("New Password", type="password", key="reg_pw")
            if st.button("Register Account"):
                if not reg_id or not reg_pw:
                    st.error("Fields cannot be empty.")
                elif reg_id in df_users["runner"].values:
                    st.error("Username already claimed.")
                else:
                    # Append new login straight to the Google Sheet users tab
                    new_user_row = pd.DataFrame([{"runner": reg_id, "password": reg_pw}])
                    updated_users = pd.concat([df_users, new_user_row], ignore_index=True)
                    conn.update(worksheet="users", data=updated_users)
                    st.success("Account saved to cloud! Please log in above.")
                    st.rerun()
    return False

if not check_user_login():
    st.stop()

current_user = st.session_state.logged_in_user

# Sidebar Logout Component
with st.sidebar:
    st.write(f"Logged in as: **{current_user}**")
    if st.button("Log Out"):
        st.session_state.logged_in_user = None
        st.rerun()

tab1, tab2 = st.tabs(["📊 My Running Records", "🏆 Global Leaderboard & Export"])

# --- Tab 1: Private Records Management (Isolated) ---
with tab1:
    st.header(f"👟 Track Records for {current_user}")
    rec_tab1, rec_tab2 = st.tabs(["Add Performance Log", "View & Clean My History"])
    
    with rec_tab1:
        run_date = st.date_input("Select Running Date").strftime("%Y-%m-%d")
        run_dist = st.number_input("Distance (km)", min_value=0.0, step=0.1)
        t_col1, t_col2, t_col3 = st.columns(3)
        with t_col1: hour = st.number_input("Hour (HH)", min_value=0, max_value=23, step=1, value=0)
        with t_col2: minute = st.number_input("Minute (MM)", min_value=0, max_value=59, step=1, value=25)
        with t_col3: second = st.number_input("Second (SS)", min_value=0, max_value=59, step=1, value=30)
        
        if st.button("Save Running Record"):
            new_run_row = pd.DataFrame([{"runner": current_user, "date": run_date, "distance": run_dist, "duration": f"{hour:02d}:{minute:02d}:{second:02d}"}])
            updated_runs = pd.concat([df_runs, new_run_row], ignore_index=True)
            conn.update(worksheet="running_data", data=updated_runs)
            st.success("Log saved permanently to cloud Google Sheet!")
            st.rerun()

    with rec_tab2:
        my_records = df_runs[df_runs["runner"] == current_user].sort_values(by="date")
        if my_records.empty: 
            st.info("No running history found on your profile yet.")
        else:
            for idx, (_, r) in enumerate(my_records.iterrows()):
                col_text, col_btn = st.columns([0.85, 0.15])
                with col_text:
                    r_pace = helpers.calculate_run_pace(float(r['distance']), str(r['duration']))
                    st.write(f"{idx+1}. **Date:** {r['date']} | **Dist:** {r['distance']}km | **Time:** {r['duration']} | **Pace:** {r_pace}")
                with col_btn:
                    if st.button("Delete", key=f"del_rec_{idx}"):
                        # Drop row based on internal index references
                        df_runs = df_runs.drop(r.name)
                        conn.update(worksheet="running_data", data=df_runs)
                        st.success("Record dropped from Google Sheet.")
                        st.rerun()

# --- Tab 2: Shared Leaderboard & Multi-Page PDF Reporting ---
with tab2:
    st.header("🏆 Family Comparison Leaderboard")
    
    # Render global calculations via helpers
    if df_runs.empty:
        st.info("No leaderboard entries recorded across profiles.")
    else:
        stats = helpers.calculate_stats_dataframe(df_runs)
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
                user_records = df_runs[df_runs["runner"] == user].sort_values(by="date")
                
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
            pdf_data = helpers.make_pdf_dataframe(stats, df_runs)
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