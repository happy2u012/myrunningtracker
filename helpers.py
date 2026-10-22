import csv
import io
import os
import matplotlib.pyplot as plt
from fpdf import FPDF

def calculate_run_pace(distance, duration_str):
    if distance <= 0: return "00:00/km"
    try:
        h, m, s = map(int, duration_str.split(":"))
        total_seconds = h * 3600 + m * 60 + s
        pace_seconds_per_km = total_seconds / distance
        pace_m, pace_s = divmod(int(pace_seconds_per_km), 60)
        return f"{pace_m:02d}:{pace_s:02d}/km"
    except Exception: return "00:00/km"

def calculate_stats_dataframe(df_runs):
    summary = {}
    unique_runners = df_runs["runner"].unique()
    for user in unique_runners:
        user_runs = df_runs[df_runs["runner"] == user]
        total_days = len(user_runs)
        if total_days == 0: continue
        
        total_distance = sum(float(d) for d in user_runs["distance"])
        total_seconds = 0
        for dur in user_runs["duration"]:
            try:
                h, m, s = map(int, str(dur).split(":"))
                total_seconds += h * 3600 + m * 60 + s
            except: pass
            
        avg_distance = total_distance / total_days
        avg_seconds = total_seconds / total_days
        
        def sec_to_str(seconds):
            m, s = divmod(int(seconds), 60)
            h, m = divmod(m, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"
            
        pace_str = f"{divmod(int(total_seconds / total_distance), 60)[0]:02d}:{divmod(int(total_seconds / total_distance), 60)[1]:02d}/km" if total_distance > 0 else "00:00/km"
        
        summary[user] = {
            "Total Days": total_days, "Total Distance (km)": round(total_distance, 2), "Total Time": sec_to_str(total_seconds),
            "Avg Distance (km)": round(avg_distance, 2), "Avg Time": sec_to_str(avg_seconds), "Avg Pace": pace_str
        }
    return summary

def make_csv(stats):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User", "Total Days", "Total Distance (km)", "Total Time", "Avg Distance (km)", "Avg Time", "Avg Pace"])
    for user, s in stats.items():
        writer.writerow([user, s["Total Days"], s["Total Distance (km)"], s["Total Time"], s["Avg Distance (km)"], s["Avg Time"], s["Avg Pace"]])
    return output.getvalue().encode('utf-8')

def make_pdf_dataframe(stats, df_runs):
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
        
        user_records = df_runs[df_runs["runner"] == user].sort_values(by="date")
        table_height_mm = 6 + (len(user_records) * 6) + 6
        if (297 - pdf.get_y() - 20) < table_height_mm:
            pdf.add_page()
            
        pdf.set_font("Arial", style="B", size=10)
        pdf.cell(190, 6, txt="Chronological Activity Logs:", ln=True)
        pdf.set_fill_color(242, 242, 242) 
        pdf.cell(15, 6, txt="No.", border=1, align="C", fill=True)
        pdf.cell(40, 6, txt="Date", border=1, align="C", fill=True)
        pdf.cell(45, 6, txt="Distance (km)", border=1, align="C", fill=True)
        pdf.cell(45, 6, txt="Duration", border=1, align="C", fill=True)
        pdf.cell(45, 6, txt="Pace", border=1, align="C", fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", size=9)
        for idx, (_, run) in enumerate(user_records.iterrows(), 1):
            fill_row = (idx % 2 == 0)
            pdf.set_fill_color(250, 250, 250) if fill_row else pdf.set_fill_color(255, 255, 255)
            pdf.cell(15, 6, txt=str(idx), border=1, align="C", fill=fill_row)
            pdf.cell(40, 6, txt=str(run['date']), border=1, align="C", fill=fill_row)
            pdf.cell(45, 6, txt=f"{run['distance']} km", border=1, align="C", fill=fill_row)
            pdf.cell(45, 6, txt=str(run['duration']), border=1, align="C", fill=fill_row)
            pdf.cell(45, 6, txt=calculate_run_pace(float(run['distance']), str(run['duration'])), border=1, align="C", fill=fill_row)
            pdf.ln()
            
        pdf.ln(4)
        if not user_records.empty:
            plt.figure(figsize=(6.5, min(6.5, max(2.2, 2.2 + (len(user_records) * 0.15)))))
            labels = [str(run['date']) for _, run in user_records.iterrows()] + ["TOTAL"]
            distances = [float(run['distance']) for _, run in user_records.iterrows()] + [s['Total Distance (km)']]
            bars = plt.barh(labels, distances, color=['#a6c8e0']*len(user_records) + ['#1f4e79'], height=0.55)
            plt.xlabel("Distance (km)", fontsize=9, fontweight='bold'); plt.gca().invert_yaxis(); plt.tight_layout()
            
            for bar in bars:
                plt.text(bar.get_width() + (max(distances)*0.02), bar.get_y() + bar.get_height()/2, f"{bar.get_width():.1f}k", va='center', ha='left', fontsize=8, fontweight='bold')
                
            chart_filename = f"temp_chart_{user}.png"
            plt.savefig(chart_filename, dpi=200, bbox_inches='tight'); plt.close()
            if (297 - pdf.get_y() - 20) < (len(user_records)*4 + 50): pdf.add_page()
            pdf.image(chart_filename, x=15, y=pdf.get_y() + 2, w=180)
            if os.path.exists(chart_filename): os.remove(chart_filename)
    return pdf.output(dest='S').encode('latin-1') if isinstance(pdf.output(dest='S'), str) else bytes(pdf.output(dest='S'))