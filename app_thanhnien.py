import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import os
from pyzbar.pyzbar import decode
from PIL import Image
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CẤU HÌNH GMAIL GỬI THƯ (BẠN SỬA Ở ĐÂY) ---
BOT_EMAIL = "dkvlvlkt.hcmus@gmail.com" 
BOT_PASSWORD = "rwge pbvo afxk ipmu" 
EMAIL_DOAN_KHOA = "dkvlvlkt.hcmus@gmail.com"

# --- 1. HÀM GỬI EMAIL ---
def send_email_notification(to_emails, subject, body_html):
    if not to_emails: return False
    # Hiển thị thông báo nhỏ góc phải để biết đang gửi
    st.toast("📨 Đang gửi email thông báo...", icon="🚀")
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Hệ thống Đoàn vụ <{BOT_EMAIL}>"
        msg['To'] = ", ".join(to_emails)
        msg['Subject'] = subject
        msg.attach(MIMEText(body_html, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(BOT_EMAIL, BOT_PASSWORD)
        text = msg.as_string()
        server.sendmail(BOT_EMAIL, to_emails, text)
        server.quit()
        st.toast("✅ Đã gửi email!", icon="✨")
        return True
    except Exception as e:
        st.error(f"Lỗi gửi mail: {e}")
        return False

# --- 2. HÀM ĐỌC ẢNH & GIAO DIỆN ---
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f: data = f.read()
    return base64.b64encode(data).decode()

LOGO_FILE = "logo.png"; BANNER_FILE = "banner.jpg"

st.set_page_config(page_title="Hệ thống Quản lý Đoàn Khoa", layout="wide", page_icon="🔵")

# Xử lý ảnh
try:
    if os.path.exists(LOGO_FILE):
        logo_base64 = get_base64_of_bin_file(LOGO_FILE)
        logo_html = f'<img class="login-logo" src="data:image/png;base64,{logo_base64}">'
    else: logo_html = '<img class="login-logo" src="https://i.imgur.com/M8a6qwz.png">'

    if os.path.exists(BANNER_FILE):
        banner_base64 = get_base64_of_bin_file(BANNER_FILE)
        banner_css = f"""background-image: linear-gradient(rgba(0, 84, 166, 0.5), rgba(0, 84, 166, 0.5)), url("data:image/jpg;base64,{banner_base64}");"""
    else: banner_css = "background-image: linear-gradient(rgba(0, 84, 166, 0.7), rgba(0, 84, 166, 0.7)), url('https://images.unsplash.com/photo-1523580494863-6f3031224c94');"
except: logo_html = ""; banner_css = ""

# CSS FIX MÀU & GIAO DIỆN
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff !important; }}
    h1, h2, h3, h4, h5, h6, p, span, div {{ color: #31333F !important; }}
    .top-banner h1, .top-banner p {{ color: white !important; }}
    .banner-text, .banner-text div {{ color: white !important; }}
    [data-testid="stMetricLabel"] {{ color: #555555 !important; }}
    [data-testid="stMetricValue"] {{ color: #0054a6 !important; }}
    .main .block-container {{ padding: 0; max-width: 100%; }}
    .login-header {{ display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 10vh; margin-bottom: 20px; }}
    .login-logo {{ width: 100px; margin-bottom: 15px; }}
    [data-testid="stForm"] {{ border: none; padding: 0 40px; box-shadow: none; }}
    .banner-container {{ {banner_css} background-size: cover; background-position: center; height: 100vh; display: flex; align-items: center; justify-content: center; color: white; flex-direction: column; padding: 20px; text-align: center; }}
    .force-blue-text {{ color: #0054a6 !important; font-family: 'Segoe UI', sans-serif; margin: 0; text-align: center; text-transform: uppercase; line-height: 1.4; }}
    .stButton>button {{ background-color: #0054a6; color: white !important; border-radius: 8px; font-weight: bold; width: 100%; height: 45px; margin-top: 10px; }}
    </style>
""", unsafe_allow_html=True)

# --- 3. KẾT NỐI GOOGLE SHEET ---
@st.cache_resource
def get_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict: creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)).open("CSDL_DoanKhoa")
    except: pass
    try:
        if os.path.exists("secrets.json"):
            return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)).open("CSDL_DoanKhoa")
    except: return None
    return None

def check_login(username, password):
    sh = get_connection(); 
    if not sh: return None
    try: ws = sh.worksheet("Users")
    except: return None
    for u in ws.get_all_records():
        if str(u.get('Username','')).strip() == str(username).strip() and str(u.get('Password','')).strip() == str(password).strip():
            return u
    return None

# Hàm lấy Email của user dựa vào Username
def get_email_by_username(username):
    try:
        sh = get_connection(); ws = sh.worksheet("Users")
        users = ws.get_all_records()
        for u in users:
            if str(u.get('Username', '')).strip() == str(username).strip():
                return u.get('Email', '')
    except: return None
    return None

# --- 4. XỬ LÝ NGHIỆP VỤ ---

# 4.1. Chi Đoàn gửi đơn
def submit_activity(name, creator, content, creator_email):
    sh = get_connection(); ws = sh.worksheet("HoatDong")
    ws.append_row([int(time.time()), name, creator, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Chờ duyệt", content, "", "", "Chưa nộp"])
    
    # Mail trình Đoàn khoa
    subject_admin = f"[{creator}] TRÌNH DUYỆT HOẠT ĐỘNG \"{name.upper()}\""
    body_admin = f"""
    <p>Kính gửi <b>Ban thường vụ Đoàn khoa Vật lý - Vật lý kỹ thuật</b>,</p>
    <p>Ban chấp hành <b>{creator}</b> kính trình hồ sơ đăng ký hoạt động: <b>{name}</b>.</p>
    <p>Nội dung tóm tắt: {content}</p>
    <p>Trân trọng.</p>
    <hr><small>Hệ thống Đoàn vụ</small>
    """
    send_email_notification([EMAIL_DOAN_KHOA], subject_admin, body_admin)

    # Mail xác nhận cho Chi đoàn
    if creator_email and "@" in creator_email:
        subject_user = f"[HỆ THỐNG] Đã tiếp nhận hồ sơ: {name}"
        body_user = f"""
        <p>Thân gửi Đ/c Bí thư {creator},</p>
        <p>Văn phòng Đoàn khoa đã nhận được đăng ký hoạt động <b>"{name}"</b>.</p>
        <p>Hồ sơ đang được chuyển đến Ban thường vụ xem xét.</p>
        <p>Trân trọng.</p>
        """
        send_email_notification([creator_email], subject_user, body_user)

# 4.2. Đoàn khoa Duyệt/Sửa (CÓ GỬI EMAIL PHẢN HỒI)
def update_activity(act_id, new_status, comment, act_name, creator_username):
    sh = get_connection(); ws = sh.worksheet("HoatDong")
    cell = ws.find(str(act_id))
    if cell:
        ws.update_cell(cell.row, 5, new_status)
        ws.update_cell(cell.row, 7, comment)
        
        # Tìm email của Chi đoàn đó để gửi thư
        creator_email = get_email_by_username(creator_username)
        if not creator_email or "@" not in creator_email:
            st.warning(f"⚠️ Không tìm thấy email của {creator_username} để gửi thông báo.")
            return

        # --- KỊCH BẢN 1: DUYỆT ---
        if new_status == "Đã duyệt":
            subject = f"[QUYẾT ĐỊNH] PHÊ DUYỆT HOẠT ĐỘNG \"{act_name.upper()}\""
            body = f"""
            <p>Kính gửi Ban chấp hành <b>{creator_username}</b>,</p>
            <p>Căn cứ Chương trình công tác Đoàn và phong trào thanh niên;</p>
            <p>Sau khi xem xét hồ sơ đăng ký hoạt động <b>"{act_name}"</b> của đơn vị;</p>
            <p>Ban thường vụ Đoàn khoa thông báo:</p>
            <h3 style="color: #0054a6;">ĐỒNG Ý CHỦ TRƯƠNG TỔ CHỨC</h3>
            <p><b>Ý kiến chỉ đạo:</b> {comment if comment else "Đề nghị đơn vị tổ chức hoạt động đảm bảo an toàn, tiết kiệm và hiệu quả."}</p>
            <p>Đề nghị đơn vị nghiêm túc triển khai thực hiện và nộp báo cáo đúng hạn.</p>
            <br>
            <p><b>TM. BTV ĐOÀN KHOA</b></p>
            <p><i>(Đã ký trên hệ thống)</i></p>
            """
            send_email_notification([creator_email], subject, body)

        # --- KỊCH BẢN 2: YÊU CẦU SỬA ---
        elif new_status == "Yêu cầu sửa":
            subject = f"[YÊU CẦU CHỈNH SỬA] HOẠT ĐỘNG \"{act_name.upper()}\""
            body = f"""
            <p>Kính gửi Ban chấp hành <b>{creator_username}</b>,</p>
            <p>Qua xem xét hồ sơ hoạt động <b>"{act_name}"</b>, Ban thường vụ Đoàn khoa có ý kiến như sau:</p>
            <div style="background-color: #fff3cd; padding: 15px; border-left: 5px solid #ffc107;">
                <b>NỘI DUNG CẦN ĐIỀU CHỈNH:</b><br>
                {comment}
            </div>
            <p>Đề nghị đơn vị khẩn trương điều chỉnh và cập nhật lại trên hệ thống.</p>
            <br>
            <p>Trân trọng.</p>
            """
            send_email_notification([creator_email], subject, body)

def submit_report(act_id, link):
    ws = get_connection().worksheet("HoatDong"); cell = ws.find(str(act_id))
    if cell: ws.update_cell(cell.row, 8, link); ws.update_cell(cell.row, 9, "Đã nộp")
def finalize_activity(act_id):
    ws = get_connection().worksheet("HoatDong"); cell = ws.find(str(act_id))
    if cell: ws.update_cell(cell.row, 9, "Hoàn tất")
def get_activities(): return get_connection().worksheet("HoatDong").get_all_records()
def load_student_info(mssv):
    if os.path.exists('data_sinhvien.xlsx'):
        df = pd.read_excel('data_sinhvien.xlsx', dtype={'MSSV': str})
        student = df[df['MSSV'] == str(mssv)]
        if not student.empty: return f"{student.iloc[0]['Ho']} {student.iloc[0]['Ten']}", student.iloc[0]['Khoa']
    return str(mssv), "Ngoài danh sách"
def submit_attendance(mssv, activity_name, don_vi):
    ws = get_connection().worksheet("DiemDanh"); now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ho_ten, khoa = load_student_info(mssv)
    ws.append_row([now_time, activity_name, mssv, ho_ten, don_vi])
    return f"✅ Đã lưu: {ho_ten}"

# --- 5. GIAO DIỆN CHÍNH ---
if 'user_info' not in st.session_state: st.session_state['user_info'] = None

if st.session_state['user_info'] is None:
    col1, col2 = st.columns([1, 1.5]) 
    with col1:
        st.markdown(f"""
            <div class="login-header">
                {logo_html}
                <p class="force-blue-text" style="font-size: 26px; font-weight: 900;">HỆ THỐNG QUẢN LÝ</p>
                <p class="force-blue-text" style="font-size: 18px; font-weight: 700;">ĐOÀN KHOA VẬT LÝ - VLKT</p>
            </div>
        """, unsafe_allow_html=True)
        with st.form("login"):
            usr = st.text_input("Tên đăng nhập")
            pwd = st.text_input("Mật khẩu", type="password")
            if st.form_submit_button("ĐĂNG NHẬP"):
                u = check_login(usr, pwd)
                if u: st.session_state['user_info'] = u; st.rerun()
                else: st.error("Sai thông tin!")
    with col2:
        st.markdown("""
            <div class="banner-container">
                <div class="banner-text">KHÁT VỌNG - TIÊN PHONG</div>
                <div class="banner-text">BẢN LĨNH - ĐOÀN KẾT</div>
                <br><div style="background:rgba(0,0,0,0.5);padding:10px;border-radius:10px;color:white !important">© 2026 Đoàn Khoa Vật lý & Vật lý Kỹ thuật</div>
            </div>
        """, unsafe_allow_html=True)
else:
    user = st.session_state['user_info']; role = user['Role']; my_name = user['TenHienThi']; my_username = user['Username']
    my_email = user.get('Email', '') 

    st.markdown(f"""
        <div class="top-banner" style="background: linear-gradient(90deg, #0054a6 0%, #00aeef 100%); padding: 20px; border-radius: 0 0 15px 15px; color: white; text-align: center; margin-bottom: 30px;">
            <h1 style="color: white !important; font-size: 24px; font-weight: 800; margin: 0;">CỔNG QUẢN LÝ CÔNG TRÌNH THANH NIÊN</h1>
            <p style="color: white !important;">{my_name} | {role.upper()}</p>
        </div>
    """, unsafe_allow_html=True)
    with st.sidebar:
        st.info(f"👤 **{my_name}**")
        if st.button("Đăng xuất"): st.session_state['user_info'] = None; st.rerun()
        st.divider()
        menu = st.radio("Menu", ["🏠 Trang chủ", "📝 Quản lý Hoạt động", "📸 Điểm danh"])

    if menu == "🏠 Trang chủ":
        st.subheader("Bảng tin")
        all_acts = get_activities(); df = pd.DataFrame(all_acts)
        if not df.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tổng HĐ", len(df)); c2.metric("Đã duyệt", len(df[df['TrangThai'] == 'Đã duyệt']))
            c3.metric("Chờ duyệt", len(df[df['TrangThai'] == 'Chờ duyệt']))
            c4.metric("Hoàn tất", len([x for x in all_acts if x.get('TrangThaiHoanThanh') == 'Hoàn tất']))
        else: st.info("Chưa có dữ liệu.")
        
    elif menu == "📝 Quản lý Hoạt động":
        if role == 'admin':
            tab1, tab2 = st.tabs(["⚡ Cần Duyệt", "🏁 Nghiệm thu"])
            with tab1:
                acts = get_activities(); pending = [a for a in acts if a['TrangThai'] in ['Chờ duyệt', 'Yêu cầu sửa']]
                if not pending: st.success("Không có hồ sơ chờ.")
                
                # --- VÒNG LẶP CÓ KHÓA DUY NHẤT (SỬA LỖI TRÙNG FORM) ---
                for i, act in enumerate(pending):
                    with st.expander(f"📌 {act['TenHoatDong']} ({act['NguoiTao']})", expanded=True):
                        st.write(f"**Nội dung:** {act['NoiDung']}")
                        # Key có thêm số thứ tự i để không bị trùng
                        with st.form(key=f"d_{act['ID']}_{i}"):
                            cmt = st.text_area("Góp ý / Chỉ đạo:")
                            c1, c2 = st.columns(2)
                            
                            # Nút DUYỆT
                            if c1.form_submit_button("✅ DUYỆT"): 
                                update_activity(act['ID'], "Đã duyệt", cmt, act['TenHoatDong'], act['NguoiTao'])
                                st.rerun()
                            
                            # Nút SỬA
                            if c2.form_submit_button("❌ SỬA"): 
                                update_activity(act['ID'], "Yêu cầu sửa", cmt, act['TenHoatDong'], act['NguoiTao'])
                                st.rerun()
            with tab2:
                acts = get_activities(); reports = [a for a in acts if a.get('TrangThaiHoanThanh') == 'Đã nộp']
                if not reports: st.info("Trống.")
                for r in reports:
                    with st.expander(f"🏆 {r['TenHoatDong']}", expanded=True):
                        st.write(f"Link: {r.get('MinhChung')}")
                        if st.button("NGHIỆM THU", key=f"f_{r['ID']}"): finalize_activity(r['ID']); st.success("Xong!"); st.rerun()
        else:
            with st.expander("➕ Đăng ký mới"):
                with st.form("add"):
                    name = st.text_input("Tên hoạt động:"); content = st.text_area("Mô tả:")
                    if st.form_submit_button("Gửi"): 
                        submit_activity(name, my_username, content, my_email)
                        st.success("Đã gửi hồ sơ & trình email lên Đoàn khoa!"); time.sleep(1); st.rerun()
            my_acts = [a for a in get_activities() if str(a['NguoiTao']) == str(my_username)]
            for act in my_acts:
                stt = act['TrangThai']; color = "green" if stt == "Đã duyệt" else "orange" if stt == "Chờ duyệt" else "red"
                with st.container(border=True):
                    st.markdown(f"**{act['TenHoatDong']}** (<span style='color:{color}'>{stt}</span>)", unsafe_allow_html=True)
                    if act['GopY']: st.info(f"🔔 Ý kiến Đoàn khoa: {act['GopY']}")
                    if stt == "Đã duyệt" and act.get('TrangThaiHoanThanh') != "Hoàn tất":
                        with st.popover("📤 Nộp minh chứng"):
                            link = st.text_input("Link:", key=f"l_{act['ID']}")
                            if st.button("Gửi", key=f"s_{act['ID']}"): submit_report(act['ID'], link); st.rerun()

    elif menu == "📸 Điểm danh":
        st.subheader("Điểm danh")
        all_acts = get_activities()
        valid = [a['TenHoatDong'] for a in all_acts if a['TrangThai'] == 'Đã duyệt'] if role == 'admin' else [a['TenHoatDong'] for a in all_acts if a['TrangThai'] == 'Đã duyệt' and str(a['NguoiTao']) == str(my_username)]
        if valid:
            act = st.selectbox("Chọn:", valid)
            if 'ukey' not in st.session_state: st.session_state['ukey'] = 0
            img = st.file_uploader("Quét thẻ", type=['png','jpg'], key=f"cam_{st.session_state['ukey']}")
            if img:
                decoded = decode(Image.open(img))
                if decoded:
                    msg = submit_attendance(decoded[0].data.decode('utf-8'), act, my_name)
                    st.success(msg); time.sleep(1); st.session_state['ukey']+=1; st.rerun()
                else: st.error("Lỗi mã")
        else: st.warning("Không có hoạt động.")