import streamlit as st
import pandas as pd
import io
from datetime import datetime

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบบันทึกความเสี่ยง - รพ.นาโพธิ์", layout="wide")

# 2. ฟังก์ชันคำนวณ (ส่วนที่ 1)
def calculate_likelihood_by_count(subtype_count_3m):
    if subtype_count_3m < 1: return 1
    elif 1 <= subtype_count_3m <= 5: return 2
    elif 5 < subtype_count_3m <= 10: return 3
    else: return 4

def map_clinical_severity_to_score(level):
    clean_level = str(level).replace("ระดับ", "").strip()
    if clean_level in ["A", "B"]: return 1
    if clean_level in ["C", "D"]: return 2
    if clean_level in ["E", "F"]: return 3
    if clean_level in ["G", "H", "I"]: return 4
    return 1

# 3. เตรียมตัวแปร Session State
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = pd.DataFrame(columns=["Date", "Department", "Risk_Type", "Phase_or_Category", "Risk_Subtype", "Severity"])
if 'monthly_summary' not in st.session_state:
    st.session_state.monthly_summary = pd.DataFrame(columns=["Month_Year", "Risk_Subtype", "Count", "Likelihood", "Severity", "Risk_Score"])

# 4. หน้าจอหลัก
st.title("🏥 ระบบบันทึกและติดตามความเสี่ยงทางห้องปฏิบัติการ")
tab1, tab2, tab3 = st.tabs(["📝 1. บันทึกความเสี่ยง", "🧮 2. ประเมินรายเดือน", "📊 3. แดชบอร์ดและ Export"])

# Tab 1: บันทึกความเสี่ยง
with tab1:
    st.header("บันทึกอุบัติการณ์")
    # (เพิ่มโค้ดบันทึกของคุณตรงนี้ หากมี)
    st.info("ใช้สำหรับบันทึกข้อมูลอุบัติการณ์เข้าสู่ระบบ")

# Tab 2: ประเมินรายเดือน
with tab2:
    st.header("ประเมินรายเดือน")
    # (เพิ่มโค้ดประเมินของคุณตรงนี้ หากมี)
    st.info("ใช้สำหรับสรุปรายการและบันทึกผลประเมินลงใน monthly_summary")

# Tab 3: แดชบอร์ดและ Export (ส่วนที่ 2 ที่คุณต้องการ)
with tab3:
    st.header("📊 แดชบอร์ดสรุปความเสี่ยง (Risk Matrix)")
    
    if 'monthly_summary' in st.session_state and not st.session_state.monthly_summary.empty:
        df_summary = st.session_state.monthly_summary.copy()
        
        # คำนวณคะแนน Severity ใหม่และ Risk Score
        df_summary['Severity_Score'] = df_summary['Severity'].apply(map_clinical_severity_to_score)
        df_summary['Likelihood_Score'] = df_summary['Likelihood'].astype(int)
        df_summary['Risk_Level'] = df_summary['Severity_Score'] * df_summary['Likelihood_Score']
        
        # แสดงตารางสรุป
        st.dataframe(df_summary, use_container_width=True)
        
        # ปุ่มดาวน์โหลด Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_summary.to_excel(writer, index=False, sheet_name='RiskSummary')
        
        st.download_button(
            label="📥 ดาวน์โหลดไฟล์สรุปความเสี่ยง (Excel)",
            data=buffer.getvalue(),
            file_name="Risk_Incident_Report_Final.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("ยังไม่มีข้อมูลในระบบ กรุณาบันทึกเหตุการณ์ความเสี่ยงและประเมินรายเดือนใน Tab 2 ก่อนครับ")