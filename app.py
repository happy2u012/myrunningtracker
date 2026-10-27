import streamlit as st
import pandas as pd
import helpers
import importlib
importlib.reload(helpers)  # 👈 Forces Python to reload helpers.py on every run
import time

# ==============================================================================
# PART 1: CONFIGURATION, STYLING & DATA LOADING
# ==============================================================================

# MUST be the absolute first Streamlit execution command
st.set_page_config(page_title="My Running Tracker", page_icon="🏃", layout="wide")

# --- CSS Injection to Hide Icons, Footers, and Add Background Image ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .viewerBadge_container__1QS1Y {display: none !important;}
    
    /* --- 🖼️ ORIGINAL FULL SCREEN BACKGROUND IMAGE STYLING --- */
    .stApp {
        background-image: url("https://i.postimg.cc/SRHWtKV2/image-880568f1.jpg");
        background-attachment: fixed;
        background-size: cover;
        background-position: center;
    }
    
    /* --- 🌆 Global Container Panels (Semi-Transparent White Cards) --- */
    div[data-testid="stExpander"], .stTabs, div[data-testid="stForm"] {
        background-color: rgba(255, 255, 255, 0.95) !important;
        padding: 1.5rem !important;
        border-radius: 10px !important;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1) !important;
    }

    /* --- 👟 Global Typography Color Settings (Dark Grey Ink) --- */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label,
    div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"] {
        color: #212529 !important;
    }

    /* --- 🛠️ MOBILE-FIRST FORCE LIGHT OVERRIDE --- */
    /* Forces light grey background colors across all input panels, grids, lists, and boxes */
    div[data-baseweb="input"], 
    div[data-testid="stDateInput"] div,
    div[data-testid="stDateInput"] button, 
    div[data-testid="stNumberInput"] div,
    div[data-testid="stNumberInput"] button,
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"],
    div[data-testid="stMultiSelect"] div,
    div[role="listbox"],
    div[data-baseweb="select"] div,
    div[data-testid="stExpander"] summary {
        background-color: #f1f3f5 !important;
        color: #212529 !important;
        border-radius: 6px !important;
        border: 1px solid #dee2e6 !important;
    }

    /* Force primary buttons (Download buttons, log out, action points) to have clear light styles */
    .stButton button, div[data-testid="stForm"] button, div[data-testid="stPopover"] button {
        background-color: #f1f3f5 !important;
        color: #212529 !important;
        border: 1px solid #dee2e6 !important;
    }

    /* Ensure deep-nested text strings inside forms, options tags, and tables print clearly */
    div[data-baseweb="input"] input, 
    div[data-testid="stDateInput"] input,
    div[data-testid="stNumberInput"] input,
    .stDataFrame div, 
    div[data-testid="stTable"] td, 
    div[data-testid="stTable"] th,
    .stButton button p,
    div[data-testid="stMultiSelect"] span,
    div[data-baseweb="select"] span,
    div[data-testid="stPopover"] p,
    div[data-testid="stExpander"] summary p {
        color: #212529 !important;
        background-color: transparent !important;
    }

    /* Format table headers to present clean background indicators */
    div[data-testid="stTable"] th {
        background-color: #e9ecef !important;
        font-weight: bold !important;
        color: #212529 !important;
    }
    div[data-testid="stTable"] tr:nth-child(even) {
        background-color: #f8f9fa !important;
    }

    /* Strip focus borders and browser-side default outline shadows */
    div[data-testid="stExpander"] summary:focus, 
    .stButton button:focus, 
    div[data-baseweb="input"]:focus-within {
        outline: none !important;
        box-shadow: none !important;
        border-color: #ced4da !important;
    }
    
    /* --- MOBILE RESPONSIVE OPTIMIZATION --- */
    @media (min-width: 768px) {
        input[type="password"] {-webkit-text-security: square;}
    }
    
    div[data-testid="stHorizontalBlock"] {
        gap: 1rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Security Brute-Force Counters
if "login_attempts" not in st.session_state: 
    st.session_state.login_attempts = 0
if "lockout_time" not in st.session_state: 
    st.session_state.lockout_time = 0.0

# --- Cloud Data Loader with 60-second TTL Caching ---
@st.cache_data(ttl=60, show_spinner=False)
def load_cloud_data():
    try:
        script_url = st.secrets["connections"]["gsheets"]["script_url"]
        
        df_u = pd.read_csv(f"{script_url}?sheet=users", on_bad_lines='skip')
        df_r = pd.read_csv(f"{script_url}?sheet=running_data", on_bad_lines='skip')
    except Exception as e:
        st.error(f"Live Apps Script API connection link error: {e}")
        df_u = pd.DataFrame(columns=["runner", "password"])
        df_r = pd.DataFrame(columns=["runner", "date", "distance", "duration"])
    
    df_u.columns = [str(c).lower().strip() for c in df_u.columns]
    df_r.columns = [str(c).lower().strip() for c in df_r.columns]
    
    if df_u.empty or "runner" not in df_u.columns:
        df_u = pd.DataFrame(columns=["runner", "password"])
        
    if df_r.empty or "runner" not in df_r.columns:
        df_r = pd.DataFrame(columns=["runner", "date", "distance", "duration"])
    else:
        if "date" in df_r.columns:
            df_r["date"] = df_r["date"].astype(str).apply(lambda x: x.split(" ")[0] if " " in x else x)
        if "duration" in df_r.columns:
            df_r["duration"] = df_r["duration"].astype(str).apply(lambda x: x.split(" ")[3] if len(x.split(" ")) > 3 else x)
        
    return df_u, df_r

# Initial Global Fetch
df_users, df_runs = load_cloud_data()
existing_users = sorted(df_users["runner"].dropna().astype(str).str.strip().unique().tolist()) if "runner" in df_users.columns else []


# ==============================================================================
# PART 2: AUTHENTICATION & ACCESS CONTROL
# ==============================================================================

# --- User Account Authentication Interface ---
def check_user_login():
    if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = None
    if "is_admin" not in st.session_state: st.session_state.is_admin = False
    if st.session_state.logged_in_user is not None: return True

    st.title("My Running Tracker")
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

            if login_id == st.secrets["admin"]["master_id"] and login_pw == st.secrets["admin"]["master_password"]:
                st.session_state.logged_in_user = login_id
                st.session_state.is_admin = True
                st.session_state.login_attempts = 0
                st.cache_data.clear()
                st.rerun()
            else:
                user_match = fresh_users[fresh_users["runner"].astype(str).str.strip() == str(login_id)]
                if not user_match.empty:
                    user_record = user_match.to_dict(orient="records")[0]
                    stored_hash = str(user_record.get("password", ""))

                    if helpers.verify_password(login_pw, stored_hash):
                        st.session_state.logged_in_user = login_id
                        st.session_state.is_admin = False
                        st.session_state.login_attempts = 0
                        st.cache_data.clear()
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
            with st.form("registration_form", clear_on_submit=True):
                reg_id = st.text_input("Choose Runner ID").strip()
                reg_pw = st.text_input("Choose Password", type="password")
                submit_reg = st.form_submit_button("Submit Registration", use_container_width=True)

                if submit_reg:
                    if not reg_id or not reg_pw:
                        st.error("All fields are required.")
                    elif reg_id in existing_users or reg_id == st.secrets["admin"]["master_id"]:
                        st.error("ID taken.")
                    elif len(reg_pw) < 6:
                        st.error("Password must be >= 6 characters.")
                    else:
                        if helpers.post_to_google_sheet({"sheet": "users", "runner": reg_id, "password": helpers.hash_password(reg_pw)}):
                            st.success("Account created! You can now log in.")
                            st.cache_data.clear()
                        else:
                            st.error("Registration failed.")
    return False

if not check_user_login(): 
    st.stop()

current_user = st.session_state.logged_in_user
is_admin = st.session_state.is_admin

if is_admin:
    df_users, df_runs = load_cloud_data()
    existing_users = sorted(df_users["runner"].dropna().astype(str).str.strip().unique().tolist()) if "runner" in df_users.columns else []


# ==============================================================================
# PART 3: MAIN DASHBOARD & TAB NAVIGATION
# ==============================================================================

# Sidebar User Info & Logout Button
with st.sidebar:
    st.write(f"Logged in as: **{current_user}** " + ("(Admin ⚙️)" if is_admin else ""))
    if st.button("Log Out"): 
        st.session_state.logged_in_user = None
        st.session_state.is_admin = False
        st.rerun()

# Dynamic Tab Provisioning
if is_admin:
    tab_records, tab_leaderboard, tab_admin = st.tabs([
        "📊 My Running Records", 
        "🏆 All Runners Leaderboard", 
        "⚙️ Admin Management Console"
    ])
else:
    tab_records, tab_leaderboard = st.tabs([
        "📊 My Running Records", 
        "🏆 All Leaderboard"
    ])

# --- Tab 1: Private Records Management ---
with tab_records:
    st.header(f"👟 Track Records for {current_user}")
    rec_tab1, rec_tab2 = st.tabs(["Add Performance Log", "View, Edit & Delete History"])
    
    with rec_tab1:
        with st.form("add_record_form", clear_on_submit=True):
            run_date = st.date_input("Select Running Date")
            run_dist = st.number_input("Distance (km)", min_value=0.0, step=0.1)
            t_col1, t_col2, t_col3 = st.columns(3)
            with t_col1: hour = st.number_input("Hour (HH)", min_value=0, max_value=23, step=1, value=0)
            with t_col2: minute = st.number_input("Minute (MM)", min_value=0, max_value=59, step=1, value=25)
            with t_col3: second = st.number_input("Second (SS)", min_value=0, max_value=59, step=1, value=30)
            submit_run = st.form_submit_button("Save Running Record", use_container_width=True)
            
            if submit_run:
                formatted_date = run_date.strftime("%Y-%m-%d")
                if helpers.post_to_google_sheet({
                    "sheet": "running_data", 
                    "runner": current_user, 
                    "date": formatted_date, 
                    "distance": run_dist, 
                    "duration": f"{hour:02d}:{minute:02d}:{second:02d}"
                }):
                    st.success("Log saved to Google Sheet!")
                    st.cache_data.clear()
                    st.rerun()
                else: 
                    st.error("Save failed.")
            
    with rec_tab2:
        my_records = df_runs[df_runs["runner"].astype(str).str.strip() == current_user].sort_values(by="date")
        
        if my_records.empty:
            st.info("No running history found.")
        else:
            formatted_my_data = []
            for i, (_, r) in enumerate(my_records.iterrows(), 1):
                formatted_my_data.append({
                    "No.": i, 
                    "Date": r["date"], 
                    "Distance": f"{r['distance']} km", 
                    "Duration": r["duration"], 
                    "Pace": helpers.calculate_run_pace(float(r['distance']), str(r['duration']))
                })
            st.dataframe(formatted_my_data, use_container_width=True, hide_index=True)
            
            st.write("---")
            with st.expander("🛠️ Manage a Specific Record Entry (Edit or Delete)", expanded=False):
                st.write("Select the **No.** from the table above to modify or permanently remove it.")
                
                record_indices = [item["No."] for item in formatted_my_data]
                selected_no = st.selectbox("Select Record Number to Modify/Delete:", options=record_indices)
                
                current_target_row = formatted_my_data[selected_no - 1]
                raw_dist_float = float(current_target_row["Distance"].replace(" km", ""))
                
                try:
                    ch, cm, cs = map(int, current_target_row["Duration"].split(":"))
                except Exception:
                    ch, cm, cs = 0, 25, 0
                
                # Protective date parsing
                try:
                    parsed_value_date = pd.to_datetime(current_target_row["Date"], errors='coerce', format='mixed')
                    if pd.isna(parsed_value_date):
                        fallback_default_date = pd.Timestamp.now()
                    else:
                        fallback_default_date = parsed_value_date
                except Exception:
                    fallback_default_date = pd.Timestamp.now()
                
                edit_date = st.date_input("Modify Running Date", value=fallback_default_date)
                edit_dist = st.number_input("Modify Distance (km)", min_value=0.0, step=0.1, value=raw_dist_float)
                
                ec1, ec2, ec3 = st.columns(3)
                with ec1: edit_hour = st.number_input("Edit Hour", min_value=0, max_value=23, value=ch)
                with ec2: edit_min = st.number_input("Edit Minute", min_value=0, max_value=59, value=cm)
                with ec3: edit_sec = st.number_input("Edit Second", min_value=0, max_value=59, value=cs)
                
                btn_col1, btn_col2 = st.columns(2)
                
                with btn_col1:
                    if st.button("💾 Save Entry Modifications", type="primary", use_container_width=True):
                        payload = {
                            "sheet": "running_data",
                            "action": "edit",
                            "record_index": selected_no,
                            "runner": current_user,
                            "date": edit_date.strftime("%Y-%m-%d"),
                            "distance": edit_dist,
                            "duration": f"{edit_hour:02d}:{edit_min:02d}:{edit_sec:02d}"
                        }
                        if helpers.post_to_google_sheet(payload):
                            st.success(f"Record No. {selected_no} updated successfully!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Failed to transmit dataset modification updates to spreadsheet.")
                            
                with btn_col2:
                    if st.button("🗑️ Delete This Record Entry", type="secondary", use_container_width=True):
                        payload = {
                            "sheet": "running_data",
                            "action": "delete_record",
                            "record_index": selected_no,
                            "runner": current_user
                        }
                        if helpers.post_to_google_sheet(payload):
                            st.success(f"Record No. {selected_no} deleted successfully!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Failed to execute deletion request on spreadsheet.")

# --- Tab 2: Shared Leaderboard & Multiselect Exporter ---
with tab_leaderboard:
    st.header("🏆 All Runners Leaderboard")
    all_runners = []
    stats = {}
    
    valid_runs = df_runs.dropna(subset=["runner", "distance", "duration"])
    if not valid_runs.empty and "date" in valid_runs.columns: 
        valid_runs = valid_runs[valid_runs["date"].astype(str).str.strip() != ""]
    
    if valid_runs.empty: 
        st.info("No leaderboard entries recorded yet. Add your first running record in the first tab!")
    else:
        stats = helpers.calculate_stats_dataframe(valid_runs)
        raw_runners = list(stats.keys())
        
        if current_user in raw_runners:
            all_runners = [current_user] + [r for r in raw_runners if r != current_user]
        else:
            all_runners = raw_runners
            
        for user in all_runners:
            s = stats[user]
            is_me = (user == current_user)
            card_title = f"⭐ My Account Profile: {user} (You)" if is_me else f"👤 Runner Account: {user}"
            
            with st.expander(card_title, expanded=is_me):
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
                    if user_records.empty: 
                        st.info("No logs tracked.")
                    else:
                        formatted_table_data = [{"No.": i, "Date": r["date"], "Distance": f"{r['distance']} km", "Duration": r["duration"]} for i, (_, r) in enumerate(user_records.iterrows(), 1)]
                        st.dataframe(formatted_table_data, use_container_width=True, hide_index=True)
                with col_chart:
                    st.write("#### 📊 Progress")
                    helpers.draw_mileage_chart(user_records, s["Total Distance (km)"], user)

    st.write("---")
    st.subheader("💾 Export Leaderboard Metrics")
    
    if len(all_runners) > 0:
        selected_runners = st.multiselect("Select Runners to Include in Export File:", options=all_runners, default=all_runners)
        if selected_runners:
            # Preserve the display order (logged-in user first) in the exported stats dictionary
            filtered_stats = {k: stats[k] for k in selected_runners if k in stats}
            ex_col1, ex_col2 = st.columns(2)
            with ex_col1:
                st.download_button(
                    label="📥 Download Dataset as CSV", 
                    data=helpers.make_csv(filtered_stats), 
                    file_name="running_leaderboard_export.csv", 
                    mime="text/csv", 
                    use_container_width=True
                )
            with ex_col2:
                st.download_button(
                    label="📥 Download Performance Report as PDF", 
                    data=helpers.make_pdf_dataframe(filtered_stats, valid_runs), 
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
        st.success("Welcome authorized Administrator. Core user identity systems active.")
        
        admin_col1, admin_col2 = st.columns(2)
        
        with admin_col1:
            st.write("### ➕ Provision New User Profile")
            with st.form("admin_provision_form", clear_on_submit=True):
                new_id = st.text_input("Assign Runner ID").strip()
                new_pw = st.text_input("Assign Temp Password", type="password")
                submit_provision = st.form_submit_button("Create Account Profile", use_container_width=True)
                
                if submit_provision:
                    if not new_id or not new_pw:
                        st.error("Both user account fields are required.")
                    elif new_id in existing_users:
                        st.error("This Runner ID already exists inside the database.")
                    elif len(new_pw) < 6:
                        st.error("Password string must be at least 6 characters.")
                    else:
                        payload = {"sheet": "users", "action": "create", "runner": new_id, "password": helpers.hash_password(new_pw)}
                        if helpers.post_to_google_sheet(payload):
                            st.success(f"Profile for '{new_id}' provisioned successfully!")
                            st.cache_data.clear()
                            st.rerun()
                        else: 
                            st.error("Provisioning backend failed to append row.")
                        
        with admin_col2:
            st.write("### 🗑️ Deprovision User Account Profile")
            if len(existing_users) > 0:
                user_to_delete = st.selectbox("Select Profile to Permanently Delete:", options=existing_users)
                confirm_delete = st.checkbox(f"I confirm I want to permanently delete user account: **{user_to_delete}**")
                
                if st.button("Delete Account Profile", type="primary", use_container_width=True):
                    if not confirm_delete:
                        st.warning("Please check the confirmation safety box before running account deletions.")
                    else:
                        payload = {"sheet": "users", "action": "delete", "runner": user_to_delete}
                        if helpers.post_to_google_sheet(payload):
                            st.success(f"Account profile '{user_to_delete}' has been completely removed.")
                            st.cache_data.clear()
                            st.rerun()
                        else: 
                            st.error("Deletion API endpoint returned a processing execution failure.")
            else:
                st.info("No active runner account profiles found to drop.")

        st.write("---")
        st.write("### 👥 Master Identity Row Ledger Preview")
        if not df_users.empty:
            st.dataframe(df_users, use_container_width=True, hide_index=True)
        else:
            st.warning("User database ledger dataframe is empty or uninitialized.")

# --- Footer Logout Control ---
st.write("---")
c_foot1, c_foot2 = st.columns(2)
with c_foot2:
    if st.button("🚪 Leave Application / Log Out", use_container_width=True, key="admin_footer_logout"):
        st.session_state.logged_in_user = None
        st.session_state.is_admin = False
        st.rerun()
