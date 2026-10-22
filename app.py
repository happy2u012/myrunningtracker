import streamlit as st

# FIX: st.set_page_config MUST be the absolute first Streamlit command executed
st.set_page_config(page_title="My Running Tracker", page_icon="🏃", layout="wide")

# --- Simple Password Protection Function ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.title("🔒 My Running Tracker Login")
    password = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        if password == "highclassrunners!": 
            st.session_state.password_correct = True
            st.success("Access Granted!")
            st.rerun()
        else:
            st.error("Incorrect password")
    return False

if not check_password():
    st.stop() # Halts dashboard initialization until correct password matching

# --- Core Dependencies & Imports ---
import json
import os
import helpers
import matplotlib.pyplot as plt

DATA_FILE = "running_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

st.title("🏃 My Running Tracker Dashboard")

if 'data' not in st.session_state:
    st.session_state.data = load_data()

data = st.session_state.data
tab1, tab2, tab3 = st.tabs(["👤 Manage Users", "📊 Manage Records", "🏆 Leaderboard & Export"])

# --- Tab 1: Manage Users ---
with tab1:
    st.header("User Management")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add New User")
        new_name = st.text_input("Enter name to register", key="add_user_input").strip()
        if st.button("Register User"):
            if not new_name: st.error("Name field cannot be empty.")
            elif new_name in data: st.warning("User already exists.")
            else:
                data[new_name] = []
                save_data(data)
                st.success(f"User '{new_name}' registered.")
                st.rerun()
    with col2:
        st.subheader("Delete User")
        if data:
            del_name = st.selectbox("Select user to delete", list(data.keys()), key="del_user_select")
            if st.button("Delete User", type="primary"):
                del data[del_name]
                save_data(data)
                st.success(f"User '{del_name}' removed.")
                st.rerun()
        else: st.info("No users registered yet.")

    st.subheader("Registered Users List")
    if data:
        for user in data.keys(): st.write(f"- **{user}** ({len(data[user])} records)")
    else: st.info("Please register a user first.")

# --- Tab 2: Manage Records ---
with tab2:
    st.header("Running Records Management")
    if not data: st.info("Please register a user first.")
    else:
        selected_user = st.selectbox("Select user", list(data.keys()), key="record_user_select")
        rec_tab1, rec_tab2 = st.tabs(["Add Record", "View & Delete Records"])

        with rec_tab1:
            run_date = st.date_input("Select Running Date").strftime("%Y-%m-%d")
            run_dist = st.number_input("Distance (km)", min_value=0.0, step=0.1)
            t_col1, t_col2, t_col3 = st.columns(3)
            with t_col1: hour = st.number_input("Hour (HH)", min_value=0, max_value=23, step=1, value=0)
            with t_col2: minute = st.number_input("Minute (MM)", min_value=0, max_value=59, step=1, value=25)
            with t_col3: second = st.number_input("Second (SS)", min_value=0, max_value=59, step=1, value=30)

            if st.button("Add Running Record"):
                data[selected_user].append({"date": run_date, "distance": run_dist, "duration": f"{hour:02d}:{minute:02d}:{second:02d}"})
                data[selected_user] = sorted(data[selected_user], key=lambda x: x['date'])
                save_data(data)
                st.success("Record added successfully!")
                st.rerun()

        with rec_tab2:
            records = data[selected_user]
            if not records: st.info("No running history found.")
            else:
                for idx, r in enumerate(records):
                    col_text, col_btn = st.columns([4, 1])
                    with col_text:
                        r_pace = helpers.calculate_run_pace(r['distance'], r['duration'])
                        st.write(f"{idx+1}. **Date:** {r['date']} | **Dist:** {r['distance']}km | **Time:** {r['duration']} | **Pace:** {r_pace}")
                    with col_btn:
                        if st.button("Delete", key=f"del_rec_{selected_user}_{idx}"):
                            records.pop(idx)
                            save_data(data)
                            st.success("Record deleted.")
                            st.rerun()

# --- Tab 3: Leaderboard & Export ---
with tab3:
    st.header("🏆 User Comparison Leaderboard")
    if not data: st.info("No data available.")
    else:
        stats = helpers.calculate_stats(data)
        for user, s in stats.items():
            with st.expander(f"👤 Runner: {user}", expanded=True):
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total Runs", f"{s['Total Days']} Days")
                m2.metric("Cumulative Distance", f"{s['Total Distance (km)']} km")
                m3.metric("Total Duration", s['Total Time'])
                m4.metric("Average Distance", f"{s['Avg Distance (km)']} km")
                m5.metric("Average Pace", s['Avg Pace'])

                st.write("---")

                col_table, col_chart = st.columns([4, 3])
                user_records = data.get(user, [])
                sorted_records = sorted(user_records, key=lambda x: x['date'])

                with col_table:
                    st.write("#### 🗓️ Running History by Date")
                    if not user_records: st.info("No run logs tracked yet.")
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
                    if not user_records: st.info("Add running records to display chart visualizations.")
                    else:
                        fig, ax = plt.subplots(figsize=(6, max(2.5, len(sorted_records) * 0.4)))
                        labels = ["TOTAL"] + [run['date'] for run in sorted_records]
                        distances = [s['Total Distance (km)']] + [run['distance'] for run in sorted_records]
                        colors = ['#1f4e79'] + ['#a6c8e0'] * len(sorted_records)

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

        st.subheader("📥 Export Data")
        csv_data = helpers.make_csv(stats)
        
        # FIX: Completed the missing/truncated exception structure from previous paste
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