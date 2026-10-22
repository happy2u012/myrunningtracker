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
    
    /* --- MOBILE RESPONSIVE OPTIMIZATION --- */
    /* Only apply password security styling on screens wider than a mobile phone */
    @media (min-width: 768px) {
        input[type="password"] {-webkit-text-security: square;}
    }
    
    /* Force form containers and tables to wrap smoothly on narrow viewports */
    div[data-testid="stHorizontalBlock"] {
        gap: 1rem !important;
    }
    </style>
""", unsafe_allow_html=True)

import pandas as pd
import helpers
import time

# --- Initialize Security Brute-Force Counters ---
if "login_attempts" not in st.session_state: st.session_state.login_attempts = 0
if "lockout_time" not in st.session_state: st.session_state.lockout_time = 0.0

def load_cloud_data():
    try:
        ts = int(time.time())
        u_url = st.secrets["connections"]["gsheets"]["users_url"]
        r_url = st.secrets["connections"]["gsheets"]["runs_url"]
        
        u_sep = "&" if "?" in u_url else "?"
        r_sep = "&" if "?" in r_url else "?"
        
        # Appending t=ts forces Google Cloud to bypass cache parameters and return live rows
        df_u = pd.read_csv(f"{u_url}{u_sep}t={ts}", on_bad_lines='skip')
        df_r = pd.read_csv(f"{r_url}{r_sep}t={ts}", on_bad_lines='skip')
    except Exception as e:
        st.error(f"Spreadsheet connection error: {e}")
        df_u = pd.DataFrame(columns=["runner", "password"])
        df_r = pd.DataFrame(columns=["runner", "date", "distance", "duration"])
    
    # Normalize column headers to lowercase strings safely
    df_u.columns = [str(c).lower().strip() for c in df_u.columns]
    df_r.columns = [str(c).lower().strip() for c in df_r.columns]
    
    if df_u.empty or "runner" not in df_u.columns:
        df_u = pd.DataFrame(columns=["runner", "password"])
    if df_r.empty or "runner" not in df_r.columns:
        df_r = pd.DataFrame(columns=["runner", "date", "distance", "duration"])
        
    return df_u, df_r

df_users, df_runs = load_cloud_data()
existing_users = sorted(df_users["runner"].dropna().astype(str).str.strip().unique().tolist()) if "runner" in df_users.columns else []

# --- User Account Authentication Interface ---
def check_user_login():
    if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = None
    if "is_admin" not in st.session_state: st.session_state.is_admin = False
    if st.session_state.logged_in_user is not None: return True

    st.title("🔒 Running Tracker Account Login")
    current_time = time.time()
    if st.session_state.login_attempts >= 5 and (st.session_state.lockout_time - current_time) > 0:
        st.error(f"🚨 System locked. Try again in {int(st.session_state.lockout_time - current_time)} seconds.")
        return False

    login_id = st.text_input("Username / ID", key="login_user_input").strip()
    login_pw = st.text_input("Password", type="password", key="login_pass_input")
    col_login, col_reg = st.columns(2)
    
    with col_login:
        if st.button("Login", use_container_width=True):
            fresh_users, fresh_runs = load_cloud_data()
            
            # 1. Admin Master Credentials Authentication Branch
            if login_id == st.secrets["admin"]["master_id"] and login_pw == st.secrets["admin"]["master_password"]:
                st.session_state.logged_in_user = login_id
                st.session_state.is_admin = True
                st.session_state.login_attempts = 0
                st.rerun()
            
            # 2. Standard User Account Spreadsheet Row Matching Branch
            else:
                user_match = fresh_users[fresh_users["runner"].astype(str).str.strip() == str(login_id)]
                
                if not user_match.empty:
                    user_record = user_match.to_dict(orient="records")[0]
                    stored_hash = str(user_record.get("password", "")).strip().lower()
                    input_hash = str(helpers.hash_password(login_pw)).strip().lower()
                    
                    if stored_hash == input_hash:
                        st.session_state.logged_in_user = login_id
                        st.session_state.is_admin = False
                        st.session_state.login_attempts = 0
                        st.rerun()
                    else:
                        st.session_state.login_attempts += 1
                        st.error("Invalid credentials.")
                else:
                    st.session_state.login_attempts += 1
                    st.error("Invalid credentials.")
                
                if st.session_state.login_attempts >= 5: 
                    st.session_state.lockout_time = time.time() + 900
                
    with col_reg:
        with st.popover("Create New Account", use_container_width=True):
            reg_id = st.text_input("Choose Runner ID", key="reg_user_input").strip()
            reg_pw = st.text_input("Choose Password", type="password", key="reg_pass_input")
            if st.button("Submit Registration"):
                if not reg_id or not reg_pw: st.error("All fields are required.")
                elif reg_id in existing_users or reg_id == st.secrets["admin"]["master_id"]: st.error("ID taken.")
                elif len(reg_pw) < 6: st.error("Password must be >= 6 characters.")
                else:
                    if helpers.post_to_google_sheet({"sheet": "users", "runner": reg_id, "password": helpers.hash_password(reg_pw)}):
                        st.success("Account created successfully! You can now log in.")
                        st.cache_data.clear()
                    else: 
                        st.error("Registration failed.")
    return False

if not check_user_login(): st.stop()
current_user, is_admin = st.session_state.logged_in_user, st.session_state.is_admin

with st.sidebar:
    st.write(f"Logged in as: **{current_user}** " + ("(Admin ⚙️)" if is_admin else ""))
    if st.button("Log Out"): 
        st.session_state.logged_in_user = None
        st.session_state.is_admin = False
        st.rerun()
# --- Unpacking Tabs ---
if is_admin:
    tab_records, tab_leaderboard, tab_admin = st.tabs([
        "📊 My Running Records", 
        "🏆 Global Leaderboard & Export", 
        "⚙️ Admin Management Console"
    ])
else:
    tab_records, tab_leaderboard = st.tabs([
        "📊 My Running Records", 
        "🏆 Global Leaderboard & Export"
    ])

# --- Tab 1: Private Records Management ---
with tab_records:
    st.header(f"👟 Track Records for {current_user}")
    rec_tab1, rec_tab2 = st.tabs(["Add Performance Log", "View My History"])
    with rec_tab1:
        run_date = st.date_input("Select Running Date").strftime("%Y-%m-%d")
        run_dist = st.number_input("Distance (km)", min_value=0.0, step=0.1)
        t_col1, t_col2, t_col3 = st.columns(3)
        with t_col1: hour = st.number_input("Hour (HH)", min_value=0, max_value=23, step=1, value=0)
        with t_col2: minute = st.number_input("Minute (MM)", min_value=0, max_value=59, step=1, value=25)
        with t_col3: second = st.number_input("Second (SS)", min_value=0, max_value=59, step=1, value=30)
        if st.button("Save Running Record"):
            if helpers.post_to_google_sheet({"sheet": "running_data", "runner": current_user, "date": run_date, "distance": run_dist, "duration": f"{hour:02d}:{minute:02d}:{second:02d}"}):
                st.success("Log saved to Google Sheet!")
                st.cache_data.clear()
                st.rerun()
            else: st.error("Save failed.")
    with rec_tab2:
        my_records = df_runs[df_runs["runner"].astype(str).str.strip() == current_user].sort_values(by="date")
        if my_records.empty: st.info("No running history found.")
        else:
            formatted_my_data = [{"No.": i, "Date": r["date"], "Distance": f"{r['distance']} km", "Duration": r["duration"], "Pace": helpers.calculate_run_pace(float(r['distance']), str(r['duration']))} for i, (_, r) in enumerate(my_records.iterrows(), 1)]
            st.dataframe(formatted_my_data, use_container_width=True, hide_index=True)

# --- Tab 2: Shared Leaderboard & Multiselect Exporter ---
with tab_leaderboard:
    st.header("🏆 Family Comparison Leaderboard")
    
    # Initialize variables cleanly so they exist regardless of conditions
    all_runners = []
    stats = {}
    
    valid_runs = df_runs.dropna(subset=["runner", "distance", "duration"])
    if not valid_runs.empty and "date" in valid_runs.columns: 
        valid_runs = valid_runs[valid_runs["date"].astype(str).str.strip() != ""]
    
    if valid_runs.empty: 
        st.info("No leaderboard entries recorded yet. Add your first running record in the first tab!")
    else:
        stats = helpers.calculate_stats_dataframe(valid_runs)
        all_runners = list(stats.keys())
        for user, s in stats.items():
            with st.expander(f"👤 Runner Account: {user}", expanded=True):
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total Runs", f"{s['Total Days']} Days")
                m2.metric("Cumulative Distance", f"{s['Total Distance (km)']} km")
                m3.metric("Total Duration", s['Total Time'])
                m4.metric("Average Distance", f"{s['Avg Distance (km)']} km")
                m5.metric("Average Pace", s['Avg Pace'])
                st.write("---")
                
                col_table, col_chart = st.columns(2)
                user_records = valid_runs[valid_runs["runner"].astype(str).str.strip() == user].sort_values(by="date")
                with col_table:
                    st.write("#### 🗓️ Log Sheets")
                    if user_records.empty: st.info("No logs tracked.")
                    else:
                        formatted_table_data = [{"No.": i, "Date": r["date"], "Distance": f"{r['distance']} km", "Duration": r["duration"]} for i, (_, r) in enumerate(user_records.iterrows(), 1)]
                        st.dataframe(formatted_table_data, use_container_width=True, hide_index=True)
                with col_chart:
                    st.write("#### 📊 Progress")
                    helpers.draw_mileage_chart(user_records, s["Total Distance (km)"], user)

    # --- EXPORT WIDGET CONTROL INTERFACE ---
    st.write("---")
    st.subheader("💾 Export Leaderboard Metrics")
    
    if len(all_runners) > 0:
        selected_runners = st.multiselect(
            "Select Runners to Include in Export File:",
            options=all_runners,
            default=all_runners
        )
        
        if selected_runners:
            filtered_stats = {k: v for k, v in stats.items() if k in selected_runners}
            ex_col1, ex_col2 = st.columns(2)
            
            with ex_col1:
                csv_data = helpers.make_csv(filtered_stats)
                st.download_button(
                    label="📥 Download Dataset as CSV",
                    data=csv_data,
                    file_name="running_leaderboard_export.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
            with ex_col2:
                pdf_data = helpers.make_pdf_dataframe(filtered_stats, valid_runs)
                st.download_button(
                    label="📥 Download Performance Report as PDF",
                    data=pdf_data,
                    file_name="running_leaderboard_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.warning("Please choose at least one runner from the selector dropdown menu to export files.")
    else:
        st.info("Export options will appear once running logs are saved in the system.")

# --- Tab 3: Admin Management Console ---
if is_admin:
    with tab_admin:
        st.header("⚙️ Admin Management Console")
        st.success("Welcome authorized Administrator. System core running components stable.")
        st.write("### 👥 System User Database Control")
        st.dataframe(df_users, use_container_width=True, hide_index=True)