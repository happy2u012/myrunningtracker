import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import helpers
import matplotlib.pyplot as plt

st.set_page_config(page_title="My Running Tracker", page_icon="🏃", layout="wide")
st.title("🏃 My Running Tracker Dashboard")

# --- Initialize Google Sheets Database Connection ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Read current records
df = conn.read(worksheet="running_data", ttl=0)
# Ensure columns exist even if sheet is completely blank
if df.empty or len(df.columns) < 4:
    df = pd.DataFrame(columns=["runner", "date", "distance", "duration"])

# Maintain an explicit list of existing users from the rows
existing_users = sorted(df["runner"].dropna().unique().tolist())

tab1, tab2, tab3 = st.tabs(["👤 Manage Users", "📊 Manage Records", "🏆 Leaderboard & Export"])

# --- Tab 1: Manage Users ---
with tab1:
    st.header("User Management")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Add New User")
        new_name = st.text_input("Enter name to register", key="add_user_input").strip()
        if st.button("Register User"):
            if not new_name:
                st.error("Name field cannot be empty.")
            elif new_name in existing_users:
                st.warning("User already exists.")
            else:
                # Add placeholder row to claim the user name
                new_row = pd.DataFrame([{"runner": new_name, "date": "", "distance": 0.0, "duration": "00:00:00"}])
                df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="running_data", data=df)
                st.success(f"User '{new_name}' registered successfully.")
                st.invalidate_pages() # Refresh the view
                st.rerun()

    with col2:
        st.subheader("Delete User")
        if existing_users:
            del_name = st.selectbox("Select user to delete", existing_users, key="del_user_select")
            if st.button("Delete User", type="primary"):
                df = df[df["runner"] != del_name]
                conn.update(worksheet="running_data", data=df)
                st.success(f"User '{del_name}' and all associated logs removed.")
                st.invalidate_pages()
                st.rerun()
        else:
            st.info("No users registered yet.")

    st.subheader("Registered Users List")
    if existing_users:
        for user in existing_users:
            user_runs = df[(df["runner"] == user) & (df["date"] != "")]
            st.write(f"- **{user}** ({len(user_runs)} activity records)")
    else:
        st.info("Please register a user first.")

# --- Tab 2: Manage Records ---
with tab2:
    st.header("Running Records Management")
    if not existing_users:
        st.info("Please register a user first to manage running records.")
    else:
        selected_user = st.selectbox("Select user", existing_users, key="record_user_select")
        rec_tab1, rec_tab2 = st.tabs(["Add Record", "View & Delete Records"])
        
        with rec_tab1:
            run_date = st.date_input("Select Running Date").strftime("%Y-%m-%d")
            run_dist = st.number_input("Distance (km)", min_value=0.0, step=0.1)
            
            t_col1, t_col2, t_col3 = st.columns(3)
            with t_col1: hour = st.number_input("Hour (HH)", min_value=0, max_value=23, step=1, value=0)
            with t_col2: minute = st.number_input("Minute (MM)", min_value=0, max_value=59, step=1, value=25)
            with t_col3: second = st.number_input("Second (SS)", min_value=0, max_value=59, step=1, value=30)
            duration_str = f"{hour:02d}:{minute:02d}:{second:02d}"
            
            if st.button("Add Running Record"):
                # Clean out dummy rows if logging first run for user
                df = df[~((df["runner"] == selected_user) & (df["date"] == ""))]
                
                new_record = pd.DataFrame([{"runner": selected_user, "date": run_date, "distance": run_dist, "duration": duration_str}])
                df = pd.concat([df, new_record], ignore_index=True)
                conn.update(worksheet="running_data", data=df)
                st.success("Record appended straight to Google Sheet!")
                st.invalidate_pages()
                st.rerun()

        with rec_tab2:
            user_records = df[(df["runner"] == selected_user) & (df["date"] != "")].sort_values(by="date")
            if user_records.empty:
                st.info("No running history found.")
            else:
                for idx, (_, r) in enumerate(user_records.iterrows()):
                    col_text, col_btn = st.columns([0.8, 0.2])
                    with col_text:
                        r_pace = helpers.calculate_run_pace(float(r['distance']), str(r['duration']))
                        st.write(f"{idx+1}. **Date:** {r['date']} | **Dist:** {r['distance']}km | **Time:** {r['duration']} | **Pace:** {r_pace}")
                    with col_btn:
                        # Identify match parameters to pull index mapping
                        if st.button("Delete", key=f"del_rec_{selected_user}_{idx}"):
                            df = df.drop(idx)
                            # Put back placeholder block if empty
                            if df[df["runner"] == selected_user].empty:
                                placeholder = pd.DataFrame([{"runner": selected_user, "date": "", "distance": 0.0, "duration": "00:00:00"}])
                                df = pd.concat([df, placeholder], ignore_index=True)
                            conn.update(worksheet="running_data", data=df)
                            st.success("Record deleted.")
                            st.invalidate_pages()
                            st.rerun()

# --- Tab 3: Leaderboard & Export ---
with tab3:
    st.header("🏆 User Comparison Leaderboard")
    valid_runs = df[df["date"] != ""]
    
    if valid_runs.empty:
        st.info("No data available yet.")
    else:
        stats = helpers.calculate_stats(valid_runs)
        for user, s in stats.items():
            with st.expander(f"👤 Runner: {user}", expanded=True):
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total Runs", f"{s['Total Days']} Days")
                m2.metric("Cumulative Distance", f"{s['Total Distance (km)']} km")
                m3.metric("Total Duration", s['Total Time'])
                m4.metric("Average Distance", f"{s['Avg Distance (km)']} km")
                m5.metric("Average Pace", s['Avg Pace'])
                
                st.write("---")
                col_table, col_chart = st.columns([0.55, 0.45])
                user_records = valid_runs[valid_runs["runner"] == user].sort_values(by="date")
                
                with col_table:
                    st.write("#### 🗓️ Running History by Date")
                    formatted_table_data = []
                    for idx, (_, run) in enumerate(user_records.iterrows(), 1):
                        formatted_table_data.append({
                            "No.": idx, "Date": run["date"], "Distance": f"{run['distance']} km",
                            "Duration": run["duration"], "Pace": helpers.calculate_run_pace(float(run['distance']), str(run['duration']))
                        })
                    st.dataframe(formatted_table_data, use_container_width=True, hide_index=True)
                        
                with col_chart:
                    st.write("#### 📊 Mileage Bar Chart")
                    fig, ax = plt.subplots(figsize=(6, max(2.5, len(user_records) * 0.4)))
                    labels = ["TOTAL"] + [str(d) for d in user_records['date']]
                    distances = [s['Total Distance (km)']] + [float(d) for d in user_records['distance']]
                    colors = ['#1f4e79'] + ['#a6c8e0'] * len(user_records)
                    
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
        try:
            pdf_data = helpers.make_pdf(stats, valid_runs)
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
