import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. ตั้งค่าหน้าเว็บให้แสดงผลเต็มจอ
st.set_page_config(
    page_title="ระบบบันทึกความเสี่ยง - รพ.นาโพธิ์", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏥 ระบบบันทึกและติดตามความเสี่ยงทางห้องปฏิบัติการ")
st.subheader("กลุ่มงานเทคนิคการแพทย์ โรงพยาบาลนาโพธิ์")
st.markdown("---")

# 2. จำลองฐานข้อมูลภายในระบบ (Session State) เพื่อเก็บข้อมูลชั่วคราว
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = pd.DataFrame(columns=[
        "Timestamp", "Date", "Shift", "Department", 
        "Risk_Type", "Phase_or_Category", "Risk_Subtype", "Event_Type", "Severity"
    ])

if 'monthly_summary' not in st.session_state:
    st.session_state.monthly_summary = pd.DataFrame(columns=[
        "Month_Year", "Department", "Risk_Type", "Phase_or_Category", "Risk_Subtype", "Count", "Likelihood", "Severity", "Risk_Score"
    ])

# ฟังก์ชันคำนวณ Likelihood ตามจำนวนครั้งย้อนหลัง 3 เดือน (เกณฑ์ใหม่ เข้าใจง่ายที่สุด)
def calculate_likelihood_by_count(subtype_count_3m):
    if subtype_count_3m < 1:
        return 1
    elif 1 <= subtype_count_3m <= 5:
        return 2
    elif 5 < subtype_count_3m <= 10:
        return 3
    else:  # มากกว่า 10 ครั้ง
        return 4

# ฟังก์ชันแปลงระดับความรุนแรงทางคลินิก A-I เป็นคะแนน Consequence (1-4)
def map_clinical_severity_to_score(level):
    if level in ["A", "B", "C"]:
        return 1  # ต่ำ
    elif level in ["D", "E", "F"]:
        return 2  # ปานกลาง
    elif level in ["G", "H"]:
        return 3  # สูง
    elif level == "I":
        return 4  # สูงมาก
    return 1

# 3. รายการข้อมูลดิบดั้งเดิมทั้งหมด (Original Master Data)
non_clinical_subtypes = {
    "สิ่งแวดล้อมทางกายภาพ": [
        "อุณหภูมิห้องสูงหรือแกว่งเกินไป (Temperature Fluctuation)",
        "ความชื้นสัมพัทธ์ไม่เหมาะสม (Improper Humidity)",
        "แสงสว่างไม่เพียงพอ (Poor Illumination )",
        "มลพิษทางเสียง (Noise Pollution)",
        "การระบายไอสารเคมีไม่ดี (Inadequate Chemical Fume Ventilation)",
        "ความเสี่ยงต่อการเกิดเพลิงไหม้ (Fire Hazards)"
    ],
    "ระบบ IT/คอมพิวเตอร์": [
        "ระบบอินเตอร์เฟสล่ม (Interface Downtime)",
        "ข้อมูลสูญหายเนื่องจากไม่มีการสำรองข้อมูล (Lack of Data Backup)",
        "การโจมตีด้วยมัลแวร์เรียกค่าไถ่ (Ransomware Attack)",
        "ระบบ HIS ล่ม",
        "ระบบ LIS ล่ม",
        "ภัยคุกคามจากภายในและสิทธิการเข้าถึง (Unauthorized Access)",
        "ช่องโหว่จากอุปกรณ์ภายนอก (Removable Media Vulnerability)"
    ],
    "ระบบสาธารณูปโภค": [
        "กระแสไฟฟ้ากระชาก/ดับชั่วขณะ (Power Surges & Sags)",
        "ระบบสำรองไฟ (UPS) ทำงานล้มเหลวหรือไม่เพียงพอ",
        "เต้ารับไฟฟ้า (Plugs/Outlets) เกินกำลังหรืออยู่ใกล้จุดเสี่ยง",
        "คุณภาพน้ำบริสุทธิ์ต่ำกว่ามาตรฐาน (Water Quality Degradation)",
        "การปนเปื้อนของเชื้อแบคทีเรียในระบบท่อน้ำ (Bacterial Biofilm)",
        "แรงดันน้ำไม่คงที่หรือน้ำประปาหยุดไหล (Water Pressure & Interruption)",
        "เครื่องปรับอากาศชำรุด",
        "ท่อน้ำทิ้งสารเคมี/น้ำเสียติดเชื้ออุดตันหรือรั่วซึม",
        "ไฟดับเป็นเวลานานมากกว่า 1 ชั่วโมง",
        "ส้วมเต็มหรือตัน"
    ],
    "พฤติกรรมบริการและการสื่อสาร": [
        "การใช้คำพูดและน้ำเสียงที่ไม่เหมาะสม (Inappropriate Verbal & Tone)",
        "ใช้ศัพท์เทคนิคทางการแพทย์ ที่เข้าใจยากในการอธิบายการปฏิบัติตัว",
        "การแสดงออกทางสีหน้าบึ้งตึง สายตาละเลยไม่สบตา (Poor eye contact)",
        "การปฏิเสธหรือละเลยการให้ข้อมูล (Information Neglect)",
        "เจ้าหน้าที่เจาะเลือดด้วยความรีบร้อน รุนแรง หรือแสดงท่าทีรำคาญ",
        "การละเลยการรักษาความเพิกเฉยต่อความกลัวของผู้ป่วย",
        "ตะโกนเรียกชื่อผู้ป่วยพร้อมบอกชื่อสิ่งส่งตรวจหรือผลตรวจที่น่าอายในที่สาธารณะ",
        "เจ้าหน้าที่ควบคุมอารมณ์ไม่ได้ เมื่อเผชิญหน้ากับผู้รับบริการที่กำลังโกรธ",
        "การประชดประชัน กระแทกกระทั้นสิ่งของ เพื่อแสดงออกถึงความไม่พอใจ",
        "การใช้น้ำเสียงหรือคำพูดเชิงตำหนิพยาบาลหรือเจ้าหน้าที่ส่งแล็บอย่างรุนแรงเมื่อส่งสิ่งส่งตรวจผิดพลาด",
        "แสดงพฤติกรรมบริการที่ดีกับผู้ป่วยบางกลุ่ม แต่ละละเลยหรือปฏิบัติด้วยท่าทีที่แย่กว่ากับผู้ป่วยกลุ่มอื่น",
        "ไม่อยู่ประจำจุดบริการในเวลาที่กำหนด หรือปล่อยให้ผู้ป่วยยืนรอหน้าห้องแล็บเป็นเวลานาน",
        "พขร. ไม่นำเลือดที่ผ่านการ cross match แล้วกลับมาด้วย",
        "พขร. ลืมนำถุงเลือดลงจากรถ",
        "พขร. นำส่งเลือดที่ผ่านการ cross match แล้ว ล่าช้า",
        "ปลดถุงเลือด หมดอายุ ไม่ได้ใช้"
    ]
}

clinical_subtypes = {
    "Pre-analytical": [
        "สิ่งส่งตรวจน้อยเกินไป (Inadequate volume)",
        "สิ่งส่งตรวจเป็นลิ่มเลือด (Clot)",
        "สิ่งส่งตรวจเม็ดเลือดแดงแตก (Hemolysis)",
        "สิ่งส่งตรวจผิดคน/ติดป้ายชื่อผิดคน สลับคน (Mislabel)",
        "ไม่ติดสติ๊กเกอร์ชื่อ สกุล คนไข้ /ไม่ระบุตัวผู้ป่วย (Unlabeled Specimen)",
        "เก็บสิ่งส่งตรวจใส่หลอดหรือภาชนะผิดชนิด",
        "เก็บสิ่งส่งตรวจผิดตำแหน่ง (ข้างที่ให้ IV)",
        "เก็บสิ่งส่งตรวจผิดเวลา",
        "เก็บสิ่งส่งตรวจซ้ำ",
        "เก็บสิ่งส่งตรวจไม่ได้ (เจาะเลือดไม่ได้ เจาะยาก)",
        "ปิดฝาหลอดเก็บสิ่งส่งตรวจสลับกัน",
        "คีย์คำสั่งตรวจ/ออเดอร์ของแพทย์ในระบบคอมพิวเตอร์ (HIS/LIS) ผิดพลาด",
        "ส่งสิ่งส่งตรวจแต่ไม่มีใบขอส่งตรวจหรือไม่คีย์ส่งตรวจในระบบ (request form)",
        "สิ่งส่งตรวจหาย",
        "สิ่งส่งตรวจหกเลอะเทอะขั้นตอนนำส่ง",
        "สิ่งส่งตรวจหก เสียหาย ระหว่างเตรียมตรวจวิเคราะห์",
        "ผู้ป่วยปฏิบัติตัวไม่ถูกต้องก่อนเจาะเลือด เช่น ไม่งดอาหารก่อนตรวจน้ำตาล",
        "เวลาในการขนส่งล่าช้า (Delayed Transport)",
        "การนำส่งสิ่งส่งตรวจไม่เหมาะสม เช่น ไม่ห่อกันแสงในหลอดส่งตรวจ MB",
        "เจ้าหน้าที่ห้องแล็บคีย์รับสิ่งส่งตรวจเข้าระบบ LIS ผิดพลาด",
        "ใช้ความเร็ว (RPM/RCF) หรือเวลาในการปั่นไม่เหมาะสม"
    ],
    "Analytical": [
        "เครื่องตรวจวิเคราะห์ Biochemistry Error / ขัดข้อง",
        "เครื่องตรวจวิเคราะห์ CBC Error / ขัดข้อง",
        "เครื่องตรวจวิเคราะห์ PT&INR Error / ขัดข้อง",
        "เครื่องตรวจวิเคราะห์ Troponin I Error / ขัดข้อง",
        "เครื่องตรวจวิเคราะห์ Urine reader Error / ขัดข้อง",
        "เครื่องตรวจวิเคราะห์ MB Error / ขัดข้อง",
        "เครื่องเพาะเชื้อในเลือด/Hemoculture ขัดข้อง ไม่พร้อมใช้งาน",
        "เครื่องมือสนับสนุนทางห้องปฏิบัติการชำรุด ไม่พร้อมใช้งาน",
        "ผลควบคุมคุณภาพ (IQC) สาขาเคมีคลินิก ไม่ผ่านเกณฑ์",
        "ผลควบคุมคุณภาพ (IQC) สาขาโลหิตวิทยา ไม่ผ่านเกณฑ์",
        "ผลควบคุมคุณภาพ (IQC) สาขาภูมิคุ้มกันวิทยา ไม่ผ่านเกณฑ์",
        "ผลควบคุมคุณภาพ (IQC) สาขาจุลทรรศนศาสตร์คลินิก ไม่ผ่านเกณฑ์",
        "ผลควบคุมคุณภาพ (IQC) สาขาจุลชีววิทยา ไม่ผ่านเกณฑ์",
        "ผลควบคุมคุณภาพ (IQC) สาขาธนาคารเลือด ไม่ผ่านเกณฑ์",
        "ผลควบคุมคุณภาพ (EQA) สาขาเคมีคลินิก ไม่ผ่านเกณฑ์",
        "ผลควบคุมคุณภาพ (EQA) สาขาโลหิตวิทยา ไม่ผ่านเกณฑ์",
        "ผลควบคุมคุณภาพ (EQA) สาขาภูมิคุ้มกันวิทยา ไม่ผ่านเกณฑ์",
        "ผลควบคุมคุณภาพ (EQA) สาขาจุลทรรศนศาสตร์คลินิก ไม่ผ่านเกณฑ์",
        "ผลควบคุมคุณภาพ (EQA) สาขาจุลชีววิทยา ไม่ผ่านเกณฑ์",
        "ผลควบคุมคุณภาพ (EQA) สาขาธนาคารเลือด ไม่ผ่านเกณฑ์",
        "สารเคมี/น้ำยา หมดอายุหรือเสื่อมสภาพ",
        "ชุดตรวจหมดอายุ",
        "ตรวจวิเคราะห์ผิดวิธี ผิดขั้นตอน",
        "เทคนิคการตรวจวิเคราะห์ไม่ถูกต้อง"
    ],
    "Post-analytical": [
        "รายงานผลผิดคน",
        "รายงานผลผิดพลาด ตัวเลขหรือตัวอักษรผิด",
        "รายงานผลล่าช้าเกินเวลาที่กำหนด (TAT เกิน)",
        "ไม่ได้โทรแจ้งผลวิกฤต (Critical value)",
        "รายงานค่าวิกฤติเกินเวลาที่กำหนด",
        "รายงานผลไม่ครบถ้วน",
        "เกิดอาการไม่พึงประสงค์จากการให้เลือด (Transfusion Reaction)",
        "การให้เลือดผิดคน (Wrong Blood Transfused)"
    ]
}

department_list = [
    "Lab", "IPD", "OPD", "ER", "LR", "VIP", "ปฐมภูมิและองค์รวม", 
    "จิตเวชและยาเสพติด", "NCD", "ARI", "OR", "ยานพาหนะ", "เวรเจาะเลือด DM",
    "พยาบาลเจาะเลือดมาจากบ้าน"
]

# 4. สร้าง Tab เมนูหลักในการใช้งาน
tab1, tab2, tab3 = st.tabs(["📝 1. บันทึกความเสี่ยงออนไลน์", "🧮 2. ประเมินรายเดือน (Risk Manager)", "📊 3. แดชบอร์ดและ Risk Matrix"])

# ==========================================
# TAB 1: หน้าบันทึกความเสี่ยงออนไลน์
# ==========================================
with tab1:
    st.header("แบบฟอร์มรายงานอุบัติการณ์และความเสี่ยง")
    
    c1, c2 = st.columns(2)
    with c1:
        date_evt = st.date_input("1. วันที่เกิดความเสี่ยง", datetime.now())
        shift_evt = st.selectbox("2. ช่วงเวรที่เกิดความเสี่ยง", ["เช้า", "บ่าย", "ดึก"])
    with c2:
        dept_evt = st.selectbox("3. หน่วยงานที่ทำให้เกิดความเสี่ยง", department_list)
        risk_type = st.radio(
            "4. ประเภทความเสี่ยง", 
            ["ความเสี่ยงทางคลินิก (Clinical Risk)", "ความเสี่ยงทั่วไป (Non-Clinical Risk)"]
        )

    st.markdown("---")
    st.subheader("รายละเอียดความเสี่ยงจำเพาะ")
    
    if risk_type == "ความเสี่ยงทางคลินิก (Clinical Risk)":
        col_cl1, col_cl2 = st.columns(2)
        with col_cl1:
            phase_or_cat = st.selectbox("ขั้นตอนที่เกิดความเสี่ยง (Phase)", ["Pre-analytical", "Analytical", "Post-analytical"])
            risk_subtype = st.selectbox("ระบุความเสี่ยงย่อยทางคลินิก", clinical_subtypes[phase_or_cat])
        with col_cl2:
            event_type = st.selectbox(
                "2.1 รูปแบบเหตุการณ์", 
                [
                    "Near Miss (เกือบพลาด - ดักจับได้ทันก่อนถึงผู้ป่วย)", 
                    "Miss / Incident (ผิดพลาด - หลุดไปถึงตัวผู้ป่วยแล้ว)"
                ]
            )
            severity = st.selectbox("ระดับความรุนแรงทางคลินิก (Clinical Severity)", [
                "ระดับ A: ยังไม่เกิดกับผู้ป่วย แต่มีโอกาสที่จะเกิดความคลาดเคลื่อน",
                "ระดับ B: เกิดความคลาดเคลื่อนขึ้นแล้ว แต่ยังไม่ถึงตัวผู้ป่วย",
                "ระดับ C: เกิดความคลาดเคลื่อนถึงตัวผู้ป่วยแล้ว แต่ไม่ทำให้เกิดอันตราย",
                "ระดับ D: ความคลาดเคลื่อนถึงตัวผู้ป่วย ส่งผลให้ต้องติดตามเฝ้าระวังเพิ่มเติม",
                "ระดับ E: ความคลาดเคลื่อนทำให้เกิดอันตรายชั่วคราว และต้องการการรักษาพยาบาลเพิ่มเติม",
                "ระดับ F: ความคลาดเคลื่อนทำให้เกิดอันตรายชั่วคราว และต้องนอนโรงพยาบาลหรืออยู่นานขึ้น",
                "ระดับ G: ความคลาดเคลื่อนส่งผลให้เกิดอันตรายถาวรแก่ผู้ป่วย",
                "ระดับ H: ความคลาดเคลื่อนส่งผลให้ผู้ป่วยเกือบเสียชีวิต (ต้องกู้ชีพ)",
                "ระดับ I: ความคลาดเคลื่อนส่งผลให้ผู้ป่วยเสียชีวิต"
            ])
    else:
        col_nc1, col_nc2 = st.columns(2)
        with col_nc1:
            phase_or_cat = st.selectbox("ลักษณะความเสี่ยงทั่วไป", ["สิ่งแวดล้อมทางกายภาพ", "ระบบ IT/คอมพิวเตอร์", "ระบบสาธารณูปโภค", "พฤติกรรมบริการและการสื่อสาร"])
            risk_subtype = st.selectbox("ระบุความเสี่ยงย่อยทั่วไป", non_clinical_subtypes[phase_or_cat])
        with col_nc2:
            event_type = "Incident"
            severity = st.selectbox("ระดับความรุนแรงทั่วไป (Non-clinical Severity)", [
                "ระดับ 1: ต่ำ (เสียหาย < 5,000 บาท หรือ กู้คืนระบบสำเร็จได้ภายใน 1 ชั่วโมง)",
                "ระดับ 2: ปานกลาง (เสียหาย 5,000 - 50,000 บาท หรือ กู้คืนระบบสำเร็จภายใน 1 - 4 ชั่วโมง)",
                "ระดับ 3: สูง (เสียหาย 50,001 - 500,000 บาท หรือ กู้คืนระบบสำเร็จภายใน 4 - 24 ชั่วโมง)",
                "ระดับ 4: สูงมาก (เสียหาย > 500,000 บาท ขึ้นไป หรือ ระบบขัดข้องยาวนานกว่า 24 ชั่วโมง)"
            ])

    st.markdown("<br>", unsafe_allow_html=True)
    submit_btn = st.button("🚀 บันทึกรายงานความเสี่ยง เข้าสู่ระบบ")
    
    if submit_btn:
        severity_value = severity.split(":")[0].replace("ระดับ ", "").strip()
        
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Date": date_evt.strftime("%Y-%m-%d"),
            "Shift": shift_evt,
            "Department": dept_evt,
            "Risk_Type": risk_type,
            "Phase_or_Category": phase_or_cat,
            "Risk_Subtype": risk_subtype,
            "Event_Type": event_type,
            "Severity": severity_value
        }])
        st.session_state.raw_data = pd.concat([st.session_state.raw_data, new_row], ignore_index=True)
        st.success("🎉 บันทึกรายงานอุบัติการณ์เรียบร้อยแล้ว!")

    st.markdown("### 📋 รายการข้อมูลดิบที่ถูกบันทึกในระบบ")
    st.dataframe(st.session_state.raw_data, use_container_width=True)


# ==========================================
# TAB 2: หน้าสรุปและประเมินรายเดือนสำหรับ Risk Manager
# ==========================================
with tab2:
    st.header("🧮 ส่วนงานประเมินสถิติและเคาะคะแนน Risk Matrix")
    
    if st.session_state.raw_data.empty:
        st.info("💡 ยังไม่มีข้อมูลดิบถูกบันทึกเข้ามาในระบบ กรุณากรอกข้อมูลในคอลัมน์ Tab ที่ 1 ก่อนนะครับ")
    else:
        df_raw = st.session_state.raw_data.copy()
        df_raw['Date_Parsed'] = pd.to_datetime(df_raw['Date'])
        df_raw['Month_Year'] = df_raw['Date_Parsed'].dt.strftime("%B %Y")
        
        summary_view = df_raw.groupby(['Month_Year', 'Risk_Type', 'Phase_or_Category', 'Risk_Subtype']).size().reset_index(name='Count_Total')
        
        st.subheader("📊 ตารางสถิติจำนวนครั้งแยกรายความเสี่ยงย่อยประจำเดือน")
        st.dataframe(summary_view, use_container_width=True)
        st.markdown("---")
        
        st.subheader("✍️ ส่วนประเมินและวิเคราะห์ระดับโอกาสเกิดย้อนหลัง 3 เดือน")
        selected_index = st.selectbox(
            "เลือกหัวข้อความเสี่ยงย่อยที่ต้องการประเมินคะแนน", 
            summary_view.index, 
            format_func=lambda x: f"[{summary_view.loc[x, 'Month_Year']}] - {summary_view.loc[x, 'Risk_Subtype']} (เดือนปัจจุบันเกิด {summary_view.loc[x, 'Count_Total']} ครั้ง)"
        )
        
        row_data = summary_view.loc[selected_index]
        
        # ค้นหาประวัติย้อนหลัง 3 เดือน เพื่อนำมานับความถี่ (Count)
        target_month_dt = datetime.strptime(row_data['Month_Year'], "%B %Y")
        three_months_ago = target_month_dt - timedelta(days=90)
        
        # ดึงสถิติย้อนหลัง 3 เดือนเฉพาะของความเสี่ยงย่อยที่เลือก
        df_3m_subtype = df_raw[
            (df_raw['Date_Parsed'] >= pd.Timestamp(three_months_ago)) & 
            (df_raw['Date_Parsed'] <= pd.Timestamp(target_month_dt + timedelta(days=31))) &
            (df_raw['Risk_Subtype'] == row_data['Risk_Subtype'])
        ]
        subtype_count_3m = len(df_3m_subtype)
        
        # คำนวณหาคะแนน Likelihood จากจำนวนครั้งตามเงื่อนไขใหม่ที่กำหนด
        computed_likelihood = calculate_likelihood_by_count(subtype_count_3m)
        
        st.markdown(f"""
        <div style="background-color:#f4f6f9; padding:20px; border-radius:10px; border-left:6px solid #28a745; margin-bottom:15px;">
            <h4 style="margin-top:0px; color:#28a745;">📈 ผลการคำนวณระดับความถี่ย้อนหลัง 3 เดือน:</h4>
            <ul style="font-size:15px; line-height:1.6; list-style-type: none; padding-left: 0;">
                <li>📌 หัวข้อความเสี่ยง: <b>"{row_data['Risk_Subtype']}"</b></li>
                <li>🔄 เกิดขึ้นจริงย้อนหลัง 3 เดือน: <b style="color:#28a745; font-size:18px;">{subtype_count_3m} ครั้ง</b></li>
                <li>📝 ได้คะแนนระดับโอกาสเกิด <b>(Likelihood Score): {computed_likelihood} คะแนน</b></li>
            </ul>
            <span style="font-size:12px; color:gray;">
                (เกณฑ์สถิติ: น้อยกว่า 1 ครั้ง = 1 คะแนน | 1-5 ครั้ง = 2 คะแนน | 5-10 ครั้ง = 3 คะแนน | มากกว่า 10 ครั้ง = 4 คะแนน)
            </span>
        </div>
        """, unsafe_allow_html=True)
        
        latest_items = df_raw[
            (df_raw['Month_Year'] == row_data['Month_Year']) & 
            (df_raw['Risk_Subtype'] == row_data['Risk_Subtype'])
        ]
        recorded_severities = latest_items['Severity'].unique()
        severity_display_str = ", ".join(map(str, recorded_severities))
        
        is_clinical = (row_data['Risk_Type'] == "ความเสี่ยงทางคลินิก (Clinical Risk)")
        
        if is_clinical:
            st.info(f"🔍 ข้อมูลระดับความรุนแรงจริง (Severity) ที่บันทึกไว้ในระบบคือ: **ระดับ {severity_display_str}**")
            st.markdown("""
            **เกณฑ์แปลงระดับจริงเป็น Consequence Score:**
            * ระดับ **A, B** = 1 คะแนน (ต่ำ)
            * ระดับ **C, D** = 2 คะแนน (ปานกลาง)
            * ระดับ **E, F** = 3 คะแนน (สูง)
            * ระดับ **G, H, I** = 4 คะแนน (สูงมาก)
            """)
            
            default_score = 1
            if len(recorded_severities) > 0:
                default_score = map_clinical_severity_to_score(recorded_severities[0])
                
            s_score = st.slider("ระบุระดับ Consequence Score (1-4) เพื่อลงแกน Matrix", 1, 4, default_score)
            eval_severity_str = severity_display_str
        else:
            st.info(f"🔍 ข้อมูลระดับความรุนแรงจริงที่บันทึกไว้คือ: **ระดับ {severity_display_str}**")
            default_score = 1
            if len(recorded_severities) > 0:
                try:
                    default_score = int(recorded_severities[0])
                except:
                    default_score = 1
            s_score = st.slider("ระบุระดับ Consequence Score (1-4)", 1, 4, default_score)
            eval_severity_str = f"ระดับ {s_score}"

        eval_submit = st.button("💾 บันทึกผลประเมินรายข้อ")
        
        if eval_submit:
            total_risk_score = computed_likelihood * s_score
            
            new_eval = pd.DataFrame([{
                "Month_Year": row_data['Month_Year'],
                "Department": "ภาพรวมหน่วยงาน",
                "Risk_Type": row_data['Risk_Type'],
                "Phase_or_Category": row_data['Phase_or_Category'],
                "Risk_Subtype": row_data['Risk_Subtype'],
                "Count": int(row_data['Count_Total']),
                "Likelihood": computed_likelihood,
                "Severity": eval_severity_str,
                "Risk_Score": total_risk_score
            }])
            
            if not st.session_state.monthly_summary.empty:
                st.session_state.monthly_summary = st.session_state.monthly_summary[
                    ~((st.session_state.monthly_summary['Month_Year'] == row_data['Month_Year']) & 
                      (st.session_state.monthly_summary['Risk_Subtype'] == row_data['Risk_Subtype']))
                ]
            
            st.session_state.monthly_summary = pd.concat([st.session_state.monthly_summary, new_eval], ignore_index=True)
            st.success(f"ประเมินสำเร็จ! [ความถี่ L: {computed_likelihood} ({subtype_count_3m} ครั้ง)] * [ความรุนแรง C: {s_score}] = Risk Score {total_risk_score} คะแนน")

        st.subheader("📋 ตารางผลการประเมินที่พร้อมขึ้นแดชบอร์ด")
        st.dataframe(st.session_state.monthly_summary, use_container_width=True)


# ==========================================
# TAB 3: หน้าแดชบอร์ดและแผงควบคุมระบบความเสี่ยง
# ==========================================
with tab3:
    st.header("📊 แดชบอร์ดวิเคราะห์และจัดลำดับความเสี่ยงห้องปฏิบัติการ")
    
    if st.session_state.monthly_summary.empty:
        st.info("💡 กรุณาผ่านกระบวนการเคาะคะแนนประเมินในข้อที่ 2 (Tab 2) ก่อนเพื่อเปิดระบบการแสดงผลแดชบอร์ด")
    else:
        df_dash = st.session_state.monthly_summary.copy()
        
        st.markdown("#### 🔍 ตัวกรองแดชบอร์ด")
        m_filter = st.multiselect("เลือกเดือนในการดูแดชบอร์ด", df_dash['Month_Year'].unique(), default=df_dash['Month_Year'].unique())
            
        df_filtered = df_dash[df_dash['Month_Year'].isin(m_filter)]
        
        if df_filtered.empty:
            st.warning("❌ ไม่พบข้อมูลตามเงื่อนไขที่เลือกในตัวกรอง")
        else:
            st.markdown("---")
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("จำนวนหัวข้อความเสี่ยงที่วิเคราะห์", len(df_filtered))
            kpi2.metric("จำนวนอุบัติการณ์สะสม (ครั้ง)", int(df_filtered['Count'].sum()))
            kpi3.metric("คะแนนความเสี่ยงเฉลี่ยของระบบ", f"{df_filtered['Risk_Score'].mean():.2f}")
            
            st.markdown("---")
            col_g1, col_g2 = st.columns([6, 4])
            
            with col_g1:
                st.subheader("📌 ลำดับความเสี่ยงเร่งด่วนประจำเดือน")
                df_sorted = df_filtered.sort_values(by="Risk_Score", ascending=True)
                
                colors = []
                for score in df_sorted['Risk_Score']:
                    if score >= 7: colors.append('crimson')       # แดง (สูงมาก)
                    elif score >= 5: colors.append('darkorange')    # ส้ม (สูง)
                    elif score == 4: colors.append('gold')          # เหลือง (ปานกลาง)
                    else: colors.append('forestgreen')              # เขียว (ต่ำ)
                
                labels = [
                    f"{row['Risk_Subtype']} [Severity: {row['Severity']}]" 
                    for _, row in df_sorted.iterrows()
                ]
                
                fig_bar = go.Figure(go.Bar(
                    x=df_sorted['Risk_Score'],
                    y=labels,
                    orientation='h',
                    marker_color=colors,
                    text=df_sorted['Risk_Score'],
                    textposition='inside'
                ))
                fig_bar.update_layout(
                    xaxis_title="คะแนนระดับความเสี่ยงรวม (Risk Score: 2-8)",
                    yaxis_title="หัวข้อความเสี่ยงย่อย [ระดับรุนแรงจริง]",
                    height=500
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
            with col_g2:
                st.subheader("🍰 สัดส่วนเหตุการณ์แยกตามหมวดงาน")
                fig_pie = px.pie(df_filtered, names="Phase_or_Category", values="Count", hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)

            st.markdown("---")
            st.subheader("🧱 4x4 Interactive Risk Matrix (พิกัดตามระดับคะแนนผลรวม L + C)")
            
            matrix_df = pd.DataFrame(0, index=[4, 3, 2, 1], columns=[1, 2, 3, 4])
            
            for _, row in df_filtered.iterrows():
                l = int(row['Likelihood'])
                sev_val = str(row['Severity'])
                if sev_val in ["A", "B", ]:
                    s = 1
                elif sev_val in ["C","D" ]:
                    s = 2
                elif sev_val in ["E", "F"]:
                    s = 3
                elif sev_val == ["G", "H","I"]:
                    s = 4
                else:
                    try:
                        s = int(sev_val.replace("ระดับ", "").strip())
                    except:
                        s = 1
                        
                if s in matrix_df.index and l in matrix_df.columns:
                    matrix_df.loc[s, l] += 1
            
            matrix_html = f"""
            <table style="width:100%; border-collapse: collapse; text-align: center; font-family: sans-serif; font-weight: bold; border: 2px solid black;">
                <tr style="background-color: #f2f2f2; border-bottom: 2px solid black;">
                    <th style="padding: 12px; border-right: 2px solid black;">ความรุนแรง / ผลกระทบ (Consequence)</th>
                    <th style="width: 22.5%; background-color: #eaeaea; border-right: 1px solid black;">เกิดขึ้นน้อยมาก (1)<br><span style="font-size:10px; font-weight:normal;">< 1 ครั้ง ใน 3 เดือน</span></th>
                    <th style="width: 22.5%; background-color: #eaeaea; border-right: 1px solid black;">เกิดขึ้นบ้าง (2)<br><span style="font-size:10px; font-weight:normal;">1 - 5 ครั้ง ใน 3 เดือน</span></th>
                    <th style="width: 22.5%; background-color: #eaeaea; border-right: 1px solid black;">เกิดขึ้นบ่อย (3)<br><span style="font-size:10px; font-weight:normal;">5 - 10 ครั้ง ใน 3 เดือน</span></th>
                    <th style="width: 22.5%; background-color: #eaeaea; border-right: 1px solid black;">เกิดขึ้นเป็นประจำ (4)<br><span style="font-size:10px; font-weight:normal;">> 10 ครั้ง ใน 3 เดือน</span></th>
                </tr>
                
                <tr style="border-bottom: 1px solid gray;">
                    <td style="background-color: #f2f2f2; padding: 12px; border-right: 2px solid black;">สูงมาก (4) [ระดับ I / 4]</td>
                    <td style="background-color: #ff9900; color: white; border-right: 1px solid black;">
                        <div>คะแนน 5 (ส้ม)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[4, 1]} เรื่อง</div>
                    </td>
                    <td style="background-color: #ff9900; color: white; border-right: 1px solid black;">
                        <div>คะแนน 6 (ส้ม)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[4, 2]} เรื่อง</div>
                    </td>
                    <td style="background-color: #ff3333; color: white; border-right: 1px solid black;">
                        <div>คะแนน 7 (แดง)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[4, 3]} เรื่อง</div>
                    </td>
                    <td style="background-color: #cc0000; color: white; border-right: 1px solid black;">
                        <div>คะแนน 8 (แดง)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[4, 4]} เรื่อง</div>
                    </td>
                </tr>
                
                <tr style="border-bottom: 1px solid gray;">
                    <td style="background-color: #f2f2f2; padding: 12px; border-right: 2px solid black;">สูง (3) [ระดับ G-H / 3]</td>
                    <td style="background-color: #ffff00; color: black; border-right: 1px solid black;">
                        <div>คะแนน 4 (เหลือง)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[3, 1]} เรื่อง</div>
                    </td>
                    <td style="background-color: #ff9900; color: white; border-right: 1px solid black;">
                        <div>คะแนน 5 (ส้ม)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[3, 2]} เรื่อง</div>
                    </td>
                    <td style="background-color: #ff9900; color: white; border-right: 1px solid black;">
                        <div>คะแนน 6 (ส้ม)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[3, 3]} เรื่อง</div>
                    </td>
                    <td style="background-color: #ff3333; color: white; border-right: 1px solid black;">
                        <div>คะแนน 7 (แดง)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[3, 4]} เรื่อง</div>
                    </td>
                </tr>
                
                <tr style="border-bottom: 1px solid gray;">
                    <td style="background-color: #f2f2f2; padding: 12px; border-right: 2px solid black;">ปานกลาง (2) [ระดับ D-F / 2]</td>
                    <td style="background-color: #99cc33; color: white; border-right: 1px solid black;">
                        <div>คะแนน 3 (เขียว)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[2, 1]} เรื่อง</div>
                    </td>
                    <td style="background-color: #ffff00; color: black; border-right: 1px solid black;">
                        <div>คะแนน 4 (เหลือง)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[2, 2]} เรื่อง</div>
                    </td>
                    <td style="background-color: #ff9900; color: white; border-right: 1px solid black;">
                        <div>คะแนน 5 (ส้ม)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[2, 3]} เรื่อง</div>
                    </td>
                    <td style="background-color: #ff9900; color: white; border-right: 1px solid black;">
                        <div>คะแนน 6 (ส้ม)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[2, 4]} เรื่อง</div>
                    </td>
                </tr>
                
                <tr>
                    <td style="background-color: #f2f2f2; padding: 12px; border-right: 2px solid black;">ต่ำ (1) [ระดับ A-C / 1]</td>
                    <td style="background-color: #54b254; color: white; border-right: 1px solid black;">
                        <div>คะแนน 2 (เขียว)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[1, 1]} เรื่อง</div>
                    </td>
                    <td style="background-color: #99cc33; color: white; border-right: 1px solid black;">
                        <div>คะแนน 3 (เขียว)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[1, 2]} เรื่อง</div>
                    </td>
                    <td style="background-color: #ffff00; color: black; border-right: 1px solid black;">
                        <div>คะแนน 4 (เหลือง)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[1, 3]} เรื่อง</div>
                    </td>
                    <td style="background-color: #ff9900; color: white; border-right: 1px solid black;">
                        <div>คะแนน 5 (ส้ม)</div>
                        <div style="font-size: 20px; margin-top:5px;">{matrix_df.loc[1, 4]} เรื่อง</div>
                    </td>
                </tr>
            </table>
            """
            st.markdown(matrix_html, unsafe_allow_html=True)
            st.caption("🧱 พิกัดบน Matrix คำนวณแบบง่ายโดยอิงจากจำนวนครั้งที่เกิดขึ้นในรอบ 3 เดือนจริง")
	def save_risk_data_to_excel(df):
    # กำหนดชื่อไฟล์ตามเดือนและปี
    filename = "Risk_Incident_Report.xlsx"
    
    # หากไฟล์มีอยู่แล้ว ให้โหลดมาแล้วเพิ่มข้อมูลต่อท้าย หรือสร้างใหม่หากยังไม่มี
    if os.path.exists(filename):
        existing_df = pd.read_excel(filename)
        updated_df = pd.concat([existing_df, df], ignore_index=True)
    else:
        updated_df = df
        
    # บันทึกลงไฟล์ Excel
    updated_df.to_excel(filename, index=False)
    return filename