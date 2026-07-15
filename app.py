import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# 1. ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="ระบบบันทึกความเสี่ยง - รพ.นาโพธิ์", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏥 ระบบบันทึกและติดตามความเสี่ยงทางห้องปฏิบัติการ")
st.subheader("กลุ่มงานเทคนิคการแพทย์ โรงพยาบาลนาโพธิ์")
st.markdown("---")

# 2. Initialize Session State
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = pd.DataFrame(columns=[
        "Timestamp", "Date", "Shift", "Department", 
        "Risk_Type", "Phase_or_Category", "Risk_Subtype", "Event_Type", "Severity"
    ])

if 'monthly_summary' not in st.session_state:
    st.session_state.monthly_summary = pd.DataFrame(columns=[
        "Month_Year", "Department", "Risk_Type", "Phase_or_Category", "Risk_Subtype", "Count", "Likelihood", "Severity", "Risk_Score"
    ])

# ฟังก์ชันคำนวณ
def calculate_likelihood_by_count(count):
    if count < 1: return 1
    elif 1 <= count <= 5: return 2
    elif 5 < count <= 10: return 3
    else: return 4

def map_clinical_severity_to_score(level):
    clean_level = str(level).replace("ระดับ", "").strip()
    if clean_level in ["A", "B", "C"]: return 1
    elif clean_level in ["D", "E", "F"]: return 2
    elif clean_level in ["G", "H"]: return 3
    elif clean_level == "I": return 4
    return 1

# [ข้อมูล Master Data คงเดิม...]
non_clinical_subtypes = {"สิ่งแวดล้อมทางกายภาพ": ["อุณหภูมิห้องสูงหรือแกว่งเกินไป", "ความชื้นสัมพัทธ์ไม่เหมาะสม", "แสงสว่างไม่เพียงพอ", "มลพิษทางเสียง", "การระบายไอสารเคมีไม่ดี", "ความเสี่ยงต่อการเกิดเพลิงไหม้"], "ระบบ IT/คอมพิวเตอร์": ["ระบบอินเตอร์เฟสล่ม", "ข้อมูลสูญหาย", "มัลแวร์", "ระบบ HIS ล่ม", "ระบบ LIS ล่ม", "ช่องโหว่ความปลอดภัย"], "ระบบสาธารณูปโภค": ["ไฟตก/ไฟดับ", "ระบบสำรองไฟล้มเหลว", "คุณภาพน้ำไม่ได้มาตรฐาน", "เครื่องปรับอากาศชำรุด"], "พฤติกรรมบริการและการสื่อสาร": ["การสื่อสารไม่เหมาะสม", "พฤติกรรมไม่เหมาะสมต่อผู้ป่วย", "ความล่าช้าในการให้บริการ"]}
clinical_subtypes = {"Pre-analytical": ["สิ่งส่งตรวจน้อย", "Hemolysis", "Mislabel", "สิ่งส่งตรวจผิดชนิด", "ส่งตรวจผิดคน"], "Analytical": ["เครื่องขัดข้อง", "IQC ไม่ผ่าน", "EQA ไม่ผ่าน", "น้ำยาหมดอายุ"], "Post-analytical": ["รายงานผลผิดพลาด", "TAT เกิน", "ไม่ได้แจ้ง Critical value"]}
department_list = ["Lab", "IPD", "OPD", "ER", "LR", "VIP", "อื่นๆ"]

# 4. สร้าง Tabs
tab1, tab2, tab3 = st.tabs(["📝 1. บันทึกความเสี่ยง", "🧮 2. ประเมินรายเดือน", "📊 3. แดชบอร์ดและ Risk Matrix"])

with tab1:
    # [คงโค้ดเดิมของคุณในส่วน Tab 1 ไว้ทั้งหมด]
    c1, c2 = st.columns(2)
    with c1:
        date_evt = st.date_input("วันที่เกิดเหตุ", datetime.now())
        shift_evt = st.selectbox("เวร", ["เช้า", "บ่าย", "ดึก"])
    with c2:
        dept_evt = st.selectbox("หน่วยงาน", department_list)
        risk_type = st.radio("ประเภท", ["ความเสี่ยงทางคลินิก (Clinical Risk)", "ความเสี่ยงทั่วไป (Non-Clinical Risk)"])
    
    if risk_type == "ความเสี่ยงทางคลินิก (Clinical Risk)":
        phase_or_cat = st.selectbox("ขั้นตอน", ["Pre-analytical", "Analytical", "Post-analytical"])
        risk_subtype = st.selectbox("ความเสี่ยงย่อย", clinical_subtypes[phase_or_cat])
        severity = st.selectbox("ระดับความรุนแรง", ["ระดับ A", "ระดับ B", "ระดับ C", "ระดับ D", "ระดับ E", "ระดับ F", "ระดับ G", "ระดับ H", "ระดับ I"])
    else:
        phase_or_cat = st.selectbox("หมวด", ["สิ่งแวดล้อมทางกายภาพ", "ระบบ IT/คอมพิวเตอร์", "ระบบสาธารณูปโภค", "พฤติกรรมบริการและการสื่อสาร"])
        risk_subtype = st.selectbox("ความเสี่ยงย่อย", non_clinical_subtypes[phase_or_cat])
        severity = st.selectbox("ระดับความรุนแรง (1-4)", ["ระดับ 1", "ระดับ 2", "ระดับ 3", "ระดับ 4"])
        
    if st.button("บันทึกรายงาน"):
        new_row = pd.DataFrame([{"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Date": date_evt.strftime("%Y-%m-%d"), "Shift": shift_evt, "Department": dept_evt, "Risk_Type": risk_type, "Phase_or_Category": phase_or_cat, "Risk_Subtype": risk_subtype, "Event_Type": "Incident", "Severity": severity}])
        st.session_state.raw_data = pd.concat([st.session_state.raw_data, new_row], ignore_index=True)
        st.success("บันทึกสำเร็จ!")

with tab2:
    # [คงโค้ดเดิมของคุณในส่วน Tab 2 ไว้ทั้งหมด]
    if not st.session_state.raw_data.empty:
        df_raw = st.session_state.raw_data.copy()
        df_raw['Date_Parsed'] = pd.to_datetime(df_raw['Date'])
        df_raw['Month_Year'] = df_raw['Date_Parsed'].dt.strftime("%B %Y")
        summary_view = df_raw.groupby(['Month_Year', 'Risk_Subtype']).size().reset_index(name='Count_Total')
        st.dataframe(summary_view)
        # (คุณสามารถวาง Logic การประเมินคะแนนของคุณต่อได้ที่นี่)
    else:
        st.info("ไม่มีข้อมูล")

with tab3:
    st.header("📊 แดชบอร์ด")
    # แก้ไขส่วนนี้เพื่อให้แน่ใจว่าหน้าจอไม่หาย
    if 'monthly_summary' in st.session_state and not st.session_state.monthly_summary.empty:
        df_dash = st.session_state.monthly_summary.copy()
        st.dataframe(df_dash)
    else:
        st.info("ยังไม่มีข้อมูลในระบบ กรุณาประเมินใน Tab 2 ก่อนครับ")