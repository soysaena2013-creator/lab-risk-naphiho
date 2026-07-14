import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ตั้งค่าหน้าจอ
st.set_page_config(page_title="ระบบบันทึกความเสี่ยง - รพ.นาโพธิ์", layout="wide")

st.title("🏥 ระบบบันทึกและติดตามความเสี่ยงทางห้องปฏิบัติการ")

# --- ฟังก์ชันคำนวณ ---
def calculate_likelihood_by_count(count_3m):
    if count_3m < 1: return 1
    elif 1 <= count_3m <= 5: return 2
    elif 5 < count_3m <= 10: return 3
    else: return 4

def map_clinical_severity_to_score(level):
    if level in ["A", "B", "C"]: return 1
    elif level in ["D", "E", "F"]: return 2
    elif level in ["G", "H"]: return 3
    elif level == "I": return 4
    return 1

# --- สถานะข้อมูล ---
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = pd.DataFrame(columns=["Timestamp", "Date", "Risk_Subtype", "Severity", "Risk_Type", "Phase_or_Category"])
if 'monthly_summary' not in st.session_state:
    st.session_state.monthly_summary = pd.DataFrame(columns=["Month_Year", "Risk_Subtype", "Count", "Likelihood", "Consequence", "Risk_Score"])

# --- TAB เมนู ---
tab1, tab2, tab3 = st.tabs(["📝 1. บันทึกรายงาน", "🧮 2. ประเมินความเสี่ยง", "📊 3. แดชบอร์ด"])

# TAB 1: บันทึก
with tab1:
    st.header("บันทึกอุบัติการณ์")
    with st.form("entry_form"):
        date_evt = st.date_input("วันที่เกิด")
        subtype = st.text_input("ชื่อความเสี่ยง")
        severity = st.selectbox("ระดับความรุนแรง", ["A", "B", "C", "D", "E", "F", "G", "H", "I"])
        submit = st.form_submit_button("บันทึก")
        if submit:
            new_data = pd.DataFrame([{"Timestamp": datetime.now(), "Date": date_evt, "Risk_Subtype": subtype, "Severity": severity, "Risk_Type": "Clinical", "Phase_or_Category": "Pre-analytical"}])
            st.session_state.raw_data = pd.concat([st.session_state.raw_data, new_data], ignore_index=True)
            st.success("บันทึกแล้ว")

# TAB 2: ประเมิน (แก้ไขตรรกะการคูณตรงนี้)
with tab2:
    st.header("ประเมินความเสี่ยง")
    if not st.session_state.raw_data.empty:
        df = st.session_state.raw_data.copy()
        df['Date'] = pd.to_datetime(df['Date'])
        
        # เลือกความเสี่ยง
        subtypes = df['Risk_Subtype'].unique()
        sel_subtype = st.selectbox("เลือกความเสี่ยง", subtypes)
        
        # คำนวณ
        count_3m = len(df[df['Risk_Subtype'] == sel_subtype])
        L = calculate_likelihood_by_count(count_3m)
        sev_val = map_clinical_severity_to_score(df[df['Risk_Subtype'] == sel_subtype]['Severity'].iloc[-1])
        
        C = st.slider("Consequence Score (Impact)", 1, 4, sev_val)
        
        if st.button("บันทึกผลประเมิน"):
            # แก้ไขจากบวกเป็นคูณ ตามสูตร Risk Score = L x I
            score = L * C 
            
            new_eval = pd.DataFrame([{
                "Month_Year": datetime.now().strftime("%B %Y"),
                "Risk_Subtype": sel_subtype,
                "Count": count_3m,
                "Likelihood": L,
                "Consequence": C,
                "Risk_Score": score
            }])
            st.session_state.monthly_summary = pd.concat([st.session_state.monthly_summary, new_eval], ignore_index=True)
            st.success(f"บันทึกสำเร็จ! คะแนนคือ {L} x {C} = {score}")

    st.dataframe(st.session_state.monthly_summary)

# TAB 3: แดชบอร์ด
with tab3:
    st.header("แดชบอร์ด")
    if not st.session_state.monthly_summary.empty:
        st.bar_chart(st.session_state.monthly_summary.set_index('Risk_Subtype')['Risk_Score'])