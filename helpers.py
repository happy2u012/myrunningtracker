import csv
import io
import os
import matplotlib.pyplot as plt
import pandas as pd
from fpdf import FPDF

# --- Helper Function to Calculate Individual Run Pace ---
def calculate_run_pace(distance, duration_str):
    if distance <= 0:
        return "00:00/km"
    try:
        h, m, s = map(int, duration_str.split(":"))
        total_seconds = h * 3600 + m * 60 + s
        pace_seconds_per_km = total_seconds / distance
        pace_m, pace_s = divmod(int(pace_seconds_per_km), 60)
        return f"{pace_m:02d}:{pace_s:02d}/km"
    except Exception:
        return "00:00/km"

# --- Statistics Calculation Function (Modified for Pandas DataFrames) ---
def calculate_stats(df):
    summary = {}
    # Get list of unique runners
    runners = df["runner"].unique() if not df.empty else []
    
    for user in runners:
        user_df = df[df["runner"] == user]
        total_days = len(user_df)
        
        if total_days == 0:
            summary[user] = {
                "Total Days": 0, "Total Distance (km)": 0, "Total Time": "00:00:00",
                "Avg Distance (km)": 0, "Avg Time": "00:00:00", "Avg Pace": "00:00/km"
            }
            continue

        total_distance = user_df["distance"].astype(float).sum()
        total_seconds = 0
        
        for duration in user_df["duration"]:
            try:
                h, m, s = map(int, str(duration).split(":"))
                total_seconds += h * 3600 + m * 60 + s
            except Exception:
                pass

        avg_distance = total_distance / total_days
        avg_seconds = total_seconds / total_days

        def sec_to_str(seconds):
            m, s = divmod(int(seconds), 60)
            h, m = divmod(m, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"

        if total_distance > 0:
            pace_seconds_per_km = total_seconds / total_distance
            pace_m, pace_s = divmod(int(pace_seconds_per_km), 60)
            pace_str = f"{pace_m:02d}:{pace_s:02d}/km"
        else:
            pace_str = "00:00/km"

        summary[user] = {
            "Total Days": total_days,
            "Total Distance (km)": round(total_distance, 2),
            "Total Time": sec_to_str(total_seconds),
            "Avg Distance (km)": round(avg_distance, 2),
            "Avg Time": sec_to_str(avg_seconds),
            "Avg Pace": pace_str
        }
    return summary

def make_csv(stats):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User", "Total Days", "Total Distance (km)", "Total Time", "Avg Distance (km)", "Avg Time", "Avg Pace"])
    for user, s in stats.items():
        writer.writerow([user, s["Total Days"], s["Total Distance (km)"], s["Total Time"], s["Avg Distance (km)"], s["Avg Time"], s["Avg Pace"]])
    return output.getvalue().encode('utf-8')

def make_pdf(stats, df):
    pdf = FPDF()
    for user, s in stats.items():
        pdf.add_page()
        pdf.set_font("Arial", style="B", size=16)
        pdf.cell(190, 10, txt="RUNNING PERFORMANCE REPORT", ln=True, align="C")
        pdf.ln(6)
        
        pdf.set_font("Arial", style="B", size=14)
        pdf.set_text_color(31, 78, 121) 
        pdf.cell(190, 8, txt=f"Runner Profile: {user.upper()}", ln=True)
        pdf.set_text_color(0, 0, 0) 
        pdf.ln(2)
        
        pdf.set_font("Arial", style="B", size=9)
        pdf.set_fill_color(220, 230, 242) 
        pdf.cell(35, 7, txt="Total Runs", border=1, align="C", fill=True)
        pdf.cell(35, 7, txt="Cumulative Dist", border=1, align="C", fill=True)
        pdf.cell(40, 7, txt="Total Duration", border=1, align="C", fill=True)
        pdf.cell(40, 7, txt="Avg Distance", border=1, align="C", fill=True)
        pdf.cell(40, 7, txt="Avg Pace", border=1, align="C", fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", size=9)
        pdf.cell(35, 7, txt=f"{s['Total Days']} Days", border=1, align="C")
        pdf.cell(35, 7, txt=f"{s['Total Distance (km)']} km", border=1, align="C")
        pdf.cell(40, 7, txt=s['Total Time'], border=1, align="C")
        pdf.cell(40, 7, txt=f"{s['Avg Distance (km)']} km", border=1, align="C")
        pdf.cell(40, 7, txt=s['Avg Pace'], border=1, align="C")
        pdf.ln(6)
        
        user_df = df[df["runner"] == user].sort_values(by="date")
        table_height_mm = 6 + (len(user_df) * 6) + 6
        remaining_space_for_table = 297 - pdf.get_y() - 20
        
        if remaining_space_for_table < table_height_mm and len(user_df) > 0:
            pdf.add_page()
            pdf.set_font("Arial", style="B", size=12)
            pdf.set_text_color(31, 78, 121)
            pdf.cell(190, 8, txt=f"Runner Profile Continued: {user.upper()}", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        pdf.set_font("Arial", style="B", size=10)
        pdf.cell(190, 6, txt="Chronological Activity Logs:", ln=True)
        
        pdf.set_font("Arial", style="B", size=9)
        pdf.set_fill_color(242, 242, 242) 
        pdf.cell(15, 6, txt="No.", border=1, align="C", fill=True)
        pdf.cell(40, 6, txt="Date", border=1, align="C", fill=True)
        pdf.cell(45, 6, txt="Distance (km)", border=1, align="C", fill=True)
        pdf.cell(45, 6, txt="Duration", border=1, align="C", fill=True)
        pdf.cell(45, 6, txt="Pace", border=1, align="C", fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", size=9)
        for idx, (_, run) in enumerate(user_df.iterrows(), 1):
            fill_row = (idx % 2 == 0)
            pdf.set_fill_color(250, 250, 250) if fill_row else pdf.set_fill_color(255, 255, 255)
            run_pace = calculate_run_pace(float(run['distance']), str(run['duration']))
            
            pdf.cell(15, 6, txt=str(idx), border=1, align="C", fill=fill_row)
            pdf.cell(40, 6, txt=str(run['date']), border=1, align="C", fill=fill_row)
            pdf.cell(45, 6, txt=f"{run['distance']} km", border=1, align="C", fill=fill_row)
            pdf.cell(45, 6, txt=str(run['duration']), border=1, align="C", fill=fill_row)
            pdf.cell(45, 6, txt=run_pace, border=1, align="C", fill=fill_row)
            pdf.ln()
            
        if user_df.empty:
            pdf.set_font("Arial", style="I", size=9)
            pdf.cell(190, 6, txt="No verified activity logs logged yet.", border=1, align="L")
            pdf.ln()
            
        pdf.ln(4)
        
        if not user_df.empty:
            chart_height_inch = 2.2 + (len(user_df) * 0.15)
            chart_height_inch = min(6.5, max(2.2, chart_height_inch))
            chart_height_mm = chart_height_inch * 25.4
            
            plt.figure(figsize=(6.5, chart_height_inch))
            
            labels = ["TOTAL"] + [str(d) for d in user_df['date']]
            distances = [s['Total Distance (km)']] + [float(d) for d in user_df['distance']]
            colors = ['#1f4e79'] + ['#a6c8e0'] * len(user_df)
            
            bars = plt.barh(labels, distances, color=colors, height=0.55)
            plt.xlabel("Distance (km)", fontsize=9, fontweight='bold')
            plt.title(f"Mileage Breakdown for {user.upper()}", fontsize=10, fontweight='bold', pad=8)
            plt.gca().invert_yaxis() 
            plt.tight_layout()
            
            for bar in bars:
                width = bar.get_width()
                plt.text(width + (max(distances)*0.02), bar.get_y() + bar.get_height()/2, 
                         f"{width:.1f}k", va='center', ha='left', fontsize=8, fontweight='bold')
            
            chart_filename = f"temp_chart_{user}.png"
            plt.savefig(chart_filename, dpi=200, bbox_inches='tight')
            plt.close()
            
            remaining_space_for_chart = 297 - pdf.get_y() - 20
            if remaining_space_for_chart < chart_height_mm:
                pdf.add_page()
                pdf.set_font("Arial", style="B", size=10)
                pdf.cell(190, 6, txt=f"Mileage Chart Breakdown Continued ({user.upper()}):", ln=True)
                pdf.ln(2)
            
            pdf.image(chart_filename, x=15, y=pdf.get_y() + 2, w=180)
            if os.path.exists(chart_filename):
                os.remove(chart_filename)
                
    pdf_output = pdf.output(dest='S')
    if isinstance(pdf_output, str):
        return pdf_output.encode('latin-1')
    return bytes(pdf_output)
