import streamlit as st

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

import json
import os
import helpers
import matplotlib.pyplot as plt

DATA_FILE = "running_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            # Seamless migration for legacy data models to authorization dictionary models
            clean_data = {}
            for k, v in raw_data.items():
                if isinstance(v, list):
                    clean_data[k] = {"password": "familyrunner!", "records": v}
                else:
                    clean_data[k] = v
            return clean_data
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- Individual Account Authentication Prompt Logic ---
def check_user_login():
    if "logged_in_user" not in st.session_state:
        st.session_state.logged_in_user = None

    if st.session_state.logged_in_user is not None:
        return True

    st.title("🔒 Running Tracker Account Login")
    data = load_data()
    
    login_id = st.text_input("Username / ID").strip()
    login_pw = st.text_input("Password", type="password")
    
    col_login, col_reg = st.columns(2)
    with col_login:
        if st.button("Login", use_container_width=True):
            if login_id in data and data[login_id]["password"] == login_pw:
                st.session_state.logged_in_user = login_id
                st.success(f"Welcome back, {login_id}!")
                st.rerun()
            else:
                st.error("Invalid username or password configuration.")
                
    with col_reg:
        # Give family members structural freedom to spin up new isolated profiles directly
        with st.popover("Create New Account", use_container_width=True):
            reg_id = st.text_input("New Runner ID").strip()
            reg_pw = st.text_input("New Password", type="password", key="reg_pw")
            if st.button("Register Account"):
                if not reg_id or not reg_pw:
                    st.error("Fields cannot be empty.")
                elif reg_id in data:
                    st.error("Username already claimed.")
                else:
                    data[reg_id] = {"password": reg_pw, "records": []}
                    save_data(data)
                    st.success("Account initialized! Please log in above.")
                    st.rerun()
    return False

if not check_user_login():
    st.stop()

# Load isolated context profile markers
data = load_data()
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
            data[current_user]["records"].append({
                "date": run_date, "distance": run_dist, "duration": f"{hour:02d}:{minute:02d}:{second:02d}"
            })
            data[current_user]["records"] = sorted(data[current_user]["records"], key=lambda x: x['date'])
            save_data(data)
            st.success("Log saved cleanly to your profile array!")
            st.rerun()

    with rec_tab2:
        my_records = data[current_user]["records"]
        if not my_records: 
            st.info("No running history found on your profile yet.")
        else:
            for idx, r in enumerate(my_records):
                col_text, col_btn = st.columns([0.85, 0.15])
                with col_text:
                    r_pace = helpers.calculate_run_pace(r['distance'], r['duration'])
                    st.write(f"{idx+1}. **Date:** {r['date']} | **Dist:** {r['distance']}km | **Time:** {r['duration']} | **Pace:** {r_pace}")
                with col_btn:
                    if st.button("Delete", key=f"del_rec_{idx}"):
                        my_records.pop(idx)
                        save_data(data)
                        st.success("Record dropped.")
                        st.rerun()

# --- Tab 2: Shared Leaderboard & Multi-Page PDF Reporting ---
with tab2:
    st.header("🏆 Family Comparison Leaderboard")
    stats = helpers.calculate_stats(data)
    
    if not stats:
        st.info("No leaderboard entries recorded across profiles.")
    else:
        for user, s in stats.items():
            with st.expander(f"👤 Runner Account: {user}", expanded=True):
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total Runs", f"{s['Total Days']} Days")
                m2.metric("Cumulative Distance", f"{s['Total Distance (km)']} km")
                m3.metric("Total Duration", s['Total Time'])
                m4.metric("Average Distance", f"{s['Avg Distance (km)']} km")
                m5.metric("Average Pace", s['Avg Pace'])
                
                st.write("---")
                col_table, col_chart = st.columns([4, 3])
                
                user_info = data.get(user, {})
                user_records = user_info.get("records", []) if isinstance(user_info, dict) else user_info
                sorted_records = sorted(user_records, key=lambda x: x['date'])
                
                with col_table:
                    st.write("#### 🗓️ Log Sheets")
                    if not user_records: 
                        st.info("This user has no activity logs tracked.")
                    else:
                        formatted_table_data = []
                        for idx, run in enumerate(sorted_records, 1):
                            formatted_table_data.append({
                                "No.": idx, "Date": run["date"], "Distance": f"{run['distance']} km",
                                "Duration": run["duration"], "Pace": helpers.calculate_run_pace(run['distance'], run['duration'])
                            })
                        st.dataframe(formatted_table_data, use_container_width=True, hide_index=True)
                        
                with col_chart:
                    st.write("#### 📊 Mileage Bar Chart")
                    if not user_records: 
                        st.info("No graph plots available.")
                    else:
                        fig, ax = plt.subplots(figsize=(6, max(2.5, len(sorted_records) * 0.4)))
                        
                        # FIX: Invert chart alignment sequences to place TOTAL at the bottom
                        labels = [run['date'] for run in sorted_records] + ["TOTAL"]
                        distances = [run['distance'] for run in sorted_records] + [s['Total Distance (km)']]
                        colors = ['#a6c8e0'] * len(sorted_records) + ['#1f4e79']
                        
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
            pdf_data = helpers.make_pdf(stats, data)
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