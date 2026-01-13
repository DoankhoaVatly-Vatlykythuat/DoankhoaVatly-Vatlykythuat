import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import os
from pyzbar.pyzbar import decode
from PIL import Image

# --- 1. CẤU HÌNH GIAO DIỆN & CSS ---
st.set_page_config(page_title="Hệ thống Quản lý Đoàn Khoa", layout="wide", page_icon="🔵")

st.markdown("""
    <style>
    /* Ẩn padding mặc định của Streamlit để banner tràn viền */
    .main .block-container {
        padding-top: 0;
        padding-bottom: 0;
        padding-left: 0;
        padding-right: 0;
        max-width: 100%;
    }
    
    /* --- CSS CHO MÀN HÌNH ĐĂNG NHẬP MỚI --- */
    .login-container {
        padding: 50px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100vh; /* Chiều cao full màn hình */
        background-color: white;
    }
    .login-logo {
        width: 120px;
        margin-bottom: 20px;
    }
    .login-title {
        color: #0054a6;
        text-align: center;
        font-weight: 700;
        font-size: 1.5rem;
        margin-bottom: 5px;
        text-transform: uppercase;
    }
    .login-subtitle {
        color: #0054a6;
        text-align: center;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 30px;
        text-transform: uppercase;
    }
    
    .banner-container {
        /* Ảnh banner thanh niên */
        background-image: url('https://doanthanhnien.vn/Content/images/banner-chao-mung-dai-hoi-doan-toan-quoc-lan-thu-xii.jpg');
        background-size: cover;
        background-position: center;
        height: 100vh;
        position: relative;
    }
    /* Lớp phủ sóng xanh bên trên và dưới banner */
    .banner-overlay-top {
        position: absolute; top: 0; left: 0; width: 100%; height: 150px;
        background: url('https://i.imgur.com/8w8YQcQ.png') no-repeat top left; background-size: 100% auto;
    }
    .banner-overlay-bottom {
        position: absolute; bottom: 0; left: 0; width: 100%; height: 150px;
        background: url('https://i.imgur.com/8w8YQcQ.png') no-repeat bottom left; background-size: 100% auto;
        transform: scaleY(-1); /* Lật ngược lại cho phần đáy */
    }

    /* --- CSS CHO PHẦN DASHBOARD (SAU KHI ĐĂNG NHẬP) --- */
    .stApp { background-color: #f0f2f6; } /* Màu nền xám nhạt cho dashboard */
    .top-banner {
        background: linear-gradient(90deg, #0054a6 0%, #00aeef 100%);
        padding: 20px; border-radius: 0 0 15px 15px; color: white;
        text-align: center; margin-top: 0px; margin-bottom: 30px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .top-banner h1 { color: white !important; font-size: 28px; font-weight: 800; margin: 0; }
    
    /* Nút bấm chung */
    .stButton>button {
        background-color: #0054a6; color: white; border-radius: 8px; font-weight: bold; border: none; width: 100%; height: 45px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { background-color: #003d7a; transform: scale(1.02); }
    
    /* Badge trạng thái */
    .status-cho { background-color: #fff3cd; color: #856404; padding: 5px 10px; border-radius: 10px; font-weight: bold;}
    .status-duyet { background-color: #d4edda; color: #155724; padding: 5px 10px; border-radius: 10px; font-weight: bold;}
    .status-sua { background-color: #f8d7da; color: #721c24; padding: 5px 10px; border-radius: 10px; font-weight: bold;}
    .status-xong { background-color: #cce5ff; color: #004085; padding: 5px 10px; border-radius: 10px; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# --- 2. BACKEND (XỬ LÝ DỮ LIỆU) ---
@st.cache_resource
def get_connection():
    # Cách 1: Ưu tiên lấy từ Secrets của Streamlit Cloud (An toàn nhất)
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        # Fix lỗi xuống dòng của private_key nếu có
        if "private_key" in creds_dict:
             creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("CSDL_DoanKhoa")
    # Cách 2: Nếu không có Secrets (đang chạy trên Laptop), dùng file json
    else:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
        client = gspread.authorize(creds)
        return client.open("CSDL_DoanKhoa")

def check_login(username, password):
    try:
        sh = get_connection(); ws = sh.worksheet("Users")
        users = ws.get_all_records()
        for u in users:
            if str(u['Username']) == str(username) and str(u['Password']) == str(password):
                return u
        return None
    except: return None

# --- Quản lý Hoạt động & Minh chứng ---
def submit_activity(name, creator, content):
    sh = get_connection(); ws = sh.worksheet("HoatDong")
    act_id = int(time.time())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Cấu trúc: ID | Ten | NguoiTao | ThoiGian | TrangThai | NoiDung | GopY | MinhChung | TrangThaiHoanThanh
    ws.append_row([act_id, name, creator, now, "Chờ duyệt", content, "", "", "Chưa nộp"])

def update_activity(act_id, new_status, comment):
    sh = get_connection(); ws = sh.worksheet("HoatDong")
    cell = ws.find(str(act_id))
    if cell:
        ws.update_cell(cell.row, 5, new_status)
        ws.update_cell(cell.row, 7, comment)

def submit_report(act_id, link_minh_chung):
    sh = get_connection(); ws = sh.worksheet("HoatDong")
    cell = ws.find(str(act_id))
    if cell:
        ws.update_cell(cell.row, 8, link_minh_chung) # Cột H: MinhChung
        ws.update_cell(cell.row, 9, "Đã nộp")       # Cột I: TrangThaiHoanThanh

def finalize_activity(act_id):
    sh = get_connection(); ws = sh.worksheet("HoatDong")
    cell = ws.find(str(act_id))
    if cell:
        ws.update_cell(cell.row, 9, "Hoàn tất")     # Chốt sổ

def get_activities():
    sh = get_connection(); ws = sh.worksheet("HoatDong")
    return ws.get_all_records()

# --- Điểm danh ---
def load_student_info(mssv):
    if os.path.exists('data_sinhvien.xlsx'):
        df = pd.read_excel('data_sinhvien.xlsx', dtype={'MSSV': str})
        student = df[df['MSSV'] == str(mssv)]
        if not student.empty:
            return f"{student.iloc[0]['Ho']} {student.iloc[0]['Ten']}", student.iloc[0]['Khoa']
    return str(mssv), "Ngoài danh sách"

def submit_attendance(mssv, activity_name, don_vi):
    sh = get_connection(); ws = sh.worksheet("DiemDanh")
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ho_ten, khoa = load_student_info(mssv)
    ws.append_row([now_time, activity_name, mssv, ho_ten, don_vi])
    return f"✅ Đã lưu: {ho_ten}"

# --- 3. GIAO DIỆN CHÍNH ---
if 'user_info' not in st.session_state: st.session_state['user_info'] = None

if st.session_state['user_info'] is None:
    # === MÀN HÌNH ĐĂNG NHẬP MỚI ===
    # Chia màn hình thành 2 cột: Trái (Form) - Phải (Banner)
    col1, col2 = st.columns([1, 1.5]) # Tỉ lệ 1:1.5
    
    with col1:
        st.markdown("""
            <div class="login-container">
                <img class="login-logo" src="https://upload.wikimedia.org/wikipedia/vi/thumb/6/60/Huy_hi%E1%BB%87u_%C4%90o%C3%A0n_TNCS_H%E1%BB%93_Ch%C3%AD_Minh.svg/1200px-Huy_hi%E1%BB%87u_%C4%90o%C3%A0n_TNCS_H%E1%BB%93_Ch%C3%AD_Minh.svg.png">
                <h2 class="login-title">HỆ THỐNG NGHIỆP VỤ</h2>
                <h3 class="login-subtitle">CÔNG TÁC ĐOÀN KHOA VẬT LÝ - VLKT</h3>
            </div>
        """, unsafe_allow_html=True)
        
        # Form đăng nhập (Đặt bên dưới tiêu đề)
        with st.form("login"):
            usr = st.text_input("Tên đăng nhập", placeholder="Nhập mã Chi đoàn hoặc Admin")
            pwd = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
            submit = st.form_submit_button("ĐĂNG NHẬP HỆ THỐNG")
            
            if submit:
                u = check_login(usr, pwd)
                if u: st.session_state['user_info'] = u; st.rerun()
                else: st.error("Sai thông tin tài khoản hoặc mật khẩu!")

    with col2:
        # Phần banner hình ảnh bên phải
        st.markdown("""
            <div class="banner-container">
                <div class="banner-overlay-top"></div>
                <div class="banner-overlay-bottom"></div>
            </div>
        """, unsafe_allow_html=True)

else:
    # === DASHBOARD (Sau khi đăng nhập) ===
    # (Phần này giữ nguyên logic, chỉ chỉnh lại một chút CSS cho header)
    user = st.session_state['user_info']
    role = user['Role']
    my_name = user['TenHienThi']
    my_username = user['Username']
    
    st.markdown(f"""
        <div class="top-banner" style="margin-top: 20px;"> <h1>CỔNG QUẢN LÝ CÔNG TRÌNH THANH NIÊN</h1>
            <p>{my_name} | {role.upper()}</p>
        </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.info(f"👤 **{my_name}**")
        if st.button("Đăng xuất"): st.session_state['user_info'] = None; st.rerun()
        st.divider()
        menu = st.radio("Menu", ["🏠 Trang chủ", "📝 Quản lý Hoạt động", "📸 Điểm danh"])

    # === TRANG CHỦ ===
    if menu == "🏠 Trang chủ":
        st.subheader("Bảng tin")
        all_acts = get_activities()
        df = pd.DataFrame(all_acts)
        if not df.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tổng hoạt động", len(df))
            c2.metric("Đã duyệt", len(df[df['TrangThai'] == 'Đã duyệt']))
            c3.metric("Chờ xử lý", len(df[df['TrangThai'] == 'Chờ duyệt']))
            finished = len([x for x in all_acts if 'TrangThaiHoanThanh' in x and x['TrangThaiHoanThanh'] == 'Hoàn tất'])
            c4.metric("Đã nghiệm thu", finished)
        else: st.info("Chưa có dữ liệu.")

    # === QUẢN LÝ HOẠT ĐỘNG ===
    elif menu == "📝 Quản lý Hoạt động":
        if role == 'admin':
            tab1, tab2 = st.tabs(["⚡ Cần Duyệt", "🏁 Nghiệm thu Báo cáo"])
            with tab1:
                acts = get_activities()
                pending = [a for a in acts if a['TrangThai'] in ['Chờ duyệt', 'Yêu cầu sửa']]
                if not pending: st.success("Không có hồ sơ chờ duyệt.")
                for act in pending:
                    with st.expander(f"📌 {act['TenHoatDong']} ({act['NguoiTao']})", expanded=True):
                        st.write(f"**Nội dung:** {act['NoiDung']}")
                        with st.form(key=f"d_{act['ID']}"):
                            cmt = st.text_area("Góp ý:")
                            c1, c2 = st.columns(2)
                            if c1.form_submit_button("✅ DUYỆT"):
                                update_activity(act['ID'], "Đã duyệt", cmt)
                                st.success("Đã duyệt!"); time.sleep(1); st.rerun()
                            if c2.form_submit_button("❌ SỬA"):
                                update_activity(act['ID'], "Yêu cầu sửa", cmt)
                                st.warning("Đã trả lại!"); time.sleep(1); st.rerun()
            with tab2:
                acts = get_activities()
                reports = [a for a in acts if a.get('TrangThaiHoanThanh') == 'Đã nộp']
                if not reports: st.info("Chưa có đơn vị nào nộp báo cáo mới.")
                for r in reports:
                    with st.expander(f"📂 Báo cáo: {r['TenHoatDong']} ({r['NguoiTao']})", expanded=True):
                        st.write(f"🔗 **Link minh chứng:** [{r.get('MinhChung')}]({r.get('MinhChung')})")
                        if st.button("🏆 NGHIỆM THU / HOÀN TẤT", key=f"f_{r['ID']}"):
                            finalize_activity(r['ID'])
                            st.balloons(); st.success("Đã ghi nhận thành tích thi đua!"); time.sleep(2); st.rerun()
        else:
            st.subheader("🌿 ĐĂNG KÝ & BÁO CÁO")
            with st.expander("➕ Đăng ký mới"):
                with st.form("add"):
                    name = st.text_input("Tên hoạt động:")
                    content = st.text_area("Mô tả:")
                    if st.form_submit_button("Gửi") and name:
                        submit_activity(name, my_username, content)
                        st.success("Đã gửi!"); time.sleep(1); st.rerun()
            st.subheader("📂 Hồ sơ của tôi")
            my_acts = [a for a in get_activities() if str(a['NguoiTao']) == str(my_username)]
            for act in my_acts:
                stt = act['TrangThai']
                stt_baocao = act.get('TrangThaiHoanThanh', 'Chưa nộp')
                color = "green" if stt == "Đã duyệt" else "orange" if stt == "Chờ duyệt" else "red"
                if stt_baocao == "Hoàn tất": color = "blue"
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{act['TenHoatDong']}**")
                        st.caption(f"Trạng thái: <span style='color:{color};font-weight:bold'>{stt}</span> | Báo cáo: {stt_baocao}", unsafe_allow_html=True)
                        if act['GopY']: st.error(f"Góp ý: {act['GopY']}")
                    with c2:
                        if stt == "Đã duyệt" and stt_baocao != "Hoàn tất":
                            with st.popover("📤 Nộp minh chứng"):
                                link = st.text_input("Link Drive/Ảnh:", key=f"l_{act['ID']}")
                                if st.button("Gửi báo cáo", key=f"s_{act['ID']}"):
                                    submit_report(act['ID'], link); st.success("Đã nộp!"); time.sleep(1); st.rerun()

    # === ĐIỂM DANH ===
    elif menu == "📸 Điểm danh":
        st.subheader("📸 ĐIỂM DANH")
        all_acts = get_activities()
        if role == 'admin':
            valid = [a['TenHoatDong'] for a in all_acts if a['TrangThai'] == 'Đã duyệt']
        else:
            valid = [a['TenHoatDong'] for a in all_acts if a['TrangThai'] == 'Đã duyệt' and str(a['NguoiTao']) == str(my_username)]
        if not valid: st.warning("Không có hoạt động khả dụng.")
        else:
            act = st.selectbox("Chọn:", valid)
            if 'uploader_key' not in st.session_state: st.session_state['uploader_key'] = 0
            img = st.file_uploader("Quét thẻ", type=['png','jpg'], key=f"c_{st.session_state['uploader_key']}")
            if img:
                decoded = decode(Image.open(img))
                if decoded:
                    msg = submit_attendance(decoded[0].data.decode('utf-8'), act, my_name)
                    st.success(msg); time.sleep(1.5); st.session_state['uploader_key'] += 1; st.rerun()
                else: st.error("Lỗi mã")
                #streamlit run app_thanhnien.py