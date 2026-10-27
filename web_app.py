import sys
import os
import io
import time
import base64
import tempfile
from pathlib import Path
from datetime import datetime, date, timedelta

# Ensure UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path (with smart fallback)
BASE_DIR = Path(__file__).resolve().parent
if not (BASE_DIR / "src").exists():
    for fallback in [Path("D:/Manh_Project/HoaDon"), Path("D:/Desktop/HoaDon"), Path("C:/Desktop/HoaDon")]:
        if (fallback / "src").exists():
            BASE_DIR = fallback
            break
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
import importlib

import src.db.security
import src.db.database
importlib.reload(src.db.security)
importlib.reload(src.db.database)

from src.db.database import Database
from src.api.tax_client import TaxClient, NoOriginalRecordError
from src.services.invoice_service import InvoiceService

# ================= 1. PAGE SETUP & STYLES =================

st.set_page_config(
    page_title="Quản Lý Hóa Đơn Điện Tử Phượng Nguyễn",
    page_icon="assets/logo.ico" if (BASE_DIR / "assets" / "logo.ico").exists() else "🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern dark luxury aesthetic
st.markdown("""
<style>
    /* Global styling */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    
    /* Header Card */
    .main-header {
        background: linear-gradient(135deg, #0b1329 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .main-header h1 {
        color: #38bdf8;
        font-size: 22px;
        font-weight: 800;
        margin: 0;
        letter-spacing: 0.5px;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 13px;
        margin: 4px 0 0 0;
    }
    
    /* Metric Cards */
    .metric-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 14px 18px;
        text-align: left;
    }
    .metric-label {
        color: #94a3b8;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 20px;
        font-weight: 800;
    }
    
    /* Status Badges */
    .badge-admin {
        background-color: rgba(2, 132, 199, 0.2);
        color: #38bdf8;
        border: 1px solid #0284c7;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
    }
    .badge-employee {
        background-color: rgba(148, 163, 184, 0.15);
        color: #cbd5e1;
        border: 1px solid #475569;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-login-ok {
        background-color: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border: 1px solid #059669;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
    }
    .badge-login-no {
        background-color: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        border: 1px solid #d97706;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
    }
    
    /* Captcha SVG container */
    .captcha-box {
        background-color: #ffffff;
        border-radius: 6px;
        padding: 6px 12px;
        display: inline-block;
        border: 1px solid #cbd5e1;
    }
</style>
""", unsafe_allow_html=True)

# ================= 2. INITIALIZE SERVICES & STATE =================

# Khởi tạo Database và InvoiceService trực tiếp (không dùng @st.cache_resource để tránh giữ instance cũ khi reload)
db = Database()
invoice_service = InvoiceService(db=db)

# Đảm bảo các hàm truy cập nhân viên luôn sẵn sàng trên db instance
if not hasattr(db, "get_employee_access_code"):
    def _fallback_get_code():
        try:
            from src.db.security import decrypt_text
            with db._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT value FROM system_settings WHERE key = 'employee_access_code'")
                row = cur.fetchone()
                if row and row["value"]:
                    return decrypt_text(row["value"], db._get_db_seed())
        except Exception:
            pass
        return "hoadon2026"
    db.get_employee_access_code = _fallback_get_code

if not hasattr(db, "set_employee_access_code"):
    def _fallback_set_code(code: str):
        try:
            from src.db.security import encrypt_text
            enc_code = encrypt_text(code.strip(), db._get_db_seed())
            with db._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('employee_access_code', ?)", (enc_code,))
                conn.commit()
                return True
        except Exception:
            return False
    db.set_employee_access_code = _fallback_set_code

if not hasattr(db, "verify_employee_access_code"):
    def _fallback_verify_code(code: str):
        if not code:
            return False
        return code.strip() == db.get_employee_access_code().strip()
    db.verify_employee_access_code = _fallback_verify_code

# Session State defaults
if "client" not in st.session_state:
    st.session_state.client = TaxClient()
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_biz_id" not in st.session_state:
    st.session_state.current_biz_id = None
if "current_ckey" not in st.session_state:
    st.session_state.current_ckey = None
if "captcha_svg" not in st.session_state:
    st.session_state.captcha_svg = None
if "invoices" not in st.session_state:
    st.session_state.invoices = []

client = st.session_state.client

def load_captcha():
    try:
        ckey, svg = client.get_captcha()
        st.session_state.current_ckey = ckey
        st.session_state.captcha_svg = svg
    except Exception as e:
        st.sidebar.error(f"Lỗi tải Captcha: {e}")

# ================= 3. ADMIN MASTER SETUP (FIRST-TIME) =================

if not db.is_admin_password_set():
    st.warning("⚠️ Hệ thống chưa thiết lập Mật khẩu Quản trị (Admin). Vui lòng đặt mật khẩu để bảo vệ hệ thống!")
    with st.form("form_initial_admin_setup"):
        st.subheader("👑 Thiết Lập Mật Khẩu Admin Lần Đầu")
        pwd1 = st.text_input("Mật khẩu Admin mới:", type="password")
        pwd2 = st.text_input("Xác nhận lại mật khẩu:", type="password")
        submit_btn = st.form_submit_button("Xác nhận & Kích hoạt Admin")
        if submit_btn:
            if not pwd1 or len(pwd1) < 4:
                st.error("Mật khẩu phải có ít nhất 4 ký tự!")
            elif pwd1 != pwd2:
                st.error("Hai mật khẩu không khớp nhau!")
            else:
                db.set_admin_password(pwd1)
                st.session_state.is_admin = True
                st.success("Đã thiết lập Mật khẩu Admin thành công! Bạn đang ở quyền Quản trị viên.")
                st.rerun()
    st.stop()

# ================= 3.5. CỔNG XÁC THỰC NỘI BỘ (ACCESS GATE) =================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("<br>", unsafe_allow_html=True)
    col_gate_left, col_gate_center, col_gate_right = st.columns([1, 2, 1])
    with col_gate_center:
        st.markdown("""
        <div style="background-color: #111827; border: 1px solid #334155; border-radius: 12px; padding: 24px 20px; text-align: center; margin-bottom: 20px;">
            <div style="font-size: 36px; margin-bottom: 6px;">🔒</div>
            <h2 style="color: #38bdf8; font-size: 20px; font-weight: 800; margin: 0;">XÁC THỰC TRUY CẬP NỘI BỘ</h2>
            <p style="color: #94a3b8; font-size: 13px; margin-top: 4px;">Hệ thống Quản lý & Tra cứu Hóa đơn Điện tử</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_access_gate"):
            access_code = st.text_input(
                "Mã truy cập nội bộ (hoặc Mật khẩu Admin):",
                type="password",
                placeholder="Nhập mã được cấp để truy cập...",
                help="Nhập mã nội bộ do Admin cấp cho nhân viên, hoặc mật khẩu Admin để vào quyền Quản trị."
            )
            submit_gate = st.form_submit_button("🚀 XÁC NHẬN VÀO HỆ THỐNG", use_container_width=True, type="primary")

            if submit_gate:
                if not access_code:
                    st.error("Vui lòng nhập mã truy cập!")
                elif db.verify_admin_password(access_code):
                    st.session_state.authenticated = True
                    st.session_state.is_admin = True
                    st.success("Đăng nhập thành công với Quyền Quản Trị Viên (Admin)!")
                    time.sleep(0.5)
                    st.rerun()
                elif db.verify_employee_access_code(access_code):
                    st.session_state.authenticated = True
                    st.session_state.is_admin = False
                    st.success("Xác thực thành công! Đang chuyển vào Chế độ Nhân viên...")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("⛔ Mã truy cập không chính xác! Bạn không được cấp quyền truy cập hệ thống này.")

        st.caption("🔒 Hệ thống bảo mật nội bộ. Người không được cấp phép không thể xem bất kỳ dữ liệu nào.")

    st.stop()

# ================= 4. SIDEBAR (QUẢN TRỊ & KẾT NỐI THUẾ) =================

with st.sidebar:
    # Logo & App Title
    logo_path = BASE_DIR / "assets" / "logo.ico"
    if logo_path.exists():
        st.image(str(logo_path), width=64)
    st.markdown("### 🏢 HÓA ĐƠN ĐIỆN TỬ")
    st.caption("Cổng Thuế Trực Tiếp - Direct API v1.0")

    st.markdown("---")

    # 4.1. QUẢN LÝ QUYỀN (ROLE: ADMIN / NHÂN VIÊN)
    st.markdown("#### 🔐 Quyền Truy Cập")
    if st.session_state.is_admin:
        st.markdown('<span class="badge-admin">👑 QUẢN TRỊ VIÊN (ADMIN)</span>', unsafe_allow_html=True)
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1:
            if st.button("🚪 Thoát", use_container_width=True, help="Đăng xuất khỏi hệ thống"):
                st.session_state.authenticated = False
                st.session_state.is_admin = False
                st.rerun()
        with col_l2:
            if st.button("🔒 Khóa", use_container_width=True, help="Về chế độ Nhân viên"):
                st.session_state.is_admin = False
                st.rerun()
        with col_l3:
            with st.popover("🔑 Đổi MK"):
                with st.form("form_change_admin_pwd"):
                    old_p = st.text_input("Mật khẩu cũ:", type="password")
                    new_p = st.text_input("Mật khẩu mới:", type="password")
                    con_p = st.text_input("Xác nhận:", type="password")
                    if st.form_submit_button("Lưu"):
                        if not db.verify_admin_password(old_p):
                            st.error("Mật khẩu cũ không đúng!")
                        elif len(new_p) < 4 or new_p != con_p:
                            st.error("Mật khẩu mới không hợp lệ hoặc không khớp!")
                        else:
                            db.set_admin_password(new_p)
                            st.success("Đã đổi mật khẩu thành công!")

        # Quản lý mã truy cập nhân viên (Admin only)
        with st.expander("🛡️ Mã Truy Cập Cho Nhân Viên"):
            current_emp_code = db.get_employee_access_code()
            st.info(f"Mã hiện tại: **`{current_emp_code}`**")
            with st.form("form_change_emp_code"):
                new_emp_code = st.text_input("Đổi mã truy cập mới cho nhân viên:", placeholder="Nhập mã mới...")
                if st.form_submit_button("Lưu Mã Mới"):
                    if not new_emp_code or len(new_emp_code) < 3:
                        st.error("Mã truy cập phải có ít nhất 3 ký tự!")
                    else:
                        db.set_employee_access_code(new_emp_code.strip())
                        st.success(f"Đã cập nhật mã mới: {new_emp_code.strip()}")
                        time.sleep(0.8)
                        st.rerun()
            st.caption("💡 Đổi mã này khi có nhân viên nghỉ việc để chặn truy cập ngay lập tức.")
    else:
        st.markdown('<span class="badge-employee">👤 NHÂN VIÊN ĐƯỢC CẤP PHÉP</span>', unsafe_allow_html=True)
        col_emp1, col_emp2 = st.columns(2)
        with col_emp1:
            if st.button("🚪 Đăng xuất", use_container_width=True, help="Đăng xuất khỏi hệ thống"):
                st.session_state.authenticated = False
                st.session_state.is_admin = False
                st.rerun()
        with col_emp2:
            with st.popover("👑 Mở Admin"):
                with st.form("form_unlock_admin"):
                    admin_p = st.text_input("Mật khẩu Admin:", type="password")
                    if st.form_submit_button("Mở khóa"):
                        if db.verify_admin_password(admin_p):
                            st.session_state.is_admin = True
                            st.success("Đã mở khóa quyền Admin!")
                            st.rerun()
                        else:
                            st.error("Mật khẩu Admin không chính xác!")

    st.markdown("---")

    # 4.2. CHỌN DOANH NGHIỆP
    st.markdown("#### 🏢 Chọn Doanh Nghiệp")
    businesses = db.get_all_businesses()
    biz_options = {b["id"]: f"{b['tax_code']} - {b['name']}" for b in businesses}
    
    current_biz = None
    if businesses:
        default_index = 0
        if st.session_state.current_biz_id in biz_options:
            default_index = list(biz_options.keys()).index(st.session_state.current_biz_id)
        
        selected_id = st.selectbox(
            "Doanh nghiệp hoạt động:",
            options=list(biz_options.keys()),
            format_func=lambda x: biz_options[x],
            index=default_index,
            label_visibility="collapsed"
        )
        st.session_state.current_biz_id = selected_id
        current_biz = next((b for b in businesses if b["id"] == selected_id), None)
    else:
        st.warning("Chưa có doanh nghiệp nào trong hệ thống.")

    # 4.3. TRẠNG THÁI & ĐĂNG NHẬP CỔNG THUẾ
    st.markdown("#### 🔑 Phiên Làm Việc Cổng Thuế")
    token_valid = False
    if current_biz:
        token = current_biz.get("token")
        if token:
            client.set_token(token)
            token_valid = client.check_token_valid()

    if token_valid:
        st.markdown(f'<span class="badge-login-ok">🟢 ĐÃ ĐĂNG NHẬP ({current_biz["tax_code"]})</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-login-no">🔑 CẦN ĐĂNG NHẬP CỔNG THUẾ</span>', unsafe_allow_html=True)

    # Form đăng nhập Cổng Thuế
    with st.expander("🔐 Đăng nhập / Gia hạn Token Thuế", expanded=not token_valid):
        if not st.session_state.captcha_svg:
            load_captcha()

        if current_biz:
            st.text_input("Mã số thuế:", value=current_biz["tax_code"], disabled=True)
            # Mật khẩu thuế tự động lấy từ DB, hiển thị ẩn
            pwd_to_use = current_biz.get("password", "")
            st.text_input("Mật khẩu thuế:", value="●●●●●●●●●●●●", disabled=True)
            
            # Captcha SVG render
            st.markdown("**Mã kiểm tra (Captcha GDT):**")
            col_cap1, col_cap2 = st.columns([3, 1])
            with col_cap1:
                if st.session_state.captcha_svg:
                    b64_svg = base64.b64encode(st.session_state.captcha_svg.encode("utf-8")).decode("utf-8")
                    st.markdown(
                        f'<div class="captcha-box"><img src="data:image/svg+xml;base64,{b64_svg}" width="160" /></div>',
                        unsafe_allow_html=True
                    )
            with col_cap2:
                if st.button("🔄", help="Đổi mã Captcha"):
                    load_captcha()
                    st.rerun()

            captcha_input = st.text_input("Nhập mã chữ/số:", key="txt_captcha_input")

            if st.button("🚀 Đăng Nhập Cổng Thuế", type="primary", use_container_width=True):
                if not captcha_input:
                    st.error("Vui lòng nhập mã Captcha!")
                else:
                    with st.spinner("Đang xác thực với Cổng Thuế..."):
                        try:
                            token = client.login(
                                current_biz["tax_code"],
                                pwd_to_use,
                                captcha_input,
                                st.session_state.current_ckey
                            )
                            db.update_business_token(current_biz["id"], token)
                            client.set_token(token)
                            st.success("Đăng nhập Cổng Thuế thành công!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Đăng nhập thất bại: {e}")
                            load_captcha()
                            st.rerun()
        else:
            st.info("Vui lòng thêm hoặc chọn doanh nghiệp trước.")

    # 4.4. QUẢN LÝ DOANH NGHIỆP (ADMIN ONLY)
    if st.session_state.is_admin:
        st.markdown("---")
        with st.expander("🛠️ Quản Trị Danh Sách Doanh Nghiệp"):
            st.markdown("**Thêm mới / Cập nhật:**")
            with st.form("form_manage_biz"):
                in_mst = st.text_input("Mã số thuế (MST):")
                in_name = st.text_input("Tên doanh nghiệp:")
                in_pwd = st.text_input("Mật khẩu Cổng Thuế:", type="password")
                btn_save_biz = st.form_submit_button("💾 Lưu Doanh Nghiệp")
                if btn_save_biz:
                    if not in_mst or not in_pwd:
                        st.error("Vui lòng nhập MST và Mật khẩu!")
                    else:
                        n = in_name.strip() if in_name.strip() else f"Doanh nghiệp {in_mst.strip()}"
                        db.save_business(in_mst.strip(), n, in_pwd.strip())
                        st.success(f"Đã lưu thành công: {n}")
                        st.rerun()

            if current_biz:
                st.markdown("---")
                st.markdown(f"**Xóa {current_biz['name']}:**")
                if st.button(f"🗑️ Xóa MST {current_biz['tax_code']}", type="secondary"):
                    db.delete_business(current_biz["id"])
                    st.warning("Đã xóa doanh nghiệp khỏi hệ thống!")
                    st.rerun()

# ================= 5. MAIN AREA: BỘ LỌC & TRA CỨU HÓA ĐƠN =================

# Header Banner
st.markdown("""
<div class="main-header">
    <div>
        <h1>HỆ THỐNG QUẢN LÝ & TRA CỨU HÓA ĐƠN ĐIỆN TỬ</h1>
        <p>Kết nối trực tiếp Cổng Thuế (hoadondientu.gdt.gov.vn) • Bảo mật nội bộ • Tra cứu & Xuất Excel tức thì</p>
    </div>
</div>
""", unsafe_allow_html=True)

if not current_biz:
    st.info("👉 Vui lòng chọn hoặc thêm doanh nghiệp ở thanh bên trái để bắt đầu tra cứu.")
    st.stop()

# 5.1. BỘ LỌC KỲ KẾ TOÁN & LOẠI HÓA ĐƠN
filter_col1, filter_col2, filter_col3 = st.columns([2, 4, 3])

with filter_col1:
    inv_type = st.radio(
        "Loại hóa đơn:",
        options=["purchase", "sold"],
        format_func=lambda x: "📥 Hóa đơn Mua vào" if x == "purchase" else "📤 Hóa đơn Bán ra",
        horizontal=True
    )

with filter_col2:
    period_type = st.radio(
        "Kỳ kế toán:",
        options=["Tháng", "Quý", "Năm", "Khoảng ngày"],
        horizontal=True
    )

current_year = datetime.now().year
from_date_str = ""
to_date_str = ""

with filter_col3:
    if period_type == "Tháng":
        c_m, c_y = st.columns(2)
        with c_m:
            sel_month = st.selectbox("Tháng:", range(1, 13), index=datetime.now().month - 1)
        with c_y:
            sel_year = st.number_input("Năm:", min_value=2020, max_value=2030, value=current_year)
        start_d = date(sel_year, sel_month, 1)
        if sel_month == 12:
            end_d = date(sel_year + 1, 1, 1) - timedelta(days=1)
        else:
            end_d = date(sel_year, sel_month + 1, 1) - timedelta(days=1)
        from_date_str = start_d.strftime("%d/%m/%Y")
        to_date_str = end_d.strftime("%d/%m/%Y")

    elif period_type == "Quý":
        c_q, c_y = st.columns(2)
        with c_q:
            current_q = (datetime.now().month - 1) // 3 + 1
            sel_quarter = st.selectbox("Quý:", [1, 2, 3, 4], index=current_q - 1)
        with c_y:
            sel_year = st.number_input("Năm:", min_value=2020, max_value=2030, value=current_year)
        start_m = (sel_quarter - 1) * 3 + 1
        start_d = date(sel_year, start_m, 1)
        if sel_quarter == 4:
            end_d = date(sel_year, 12, 31)
        else:
            end_d = date(sel_year, start_m + 3, 1) - timedelta(days=1)
        from_date_str = start_d.strftime("%d/%m/%Y")
        to_date_str = end_d.strftime("%d/%m/%Y")

    elif period_type == "Năm":
        sel_year = st.number_input("Năm:", min_value=2020, max_value=2030, value=current_year)
        from_date_str = f"01/01/{sel_year}"
        to_date_str = f"31/12/{sel_year}"

    else:
        c_from, c_to = st.columns(2)
        with c_from:
            d_from = st.date_input("Từ ngày:", value=datetime.now() - timedelta(days=30))
        with c_to:
            d_to = st.date_input("Đến ngày:", value=datetime.now())
        from_date_str = d_from.strftime("%d/%m/%Y")
        to_date_str = d_to.strftime("%d/%m/%Y")

# 5.2. HÀNG NÚT THAO TÁC TRA CỨU & ĐỒNG BỘ
st.markdown("<br>", unsafe_allow_html=True)
btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 5])

with btn_col1:
    btn_search_local = st.button("🔍 TÌM NỘI BỘ (OFFLINE)", use_container_width=True, type="secondary")

with btn_col2:
    btn_sync_tax = st.button("☁️ ĐỒNG BỘ CỔNG THUẾ", use_container_width=True, type="primary")

with btn_col3:
    biz_title = current_biz["name"] if current_biz else "Chưa chọn doanh nghiệp"
    st.info(f"📅 Khoảng thời gian: **{from_date_str}** đến **{to_date_str}** | Đơn vị: **{biz_title}**")

# Xử lý sự kiện Tìm Nội Bộ
if btn_search_local:
    with st.spinner("Đang truy vấn cơ sở dữ liệu nội bộ..."):
        invoices = db.search_local_invoices(
            business_id=current_biz["id"],
            inv_type=inv_type,
            from_date_str=from_date_str,
            to_date_str=to_date_str
        )
        st.session_state.invoices = invoices
        st.toast(f"Đã tải {len(invoices)} hóa đơn từ cơ sở dữ liệu nội bộ!", icon="✅")

# Xử lý sự kiện Đồng Bộ Cổng Thuế
if btn_sync_tax:
    if not token_valid:
        st.error("Phiên làm việc Cổng Thuế chưa đăng nhập hoặc đã hết hạn. Vui lòng đăng nhập ở thanh bên trái!")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text(f"Đang kết nối Cổng Thuế ({from_date_str} - {to_date_str})...")

        try:
            def sync_progress(msg):
                status_text.text(msg)

            fetched_invoices = client.search_invoices(
                inv_type=inv_type,
                from_date_str=from_date_str,
                to_date_str=to_date_str,
                is_sco=False,
                progress_callback=sync_progress
            )
            total = len(fetched_invoices)
            status_text.text(f"Đang lưu {total} hóa đơn vào cơ sở dữ liệu...")

            for idx, inv in enumerate(fetched_invoices):
                row_id = db.upsert_invoice(current_biz["id"], inv_type, inv)
                inv["id"] = row_id
                progress_bar.progress((idx + 1) / total if total > 0 else 1.0)

            status_text.empty()
            progress_bar.empty()

            # Refresh local view
            st.session_state.invoices = db.search_local_invoices(
                business_id=current_biz["id"],
                inv_type=inv_type,
                from_date_str=from_date_str,
                to_date_str=to_date_str
            )
            st.success(f"Đồng bộ thành công! Tìm thấy và lưu {total} hóa đơn từ Tổng Cục Thuế.")
            st.balloons()
        except Exception as e:
            status_text.empty()
            progress_bar.empty()
            st.error(f"Lỗi đồng bộ Cổng Thuế: {e}")

# ================= 6. METRICS & BẢNG DỮ LIỆU =================

invoices = st.session_state.invoices

total_count = len(invoices)
total_pretax = sum(float(inv.get("tgtcthue") or 0) for inv in invoices)
total_vat = sum(float(inv.get("tgtthue") or 0) for inv in invoices)
total_all = sum(float(inv.get("tgtttbso") or 0) for inv in invoices)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">📄 TỔNG SỐ HÓA ĐƠN</div><div class="metric-value">{total_count:,}</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">💰 TIỀN HÀNG (CHƯA THUẾ)</div><div class="metric-value">{total_pretax:,.0f} đ</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card"><div class="metric-label">🏷️ TIỀN THUẾ VAT</div><div class="metric-value">{total_vat:,.0f} đ</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">💳 TỔNG THANH TOÁN</div><div class="metric-value">{total_all:,.0f} đ</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Tabs hiển thị
tab_table, tab_download = st.tabs(["📋 Danh Sách Hóa Đơn Chi Tiết", "📥 Xuất Báo Cáo & Tải Tệp Gốc"])

with tab_table:
    if invoices:
        # Search box in table
        search_query = st.text_input("🔍 Lọc nhanh theo số HĐ, MST hoặc tên đối tác:", "").strip().lower()

        table_rows = []
        for inv in invoices:
            shdon = str(inv.get("shdon", ""))
            khhdon = str(inv.get("khhdon", ""))
            tdlap = str(inv.get("tdlap", ""))[:10]
            nbmst = str(inv.get("nbmst", ""))
            nbten = str(inv.get("nbten", ""))
            nmmst = str(inv.get("nmmst", ""))
            nmten = str(inv.get("nmten", ""))
            tgtcthue = float(inv.get("tgtcthue") or 0)
            tgtthue = float(inv.get("tgtthue") or 0)
            tgtttbso = float(inv.get("tgtttbso") or 0)
            ttxly = str(inv.get("ttxly", ""))

            partner_name = nbten if inv_type == "purchase" else nmten
            partner_mst = nbmst if inv_type == "purchase" else nmmst

            # Search filter check
            if search_query:
                combined_text = f"{shdon} {khhdon} {partner_mst} {partner_name}".lower()
                if search_query not in combined_text:
                    continue

            table_rows.append({
                "Số HĐ": shdon,
                "Ký hiệu": khhdon,
                "Ngày lập": tdlap,
                "Tên Đối Tác": partner_name,
                "MST Đối Tác": partner_mst,
                "Tiền chưa thuế": f"{tgtcthue:,.0f} đ",
                "Tiền thuế": f"{tgtthue:,.0f} đ",
                "Tổng thanh toán": f"{tgtttbso:,.0f} đ",
                "Trạng thái": ttxly
            })

        if table_rows:
            df = pd.DataFrame(table_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"Đang hiển thị {len(table_rows)} / {total_count} hóa đơn.")
        else:
            st.info("Không có hóa đơn nào khớp với từ khóa tìm kiếm.")
    else:
        st.info("Chưa có dữ liệu hiển thị. Hãy bấm '🔍 TÌM NỘI BỘ' hoặc '☁️ ĐỒNG BỘ CỔNG THUẾ' ở trên.")

with tab_download:
    st.markdown("#### 📥 Xuất Dữ Liệu Báo Cáo")
    if invoices:
        col_ex1, col_ex2 = st.columns(2)
        
        # 1. Xuất Excel Bảng Kê Tiêu Chuẩn
        with col_ex1:
            st.markdown("**Bảng Kê Tiêu Chuẩn (Tổng hợp):**")
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            try:
                invoice_service.export_excel(invoices, export_type="standard", output_filepath=tmp_path)
                with open(tmp_path, "rb") as f:
                    excel_bytes = f.read()
                os.remove(tmp_path)

                fname_std = f"BangKe_HoaDon_{inv_type}_{current_biz['tax_code']}_{from_date_str.replace('/', '')}_{to_date_str.replace('/', '')}.xlsx"
                st.download_button(
                    label="📊 Tải Bảng Kê Excel (Tiêu chuẩn)",
                    data=excel_bytes,
                    file_name=fname_std,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Lỗi tạo Excel tiêu chuẩn: {e}")

        # 2. Xuất Excel Bảng Kê Chi Tiết Hàng Hóa
        with col_ex2:
            st.markdown("**Bảng Kê Chi Tiết (Từng dòng hàng hóa):**")
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
                tmp_path2 = tmp_file.name
            try:
                invoice_service.export_excel(invoices, export_type="detailed", output_filepath=tmp_path2)
                with open(tmp_path2, "rb") as f:
                    excel_bytes2 = f.read()
                os.remove(tmp_path2)

                fname_dtl = f"ChiTiet_HangHoa_{inv_type}_{current_biz['tax_code']}_{from_date_str.replace('/', '')}_{to_date_str.replace('/', '')}.xlsx"
                st.download_button(
                    label="📑 Tải Bảng Kê Excel (Chi tiết hàng hóa)",
                    data=excel_bytes2,
                    file_name=fname_dtl,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Lỗi tạo Excel chi tiết: {e}")
    else:
        st.info("Chưa có hóa đơn nào để xuất dữ liệu. Vui lòng tra cứu hoặc đồng bộ trước.")
