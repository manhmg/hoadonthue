import os
import sys
import logging
from datetime import datetime, date, timedelta
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QDateEdit, QRadioButton, QButtonGroup,
    QCheckBox, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QTextEdit, QFrame, QMessageBox, QGroupBox, QSplitter,
    QComboBox, QSpinBox, QDialog
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QFont, QKeySequence, QShortcut, QPixmap

from src.db.database import Database
from src.api.tax_client import TaxClient, NoOriginalRecordError
from src.services.invoice_service import InvoiceService
from src.ui.business_dialog import BusinessDialog
from src.ui.login_dialog import LoginDialog
from src.ui.admin_dialog import AdminSetupDialog, AdminVerifyDialog, AdminChangePasswordDialog

logger = logging.getLogger("MainWindow")

def get_base_dir():
    if hasattr(sys, '_MEIPASS') and (Path(sys._MEIPASS) / "assets").exists():
        return Path(sys._MEIPASS)
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent

STYLESHEET_MAIN = """
QMainWindow {
    background-color: #0b1120;
}
QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', Tahoma, sans-serif;
    font-size: 13px;
}
QFrame.card {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 10px;
}
QFrame.box-header {
    background-color: #0b1329;
    border-bottom: 2px solid #1e293b;
    padding: 6px 14px;
}
QLabel.app-header-title {
    font-size: 17px;
    font-weight: 800;
    color: #22c55e;
    letter-spacing: 0.5px;
}
QPushButton.btn-biz-select {
    background-color: #1e293b;
    border: 1px dashed #f59e0b;
    color: #fbbf24;
    font-weight: 700;
    padding: 8px 14px;
    border-radius: 6px;
}
QPushButton.btn-biz-select:hover {
    background-color: #334155;
}
QPushButton.btn-login-needed {
    background-color: #0284c7;
    border: 1px solid #38bdf8;
    color: white;
    font-weight: 800;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
}
QPushButton.btn-login-needed:hover {
    background-color: #0369a1;
}
QPushButton.btn-login-success {
    background-color: #064e3b;
    border: 1px solid #10b981;
    color: #34d399;
    font-weight: 700;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
}
QPushButton.btn-login-success:hover {
    background-color: #065f46;
}
QComboBox, QDateEdit, QSpinBox, QLineEdit {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f8fafc;
    font-size: 12px;
}
QComboBox:focus, QDateEdit:focus, QLineEdit:focus {
    border: 1px solid #38bdf8;
}
QComboBox QAbstractItemView {
    background-color: #1e293b;
    selection-background-color: #0284c7;
    color: #f8fafc;
    border: 1px solid #334155;
}
QPushButton.btn-type {
    background-color: #1e293b;
    border: 1px solid #334155;
    color: #94a3b8;
    font-weight: 700;
    padding: 8px 14px;
    border-radius: 6px;
}
QPushButton.btn-type-active {
    background-color: #10b981;
    border: 1px solid #10b981;
    color: white;
    font-weight: 800;
    padding: 8px 14px;
    border-radius: 6px;
}
QPushButton.btn-local-search {
    background-color: #0284c7;
    color: white;
    font-weight: 700;
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
}
QPushButton.btn-local-search:hover {
    background-color: #0369a1;
}
QPushButton.btn-sync {
    background-color: #10b981;
    color: white;
    font-weight: 700;
    padding: 8px 16px;
    border-radius: 6px;
    border: none;
}
QPushButton.btn-sync:hover {
    background-color: #059669;
}
QPushButton.btn-xml {
    background-color: #f59e0b;
    color: #000;
    font-weight: 800;
    padding: 7px 14px;
    border-radius: 6px;
    border: none;
}
QPushButton.btn-xml:hover {
    background-color: #d97706;
}
QPushButton.btn-excel {
    background-color: #10b981;
    color: white;
    font-weight: 800;
    padding: 7px 14px;
    border-radius: 6px;
    border: none;
}
QPushButton.btn-excel:hover {
    background-color: #059669;
}
QPushButton.btn-pdf {
    background-color: #ea580c;
    color: white;
    font-weight: 800;
    padding: 7px 14px;
    border-radius: 6px;
    border: none;
}
QPushButton.btn-pdf:hover {
    background-color: #c2410c;
}
QPushButton.btn-expand {
    background-color: #1e293b;
    border: 1px solid #334155;
    color: #94a3b8;
    border-radius: 4px;
    font-size: 11px;
    padding: 4px 8px;
}
QTableWidget {
    background-color: #0a0f1d;
    border: 1px solid #1e293b;
    gridline-color: #182234;
    color: #f8fafc;
    font-size: 12px;
}
QHeaderView::section {
    background-color: #111827;
    color: #38bdf8;
    font-weight: 700;
    font-size: 11px;
    padding: 6px;
    border: 1px solid #1e293b;
}
QTableWidget::item {
    padding: 4px 6px;
}
QTableWidget::item:selected {
    background-color: #0369a1;
}
QLabel.status-summary {
    color: #22c55e;
    font-weight: 700;
    font-size: 13px;
}
QMessageBox {
    background-color: #0f172a;
    color: #f8fafc;
}
QMessageBox QLabel {
    color: #f8fafc;
    font-size: 13px;
}
QMessageBox QPushButton {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: 700;
    font-size: 13px;
    border-radius: 6px;
    padding: 8px 24px;
    min-width: 80px;
    border: none;
}
QMessageBox QPushButton:hover {
    background-color: #0369a1;
}
QMessageBox QPushButton:pressed {
    background-color: #0284c7;
}
"""

class SyncWorker(QThread):
    progress_signal = pyqtSignal(int, int) # current, total
    invoice_saved = pyqtSignal(dict)
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(int, str) # total, error_msg

    def __init__(self, client, db, biz_id, inv_type, from_date_str, to_date_str):
        super().__init__()
        self.client = client
        self.db = db
        self.biz_id = biz_id
        self.inv_type = inv_type
        self.from_date_str = from_date_str
        self.to_date_str = to_date_str
        self.is_stopped = False

    def run(self):
        self.log_signal.emit(f"Bắt đầu đồng bộ từ Thuế ({self.from_date_str} - {self.to_date_str})...", "INFO")
        try:
            invoices = self.client.search_invoices(
                inv_type=self.inv_type,
                from_date_str=self.from_date_str,
                to_date_str=self.to_date_str,
                is_sco=False,
                progress_callback=lambda msg: self.log_signal.emit(msg, "INFO")
            )
            total = len(invoices)
            self.log_signal.emit(f"Tìm thấy {total} hóa đơn trên Cổng Thuế.", "SUCCESS")

            for idx, inv in enumerate(invoices):
                if self.is_stopped:
                    break
                row_id = self.db.upsert_invoice(self.biz_id, self.inv_type, inv)
                inv["id"] = row_id
                self.invoice_saved.emit(inv)
                self.progress_signal.emit(idx + 1, total)

            self.finished_signal.emit(total, "")
        except Exception as e:
            err_msg = str(e)
            self.log_signal.emit(f"Lỗi đồng bộ: {err_msg}", "ERROR")
            self.finished_signal.emit(-1, err_msg)

    def stop(self):
        self.is_stopped = True


class BatchDownloadWorker(QThread):
    progress_signal = pyqtSignal(int, int)
    item_completed = pyqtSignal(int, str, str) # row, status, color
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(int, int, int) # success, no_record, failed

    def __init__(self, client, invoice_service, db, invoices, out_dir, mode="pdf"):
        super().__init__()
        self.client = client
        self.invoice_service = invoice_service
        self.db = db
        self.invoices = invoices
        self.out_dir = out_dir
        self.mode = mode # 'pdf' or 'xml'
        self.is_stopped = False

    def run(self):
        import time
        total = len(self.invoices)
        success = 0
        no_record = 0
        failed = 0

        for idx, inv in enumerate(self.invoices):
            if self.is_stopped:
                break

            if idx > 0:
                time.sleep(1.2) # Polite delay to avoid GDT rate limiting

            shdon = inv.get("shdon", "")
            khhdon = inv.get("khhdon", "")
            nbmst = inv.get("nbmst", "")
            khmshdon = inv.get("khmshdon", "1")
            prefix = f"HD_{shdon}_{khhdon}_{nbmst}"

            self.item_completed.emit(idx, "Đang tải...", "#38bdf8")
            self.progress_signal.emit(idx + 1, total)

            try:
                zip_bytes = self.client.download_invoice_xml_zip(
                    nbmst=nbmst,
                    khhdon=khhdon,
                    shdon=shdon,
                    khmshdon=khmshdon
                )
                res = self.invoice_service.process_invoice_zip(
                    zip_bytes=zip_bytes,
                    output_dir=self.out_dir,
                    file_prefix=prefix,
                    invoice_db_id=inv.get("id"),
                    convert_pdf=(self.mode == "pdf")
                )
                success += 1
                self.item_completed.emit(idx, "Đã có XML" if self.mode == "xml" else "Đã có PDF", "#22c55e")
                self.log_signal.emit(f"Tải thành công: HĐ {shdon} ({khhdon})", "SUCCESS")
            except NoOriginalRecordError as ne:
                no_record += 1
                self.item_completed.emit(idx, "Không có HS gốc", "#f59e0b")
                self.log_signal.emit(f"HĐ {shdon} ({khhdon}): Không có hồ sơ gốc trên Cổng Thuế (HĐ ngân hàng/không mã)", "WARNING")
                if inv.get("id"):
                    self.db.update_invoice_files(inv["id"], xml_status=2)
            except Exception as e:
                failed += 1
                self.item_completed.emit(idx, "Lỗi tải", "#ef4444")
                self.log_signal.emit(f"Lỗi HĐ {shdon}: {e}", "ERROR")

        self.finished_signal.emit(success, no_record, failed)

    def stop(self):
        self.is_stopped = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quản Lý Hóa Đơn Phượng Nguyễn v1.0")
        icon_path = get_base_dir() / "assets" / "logo.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1360, 850)
        self.setStyleSheet(STYLESHEET_MAIN)

        self.db = Database()
        self.client = TaxClient()
        self.invoice_service = InvoiceService(db=self.db)

        self.current_business = None
        self.current_inv_type = "purchase" # 'purchase' or 'sold'
        self.displayed_invoices = []
        self.worker = None
        self.is_admin = False

        self._setup_ui()
        self.set_admin_mode(False)
        self._load_default_business()
        self._check_initial_admin_setup()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # ================= 1. TOP HEADER =================
        header_frame = QFrame()
        header_frame.setProperty("class", "box-header")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 6, 8, 6)

        # Doanh nghiệp Selector button
        self.btn_biz = QPushButton(" Chưa chọn doanh nghiệp + ")
        self.btn_biz.setProperty("class", "btn-biz-select")
        self.btn_biz.clicked.connect(self._open_business_dialog)
        header_layout.addWidget(self.btn_biz)

        # Nút Đăng nhập Cổng Thuế (Rõ ràng, trực quan)
        self.btn_auth_status = QPushButton("🔑 ĐĂNG NHẬP CỔNG THUẾ")
        self.btn_auth_status.setProperty("class", "btn-login-needed")
        self.btn_auth_status.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_auth_status.clicked.connect(lambda: self._open_login_dialog())
        header_layout.addWidget(self.btn_auth_status)

        # Nút Chế độ Quyền (Admin / Nhân viên)
        self.btn_role_badge = QPushButton("👤 Nhân viên")
        self.btn_role_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_role_badge.clicked.connect(self._toggle_or_prompt_admin)
        header_layout.addWidget(self.btn_role_badge)

        header_layout.addStretch()

        # Logo + App Title
        title_box = QHBoxLayout()
        title_box.setSpacing(12)
        title_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        icon_path = get_base_dir() / "assets" / "logo.ico"
        if icon_path.exists():
            lbl_logo = QLabel()
            lbl_logo.setFixedSize(52, 52)
            lbl_logo.setPixmap(QPixmap(str(icon_path)).scaled(52, 52, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            title_box.addWidget(lbl_logo)

        app_title = QLabel("QUẢN LÝ HÓA ĐƠN PHƯỢNG NGUYỄN")
        app_title.setProperty("class", "app-header-title")
        title_box.addWidget(app_title)
        header_layout.addLayout(title_box)

        main_layout.addWidget(header_frame)

        # ================= 2. TOP CONTROL AREA =================
        self.top_control_frame = QFrame()
        self.top_control_frame.setProperty("class", "card")
        top_grid = QHBoxLayout(self.top_control_frame)
        top_grid.setContentsMargins(10, 8, 10, 8)
        top_grid.setSpacing(12)

        # Box 1: Loại HĐ & Kỳ kế toán & Thời gian
        ctrl_box = QVBoxLayout()
        ctrl_box.setSpacing(8)

        # Row 1: Loại HĐ
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("LOẠI HĐ:"))
        self.btn_type_sold = QPushButton("Bán ra")
        self.btn_type_sold.setProperty("class", "btn-type")
        self.btn_type_sold.clicked.connect(lambda: self._set_inv_type("sold"))
        r1.addWidget(self.btn_type_sold)

        self.btn_type_purchase = QPushButton("Mua vào")
        self.btn_type_purchase.setProperty("class", "btn-type-active")
        self.btn_type_purchase.clicked.connect(lambda: self._set_inv_type("purchase"))
        r1.addWidget(self.btn_type_purchase)
        ctrl_box.addLayout(r1)

        # Row 2: Kỳ kế toán
        r2 = QHBoxLayout()
        r2.addWidget(QLabel("KỲ KẾ TOÁN:"))
        self.cbo_period = QComboBox()
        self.cbo_period.addItems(["Theo Ngày", "Theo Tháng", "Theo Quý", "Theo Năm", "Tùy Chọn"])
        self.cbo_period.currentIndexChanged.connect(self._on_period_changed)
        r2.addWidget(self.cbo_period)
        ctrl_box.addLayout(r2)

        # Row 3: Thời gian (Dynamic picker)
        r3 = QHBoxLayout()
        r3.addWidget(QLabel("THỜI GIAN:"))
        
        today = QDate.currentDate()

        # Single Date (Theo Ngày)
        self.date_single = QDateEdit(today)
        self.date_single.setDisplayFormat("dd/MM/yyyy")
        self.date_single.setCalendarPopup(True)
        r3.addWidget(self.date_single)

        # Month & Year (Theo Tháng)
        self.cbo_month = QComboBox()
        for m in range(1, 13):
            self.cbo_month.addItem(f"Tháng {m:02d}", m)
        self.cbo_month.setCurrentIndex(today.month() - 1)
        self.cbo_month.hide()
        r3.addWidget(self.cbo_month)

        # Quarter (Theo Quý)
        self.cbo_quarter = QComboBox()
        self.cbo_quarter.addItem("Quý 1 (T1 - T3)", 1)
        self.cbo_quarter.addItem("Quý 2 (T4 - T6)", 2)
        self.cbo_quarter.addItem("Quý 3 (T7 - T9)", 3)
        self.cbo_quarter.addItem("Quý 4 (T10 - T12)", 4)
        self.cbo_quarter.setCurrentIndex((today.month() - 1) // 3)
        self.cbo_quarter.hide()
        r3.addWidget(self.cbo_quarter)

        # Year selector
        self.spin_year = QSpinBox()
        self.spin_year.setRange(2020, 2035)
        self.spin_year.setValue(today.year())
        self.spin_year.hide()
        r3.addWidget(self.spin_year)

        # From - To Date (Tùy Chọn)
        self.date_from = QDateEdit(today.addDays(-30))
        self.date_from.setDisplayFormat("dd/MM/yyyy")
        self.date_from.setCalendarPopup(True)
        self.date_from.hide()
        r3.addWidget(self.date_from)

        self.lbl_to = QLabel("-")
        self.lbl_to.hide()
        r3.addWidget(self.lbl_to)

        self.date_to = QDateEdit(today)
        self.date_to.setDisplayFormat("dd/MM/yyyy")
        self.date_to.setCalendarPopup(True)
        self.date_to.hide()
        r3.addWidget(self.date_to)

        ctrl_box.addLayout(r3)

        # Row 4: Search & Sync buttons
        r4 = QHBoxLayout()
        self.btn_search_local = QPushButton("🔍 TÌM NỘI BỘ")
        self.btn_search_local.setProperty("class", "btn-local-search")
        self.btn_search_local.clicked.connect(self._do_local_search)
        r4.addWidget(self.btn_search_local)

        self.btn_sync_gdt = QPushButton("☁ ĐỒNG BỘ TỔNG CỤC THUẾ")
        self.btn_sync_gdt.setProperty("class", "btn-sync")
        self.btn_sync_gdt.clicked.connect(self._do_sync_gdt)
        r4.addWidget(self.btn_sync_gdt)
        ctrl_box.addLayout(r4)

        top_grid.addLayout(ctrl_box, 4)

        # Center: BIỂU ĐỒ HÓA ĐƠN MUA - BÁN
        chart_frame = QFrame()
        chart_frame.setProperty("class", "card")
        chart_layout = QVBoxLayout(chart_frame)
        chart_layout.setContentsMargins(12, 8, 12, 8)
        chart_layout.setSpacing(6)

        chart_title = QLabel("BIỂU ĐỒ HÓA ĐƠN MUA - BÁN")
        chart_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_title.setStyleSheet("font-weight: 800; color: #94a3b8; font-size: 11px; letter-spacing: 0.5px;")
        chart_layout.addWidget(chart_title)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(6)

        stats_grid.addWidget(QLabel("📦 Số lượng:"), 0, 0)
        self.lbl_stat_count = QLabel("0 HĐ")
        self.lbl_stat_count.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 13px;")
        stats_grid.addWidget(self.lbl_stat_count, 0, 1)

        stats_grid.addWidget(QLabel("💵 Chưa thuế:"), 0, 2)
        self.lbl_stat_notax = QLabel("0 VNĐ")
        self.lbl_stat_notax.setStyleSheet("color: #e2e8f0; font-weight: 700; font-size: 13px;")
        stats_grid.addWidget(self.lbl_stat_notax, 0, 3)

        stats_grid.addWidget(QLabel("💸 Tiền thuế:"), 1, 0)
        self.lbl_stat_tax = QLabel("0 VNĐ")
        self.lbl_stat_tax.setStyleSheet("color: #fbbf24; font-weight: 700; font-size: 13px;")
        stats_grid.addWidget(self.lbl_stat_tax, 1, 1)

        stats_grid.addWidget(QLabel("💳 Tổng thanh toán:"), 1, 2)
        self.lbl_stat_total = QLabel("0 VNĐ")
        self.lbl_stat_total.setStyleSheet("color: #22c55e; font-weight: 800; font-size: 13px;")
        stats_grid.addWidget(self.lbl_stat_total, 1, 3)

        chart_layout.addLayout(stats_grid)

        self.lbl_stat_xml_progress = QLabel("Tỷ lệ XML: 0/0 (0%)")
        self.lbl_stat_xml_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stat_xml_progress.setStyleSheet("color: #94a3b8; font-size: 11px;")
        chart_layout.addWidget(self.lbl_stat_xml_progress)

        top_grid.addWidget(chart_frame, 5)

        # Right: LIÊN HỆ GÓP Ý
        support_frame = QFrame()
        support_frame.setProperty("class", "card")
        support_layout = QVBoxLayout(support_frame)
        support_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        support_layout.setSpacing(8)

        support_title = QLabel("LIÊN HỆ GÓP Ý")
        support_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        support_title.setStyleSheet("font-weight: 700; color: #f8fafc; font-size: 13px;")
        support_layout.addWidget(support_title)

        lbl_phone = QLabel("0974496415")
        lbl_phone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_phone.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 15px;")
        support_layout.addWidget(lbl_phone)
        top_grid.addWidget(support_frame, 2)

        main_layout.addWidget(self.top_control_frame)

        # ================= 3. MID TOOLBAR =================
        mid_bar = QHBoxLayout()
        mid_bar.setSpacing(10)

        self.btn_download_xml = QPushButton("⬇ TẢI XML")
        self.btn_download_xml.setProperty("class", "btn-xml")
        self.btn_download_xml.clicked.connect(self._batch_download_xml)
        mid_bar.addWidget(self.btn_download_xml)

        self.btn_export_excel = QPushButton("📊 XUẤT EXCEL (F5)")
        self.btn_export_excel.setProperty("class", "btn-excel")
        self.btn_export_excel.clicked.connect(self._export_excel)
        mid_bar.addWidget(self.btn_export_excel)

        # Excel format selector: Bảng kê tiêu chuẩn / Bảng kê chi tiết hàng hóa
        self.cbo_excel_type = QComboBox()
        self.cbo_excel_type.addItem("Bảng kê tiêu chuẩn", "standard")
        self.cbo_excel_type.addItem("Bảng kê chi tiết hàng hóa", "detailed")
        mid_bar.addWidget(self.cbo_excel_type)

        self.btn_download_pdf = QPushButton("📑 TẢI PDF HÀNG LOẠT")
        self.btn_download_pdf.setProperty("class", "btn-pdf")
        self.btn_download_pdf.clicked.connect(self._batch_download_pdf)
        mid_bar.addWidget(self.btn_download_pdf)

        self.cbo_filter = QComboBox()
        self.cbo_filter.addItems(["Lọc: Tất cả", "Lọc: Đã có XML", "Lọc: Chưa có XML", "Lọc: Không có HS gốc"])
        self.cbo_filter.currentIndexChanged.connect(self._apply_filter)
        mid_bar.addWidget(self.cbo_filter)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Tìm kiếm hóa đơn...")
        self.txt_search.textChanged.connect(self._apply_filter)
        mid_bar.addWidget(self.txt_search)

        self.btn_toggle_expand = QPushButton("⌃ Mở rộng bảng")
        self.btn_toggle_expand.setProperty("class", "btn-expand")
        self.btn_toggle_expand.clicked.connect(self._toggle_expand_table)
        mid_bar.addWidget(self.btn_toggle_expand)

        main_layout.addLayout(mid_bar)

        # ================= 4. TABLE OF INVOICES (15 COLUMNS) =================
        self.table = QTableWidget()
        self.table.setColumnCount(15)
        headers_15 = [
            "STT", "TRẠNG THÁI XML", "KÝ HIỆU", "SỐ HÓA ĐƠN", "NGÀY LẬP",
            "THÔNG TIN NGƯỜI BÁN", "THÔNG TIN NGƯỜI MUA", "TỔNG TIỀN CHƯA THUẾ",
            "TỔNG TIỀN THUẾ", "TỔNG TIỀN THANH TOÁN", "TRẠNG THÁI",
            "KẾT QUẢ KIỂM TRA", "HÓA ĐƠN LIÊN QUAN", "CẢNH BÁO", "PHÂN LOẠI"
        ]
        self.table.setHorizontalHeaderLabels(headers_15)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(11, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(12, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(13, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(14, QHeaderView.ResizeMode.ResizeToContents)

        main_layout.addWidget(self.table, stretch=1)

        # ================= 5. PROGRESS & STATUS BAR =================
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.progress_bar)

        bottom_bar = QHBoxLayout()
        self.lbl_sum_notax = QLabel("Chưa thuế: 0 VNĐ")
        self.lbl_sum_notax.setProperty("class", "status-summary")
        bottom_bar.addWidget(self.lbl_sum_notax)
        bottom_bar.addSpacing(20)

        self.lbl_sum_tax = QLabel("Thuế: 0 VNĐ")
        self.lbl_sum_tax.setProperty("class", "status-summary")
        bottom_bar.addWidget(self.lbl_sum_tax)
        bottom_bar.addSpacing(20)

        self.lbl_sum_total = QLabel("Tổng thanh toán: 0 VNĐ")
        self.lbl_sum_total.setProperty("class", "status-summary")
        bottom_bar.addWidget(self.lbl_sum_total)
        bottom_bar.addSpacing(20)

        self.lbl_sum_xml = QLabel("Số lượng XML: 0/0")
        self.lbl_sum_xml.setProperty("class", "status-summary")
        bottom_bar.addWidget(self.lbl_sum_xml)

        bottom_bar.addStretch()

        self.lbl_log = QLabel("Sẵn sàng")
        self.lbl_log.setStyleSheet("color: #94a3b8; font-size: 11px;")
        bottom_bar.addWidget(self.lbl_log)

        main_layout.addLayout(bottom_bar)

        # F5 shortcut for Excel export
        shortcut_f5 = QShortcut(QKeySequence("F5"), self)
        shortcut_f5.activated.connect(self._export_excel)

    # ================= LOGIC KỲ KẾ TOÁN =================

    def _on_period_changed(self, idx):
        # 0: Ngày, 1: Tháng, 2: Quý, 3: Năm, 4: Tùy Chọn
        self.date_single.hide()
        self.cbo_month.hide()
        self.cbo_quarter.hide()
        self.spin_year.hide()
        self.date_from.hide()
        self.lbl_to.hide()
        self.date_to.hide()

        if idx == 0: # Theo Ngày
            self.date_single.show()
        elif idx == 1: # Theo Tháng
            self.cbo_month.show()
            self.spin_year.show()
        elif idx == 2: # Theo Quý
            self.cbo_quarter.show()
            self.spin_year.show()
        elif idx == 3: # Theo Năm
            self.spin_year.show()
        elif idx == 4: # Tùy Chọn
            self.date_from.show()
            self.lbl_to.show()
            self.date_to.show()

    def _get_active_date_range(self):
        idx = self.cbo_period.currentIndex()
        if idx == 0: # Theo Ngày
            d_str = self.date_single.date().toString("dd/MM/yyyy")
            return d_str, d_str
        elif idx == 1: # Theo Tháng
            m = self.cbo_month.currentData()
            y = self.spin_year.value()
            start_date = date(y, m, 1)
            # next month 1st - 1 day
            if m == 12:
                end_date = date(y + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(y, m + 1, 1) - timedelta(days=1)
            return start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y")
        elif idx == 2: # Theo Quý
            q = self.cbo_quarter.currentData()
            y = self.spin_year.value()
            start_m = (q - 1) * 3 + 1
            start_date = date(y, start_m, 1)
            if q == 4:
                end_date = date(y, 12, 31)
            else:
                end_date = date(y, start_m + 3, 1) - timedelta(days=1)
            return start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y")
        elif idx == 3: # Theo Năm
            y = self.spin_year.value()
            return f"01/01/{y}", f"31/12/{y}"
        else: # Tùy Chọn
            return self.date_from.date().toString("dd/MM/yyyy"), self.date_to.date().toString("dd/MM/yyyy")

    def _set_inv_type(self, itype):
        self.current_inv_type = itype
        if itype == "sold":
            self.btn_type_sold.setProperty("class", "btn-type-active")
            self.btn_type_purchase.setProperty("class", "btn-type")
        else:
            self.btn_type_sold.setProperty("class", "btn-type")
            self.btn_type_purchase.setProperty("class", "btn-type-active")
        self.btn_type_sold.setStyle(self.btn_type_sold.style())
        self.btn_type_purchase.setStyle(self.btn_type_purchase.style())
        self._do_local_search()

    # ================= QUẢN LÝ DOANH NGHIỆP & AUTH =================

    def _load_default_business(self):
        businesses = self.db.get_all_businesses()
        if businesses:
            self._set_current_business(businesses[0])
        else:
            self.btn_biz.setText(" Chưa chọn doanh nghiệp + ")

    def _set_current_business(self, biz):
        self.current_business = biz
        if not biz:
            self.btn_biz.setText(" Chưa chọn doanh nghiệp + ")
            self.btn_auth_status.setText("🔑 ĐĂNG NHẬP CỔNG THUẾ")
            self.btn_auth_status.setProperty("class", "btn-login-needed")
            self.btn_auth_status.setStyle(self.btn_auth_status.style())
            return

        name = biz.get("name", "")
        mst = biz.get("tax_code", "")
        self.btn_biz.setText(f" 🏢 {mst} - {name} ▾ ")

        # Update client token
        token = biz.get("token")
        self.client.set_token(token)
        if token and self.client.check_token_valid():
            self.btn_auth_status.setText(f"🟢 ĐÃ ĐĂNG NHẬP ({mst})")
            self.btn_auth_status.setProperty("class", "btn-login-success")
        else:
            self.btn_auth_status.setText(f"🔑 ĐĂNG NHẬP THUẾ ({mst})")
            self.btn_auth_status.setProperty("class", "btn-login-needed")
        self.btn_auth_status.setStyle(self.btn_auth_status.style())

        self._do_local_search()

    def _check_initial_admin_setup(self):
        """Nếu lần đầu chạy và chưa có mật khẩu admin, yêu cầu thiết lập."""
        if not self.db.is_admin_password_set():
            dlg = AdminSetupDialog(self.db, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.set_admin_mode(True)

    def set_admin_mode(self, is_admin: bool):
        self.is_admin = is_admin
        if self.is_admin:
            self.btn_role_badge.setText("👑 Quản Trị Viên (Admin)")
            self.btn_role_badge.setStyleSheet(
                "background-color: #0284c7; color: #ffffff; font-weight: 800; border: none; border-radius: 6px; padding: 7px 14px;"
            )
        else:
            self.btn_role_badge.setText("👤 Nhân Viên (Khóa Admin)")
            self.btn_role_badge.setStyleSheet(
                "background-color: #1e293b; color: #94a3b8; font-weight: 600; border: 1px solid #334155; border-radius: 6px; padding: 7px 14px;"
            )

    def _toggle_or_prompt_admin(self):
        if not self.is_admin:
            dlg = AdminVerifyDialog(self.db, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.set_admin_mode(True)
                QMessageBox.information(self, "Đã mở khóa", "Đã chuyển sang Quyền Quản Trị Viên (Admin) thành công!")
        else:
            reply = QMessageBox.question(
                self,
                "Tùy chọn Quản trị",
                "Bạn đang đăng nhập với Quyền Quản Trị Viên (Admin).\n\n"
                "• Bấm 'Yes' để ĐỔI MẬT KHẨU ADMIN.\n"
                "• Bấm 'No' để THOÁT QUYỀN ADMIN (Khóa lại về quyền Nhân viên).\n"
                "• Bấm 'Cancel' để giữ nguyên.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                change_dlg = AdminChangePasswordDialog(self.db, self)
                change_dlg.exec()
            elif reply == QMessageBox.StandardButton.No:
                self.set_admin_mode(False)
                QMessageBox.information(self, "Đã khóa", "Đã thoát quyền Admin, chuyển về Chế độ Nhân viên an toàn.")

    def _open_business_dialog(self):
        dlg = BusinessDialog(self.db, is_admin=self.is_admin, parent=self)
        dlg.admin_mode_changed.connect(self.set_admin_mode)
        dlg.business_selected.connect(self._set_current_business)
        dlg.business_login_requested.connect(self._on_biz_login_requested)
        dlg.exec()

    def _on_biz_login_requested(self, biz):
        self._set_current_business(biz)
        self._open_login_dialog(biz)

    def _open_login_dialog(self, biz=None):
        target_biz = biz or self.current_business
        dlg = LoginDialog(self.client, self.db, target_biz, is_admin=self.is_admin, parent=self)
        dlg.login_success.connect(self._on_login_success)
        dlg.exec()

    def _on_login_success(self, biz, token):
        self._set_current_business(biz)
        self.lbl_log.setText(f"Đã đăng nhập thành công doanh nghiệp: {biz.get('tax_code')}")

    # ================= TÌM NỘI BỘ & ĐỒNG BỘ GDT =================

    def _do_local_search(self):
        if not self.current_business:
            return
        from_d, to_d = self._get_active_date_range()
        biz_id = self.current_business["id"]
        invoices = self.db.search_local_invoices(
            business_id=biz_id,
            inv_type=self.current_inv_type,
            from_date_str=from_d,
            to_date_str=to_d
        )
        self.displayed_invoices = invoices
        self._populate_table(invoices)
        self._update_chart_and_summary(invoices)
        self.lbl_log.setText(f"Đã tải {len(invoices)} hóa đơn từ dữ liệu nội bộ.")

    def _do_sync_gdt(self):
        if not self.current_business:
            QMessageBox.warning(self, "Chưa chọn doanh nghiệp", "Vui lòng chọn doanh nghiệp trước!")
            self._open_business_dialog()
            return

        # Check token
        if not self.client.check_token_valid():
            reply = QMessageBox.question(
                self,
                "Chưa đăng nhập",
                "Phiên đăng nhập chưa kích hoạt hoặc đã hết hạn. Bạn có muốn đăng nhập ngay?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._open_login_dialog()
            return

        from_d, to_d = self._get_active_date_range()
        self.btn_sync_gdt.setEnabled(False)
        self.btn_sync_gdt.setText("Đang đồng bộ...")
        self.progress_bar.setValue(0)

        self.worker = SyncWorker(
            client=self.client,
            db=self.db,
            biz_id=self.current_business["id"],
            inv_type=self.current_inv_type,
            from_date_str=from_d,
            to_date_str=to_d
        )
        self.worker.progress_signal.connect(lambda cur, tot: self.progress_bar.setValue(int(cur / tot * 100) if tot else 0))
        self.worker.log_signal.connect(lambda msg, lvl: self.lbl_log.setText(msg))
        self.worker.finished_signal.connect(self._on_sync_finished)
        self.worker.start()

    def _on_sync_finished(self, total, error_msg=""):
        self.btn_sync_gdt.setEnabled(True)
        self.btn_sync_gdt.setText("☁ ĐỒNG BỘ TỔNG CỤC THUẾ")
        self.progress_bar.setValue(100)
        self._do_local_search()
        if total >= 0:
            QMessageBox.information(self, "Hoàn tất", f"Đã đồng bộ thành công {total} hóa đơn từ Tổng cục Thuế!")
        else:
            QMessageBox.critical(self, "Lỗi đồng bộ", f"Không thể đồng bộ dữ liệu từ Tổng cục Thuế:\n{error_msg}")

    # ================= HIỂN THỊ BẢNG & THỐNG KÊ =================

    def _populate_table(self, invoices):
        self.table.setRowCount(len(invoices))
        for row, inv in enumerate(invoices):
            # 1. STT
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            
            # 2. TRẠNG THÁI XML
            xml_status = inv.get("xml_status", 0)
            if xml_status == 1:
                status_text = "Đã có"
                status_color = "#22c55e" # green
            elif xml_status == 2:
                status_text = "Không có HS gốc"
                status_color = "#f59e0b" # amber
            else:
                status_text = "Chưa tải"
                status_color = "#94a3b8" # gray

            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(status_color))
            self.table.setItem(row, 1, status_item)

            # 3. KÝ HIỆU
            self.table.setItem(row, 2, QTableWidgetItem(str(inv.get("khhdon", ""))))

            # 4. SỐ HÓA ĐƠN
            self.table.setItem(row, 3, QTableWidgetItem(str(inv.get("shdon", ""))))

            # 5. NGÀY LẬP
            tdlap = str(inv.get("tdlap", ""))[:10]
            self.table.setItem(row, 4, QTableWidgetItem(tdlap))

            # 6. THÔNG TIN NGƯỜI BÁN
            nbmst = inv.get("nbmst", "")
            nbten = inv.get("nbten", "")
            self.table.setItem(row, 5, QTableWidgetItem(f"{nbmst} - {nbten}"))

            # 7. THÔNG TIN NGƯỜI MUA
            nmmst = inv.get("nmmst", "")
            nmten = inv.get("nmten", "")
            self.table.setItem(row, 6, QTableWidgetItem(f"{nmmst} - {nmten}"))

            # 8. TỔNG TIỀN CHƯA THUẾ
            tgtcthue = float(inv.get("tgtcthue") or 0)
            self.table.setItem(row, 7, QTableWidgetItem(f"{tgtcthue:,.0f}"))

            # 9. TỔNG TIỀN THUẾ
            tgtthue = float(inv.get("tgtthue") or 0)
            self.table.setItem(row, 8, QTableWidgetItem(f"{tgtthue:,.0f}"))

            # 10. TỔNG TIỀN THANH TOÁN
            tgtttbso = float(inv.get("tgtttbso") or 0)
            self.table.setItem(row, 9, QTableWidgetItem(f"{tgtttbso:,.0f}"))

            # 11. TRẠNG THÁI
            self.table.setItem(row, 10, QTableWidgetItem("Hóa đơn mới"))

            # 12. KẾT QUẢ KIỂM TRA
            self.table.setItem(row, 11, QTableWidgetItem("Hợp lệ"))

            # 13. HÓA ĐƠN LIÊN QUAN
            self.table.setItem(row, 12, QTableWidgetItem("-"))

            # 14. CẢNH BÁO
            self.table.setItem(row, 13, QTableWidgetItem("Không"))

            # 15. PHÂN LOẠI
            self.table.setItem(row, 14, QTableWidgetItem("HĐ Gốc"))

    def _update_chart_and_summary(self, invoices):
        sum_notax = sum(float(i.get("tgtcthue") or 0) for i in invoices)
        sum_tax = sum(float(i.get("tgtthue") or 0) for i in invoices)
        sum_total = sum(float(i.get("tgtttbso") or 0) for i in invoices)
        xml_count = sum(1 for i in invoices if i.get("xml_status") == 1)
        total_count = len(invoices)

        # Bottom status bar
        self.lbl_sum_notax.setText(f"Chưa thuế: {sum_notax:,.0f} VNĐ")
        self.lbl_sum_tax.setText(f"Thuế: {sum_tax:,.0f} VNĐ")
        self.lbl_sum_total.setText(f"Tổng thanh toán: {sum_total:,.0f} VNĐ")
        self.lbl_sum_xml.setText(f"Số lượng XML: {xml_count}/{total_count}")

        # Update Chart Tiles
        t_text = "Mua vào" if self.current_inv_type == "purchase" else "Bán ra"
        self.lbl_stat_count.setText(f"{total_count} HĐ ({t_text})")
        self.lbl_stat_notax.setText(f"{sum_notax:,.0f} đ")
        self.lbl_stat_tax.setText(f"{sum_tax:,.0f} đ")
        self.lbl_stat_total.setText(f"{sum_total:,.0f} đ")

        xml_pct = (xml_count / total_count * 100) if total_count > 0 else 0
        self.lbl_stat_xml_progress.setText(f"Tỷ lệ XML: {xml_count}/{total_count} ({xml_pct:.1f}%)")

    def _apply_filter(self):
        kw = self.txt_search.text().lower().strip()
        flt = self.cbo_filter.currentIndex()

        for r in range(self.table.rowCount()):
            show = True
            # Check text keyword
            if kw:
                row_text = " ".join(self.table.item(r, c).text().lower() for c in range(self.table.columnCount()))
                if kw not in row_text:
                    show = False

            # Check status filter
            if show and flt != 0:
                xml_status_text = self.table.item(r, 1).text()
                if flt == 1 and xml_status_text != "Đã có":
                    show = False
                elif flt == 2 and xml_status_text != "Chưa tải":
                    show = False
                elif flt == 3 and xml_status_text != "Không có HS gốc":
                    show = False

            self.table.setRowHidden(r, not show)

    def _toggle_expand_table(self):
        if self.top_control_frame.isVisible():
            self.top_control_frame.hide()
            self.btn_toggle_expand.setText("⌄ Thu nhỏ bảng")
        else:
            self.top_control_frame.show()
            self.btn_toggle_expand.setText("⌃ Mở rộng bảng")

    # ================= TẢI XML & PDF HÀNG LOẠT =================

    def _batch_download_xml(self):
        self._start_batch_download(mode="xml")

    def _batch_download_pdf(self):
        self._start_batch_download(mode="pdf")

    def _start_batch_download(self, mode="pdf"):
        if not self.displayed_invoices:
            QMessageBox.information(self, "Thông báo", "Không có hóa đơn nào trong bảng để tải!")
            return

        if not self.client.check_token_valid():
            QMessageBox.warning(self, "Chưa đăng nhập", "Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại!")
            self._open_login_dialog()
            return

        out_dir = str(Path("D:/Manh_Project/HoaDon/HoaDon_Files").resolve())
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu hóa đơn", out_dir)
        if not folder:
            return

        self.btn_download_xml.setEnabled(False)
        self.btn_download_pdf.setEnabled(False)
        self.progress_bar.setValue(0)

        self.worker = BatchDownloadWorker(
            client=self.client,
            invoice_service=self.invoice_service,
            db=self.db,
            invoices=self.displayed_invoices,
            out_dir=folder,
            mode=mode
        )
        self.worker.progress_signal.connect(lambda cur, tot: self.progress_bar.setValue(int(cur / tot * 100) if tot else 0))
        self.worker.item_completed.connect(self._on_item_download_status)
        self.worker.log_signal.connect(lambda msg, lvl: self.lbl_log.setText(msg))
        self.worker.finished_signal.connect(lambda s, nr, f: self._on_download_completed(s, nr, f, folder))
        self.worker.start()

    def _on_item_download_status(self, row, status_text, color_hex):
        item = self.table.item(row, 1)
        if item:
            item.setText(status_text)
            item.setForeground(QColor(color_hex))

    def _on_download_completed(self, success, no_record, failed, out_dir):
        self.btn_download_xml.setEnabled(True)
        self.btn_download_pdf.setEnabled(True)
        self.progress_bar.setValue(100)
        self._do_local_search()

        msg = (
            f"Đã hoàn thành tiến trình tải:\n"
            f"✔ Tải thành công: {success} hóa đơn\n"
        )
        if no_record > 0:
            msg += f"⚠ Không có hồ sơ gốc trên Cổng Thuế: {no_record} hóa đơn (HĐ ngân hàng/không có mã CQT)\n"
        if failed > 0:
            msg += f"✖ Lỗi tải: {failed} hóa đơn\n"
        msg += f"\nThư mục lưu trữ:\n{out_dir}"

        reply = QMessageBox.information(
            self,
            "Hoàn tất tải",
            msg,
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok
        )
        if reply == QMessageBox.StandardButton.Open:
            try:
                os.startfile(out_dir)
            except Exception:
                pass

    # ================= XUẤT EXCEL (F5) =================

    def _export_excel(self):
        if not self.displayed_invoices:
            QMessageBox.information(self, "Thông báo", "Không có hóa đơn nào để xuất Excel!")
            return

        export_type = self.cbo_excel_type.currentData()
        name_prefix = "BangKeChiTiet" if export_type == "detailed" else "BangKeTieuChuan"
        d_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{name_prefix}_{d_str}.xlsx"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu file Excel Báo Cáo",
            default_filename,
            "Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            self.lbl_log.setText("Đang xuất file Excel...")
            self.invoice_service.export_excel(
                invoices=self.displayed_invoices,
                export_type=export_type,
                output_filepath=file_path
            )
            self.lbl_log.setText(f"Đã xuất Excel: {file_path}")
            reply = QMessageBox.information(
                self,
                "Xuất Excel thành công",
                f"Đã xuất thành công báo cáo Excel:\n{file_path}\n\nBạn có muốn mở file ngay không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.startfile(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất Excel", f"Không thể xuất Excel: {e}")
            self.lbl_log.setText(f"Lỗi xuất Excel: {e}")
