import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFrame, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray
from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon
from PyQt6.QtSvg import QSvgRenderer

logger = logging.getLogger("LoginDialog")

STYLESHEET_LOGIN = """
QDialog {
    background-color: #0b1120;
    color: #f8fafc;
    font-family: 'Segoe UI', Tahoma, sans-serif;
    font-size: 13px;
}
QLabel {
    color: #e2e8f0;
    font-size: 13px;
}
QLabel.title {
    font-size: 17px;
    font-weight: 800;
    color: #38bdf8;
    margin-bottom: 2px;
}
QLabel.subtitle {
    font-size: 11px;
    color: #94a3b8;
    margin-bottom: 10px;
}
QLabel.emp-badge {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #fbbf24;
    font-size: 12px;
    font-weight: 600;
}
QComboBox, QLineEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 12px;
    color: #f8fafc;
    font-size: 13px;
}
QComboBox:focus, QLineEdit:focus {
    border: 1px solid #38bdf8;
    background-color: #0f172a;
}
QLineEdit:read-only {
    background-color: #182234;
    color: #94a3b8;
    border: 1px solid #293548;
}
QComboBox QAbstractItemView {
    background-color: #1e293b;
    selection-background-color: #0284c7;
    color: #f8fafc;
    border: 1px solid #334155;
}
QPushButton.btn-login {
    background-color: #10b981;
    color: white;
    font-size: 14px;
    font-weight: 800;
    padding: 12px;
    border-radius: 8px;
    border: none;
}
QPushButton.btn-login:hover {
    background-color: #059669;
}
QPushButton.btn-login:disabled {
    background-color: #334155;
    color: #64748b;
}
QPushButton.btn-refresh {
    background-color: #1e293b;
    border: 1px solid #334155;
    color: #e2e8f0;
    border-radius: 6px;
    font-weight: 600;
    padding: 8px 14px;
}
QPushButton.btn-refresh:hover {
    background-color: #334155;
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

class LoginDialog(QDialog):
    login_success = pyqtSignal(dict, str) # business_dict, token

    def __init__(self, client, db, initial_business=None, is_admin=False, parent=None):
        super().__init__(parent)
        self.client = client
        self.db = db
        self.initial_business = initial_business
        self.current_business = initial_business
        self.is_admin = is_admin
        self.current_ckey = None

        self.setWindowTitle("Đăng Nhập Cổng Hóa Đơn Điện Tử - Tổng Cục Thuế")
        icon_path = (Path(sys.executable).resolve().parent / "assets" / "logo.ico") if getattr(sys, 'frozen', False) else (Path(__file__).resolve().parent.parent.parent / "assets" / "logo.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setFixedSize(480, 580)
        self.setStyleSheet(STYLESHEET_LOGIN)

        self._setup_ui()
        self._load_saved_businesses()
        self._load_captcha()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("🔑 ĐĂNG NHẬP TỔNG CỤC THUẾ")
        title.setProperty("class", "title")
        subtitle = QLabel("Xác thực bảo mật để lưu phiên làm việc (JWT) & tra cứu hóa đơn không lo hết hạn captcha")
        subtitle.setWordWrap(True)
        subtitle.setProperty("class", "subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        if not self.is_admin:
            lbl_notice = QLabel("🔒 Chế độ Nhân viên: Mật khẩu thuế được bảo vệ tự động điền. Chỉ cần chọn công ty & nhập Captcha.")
            lbl_notice.setWordWrap(True)
            lbl_notice.setProperty("class", "emp-badge")
            layout.addWidget(lbl_notice)

        # Quick company selector
        layout.addWidget(QLabel("Chọn doanh nghiệp:"))
        self.cbo_biz = QComboBox()
        self.cbo_biz.currentIndexChanged.connect(self._on_business_combo_changed)
        layout.addWidget(self.cbo_biz)

        # MST
        layout.addWidget(QLabel("Mã số thuế (Tài khoản GDT):"))
        self.txt_mst = QLineEdit()
        self.txt_mst.setPlaceholderText("Mã số thuế...")
        layout.addWidget(self.txt_mst)

        # Tên doanh nghiệp
        layout.addWidget(QLabel("Tên doanh nghiệp:"))
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Tên doanh nghiệp...")
        layout.addWidget(self.txt_name)

        # Mật khẩu
        layout.addWidget(QLabel("Mật khẩu trang https://hoadondientu.gdt.gov.vn:"))
        self.txt_pwd = QLineEdit()
        self.txt_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pwd.setPlaceholderText("Mật khẩu Cổng Thuế...")
        layout.addWidget(self.txt_pwd)

        # Captcha
        layout.addWidget(QLabel("Mã kiểm tra (Captcha từ Tổng Cục Thuế):"))
        captcha_row = QHBoxLayout()
        self.lbl_captcha = QLabel()
        self.lbl_captcha.setFixedSize(180, 44)
        self.lbl_captcha.setStyleSheet("background-color: white; border: 1px solid #334155; border-radius: 6px;")
        self.lbl_captcha.setAlignment(Qt.AlignmentFlag.AlignCenter)
        captcha_row.addWidget(self.lbl_captcha)

        self.btn_refresh = QPushButton("🔄 Đổi mã")
        self.btn_refresh.setProperty("class", "btn-refresh")
        self.btn_refresh.clicked.connect(self._load_captcha)
        captcha_row.addWidget(self.btn_refresh)
        layout.addLayout(captcha_row)

        self.txt_captcha = QLineEdit()
        self.txt_captcha.setPlaceholderText("Nhập mã chữ/số hiển thị phía trên...")
        layout.addWidget(self.txt_captcha)

        self.chk_save = QCheckBox("Tự động lưu thông tin doanh nghiệp vào hệ thống")
        self.chk_save.setChecked(True)
        if not self.is_admin:
            self.chk_save.setVisible(False)
        layout.addWidget(self.chk_save)

        layout.addSpacing(6)
        self.btn_submit = QPushButton("🚀 ĐĂNG NHẬP & LƯU PHIÊN LÀM VIỆC")
        self.btn_submit.setProperty("class", "btn-login")
        self.btn_submit.clicked.connect(self._do_login)
        layout.addWidget(self.btn_submit)

        layout.addStretch()

    def _load_saved_businesses(self):
        self.cbo_biz.blockSignals(True)
        self.cbo_biz.clear()
        
        businesses = self.db.get_all_businesses()
        selected_index = 0

        for idx, biz in enumerate(businesses):
            display_text = f"🏢 {biz.get('tax_code')} - {biz.get('name')}"
            self.cbo_biz.addItem(display_text, biz)
            if self.current_business and biz.get("id") == self.current_business.get("id"):
                selected_index = idx

        if self.is_admin:
            # Only admin can choose to add new
            self.cbo_biz.addItem("➕ [Thêm mới / Nhập tài khoản khác]", None)

        if businesses:
            self.cbo_biz.setCurrentIndex(selected_index)
            self._fill_business_fields(businesses[selected_index])
            self.btn_submit.setEnabled(True)
        else:
            if not self.is_admin:
                self.cbo_biz.addItem("⚠️ Chưa có doanh nghiệp nào được cấu hình", None)
                self.btn_submit.setEnabled(False)
            self.cbo_biz.setCurrentIndex(0)
            self._fill_business_fields(None)

        self.cbo_biz.blockSignals(False)

    def _on_business_combo_changed(self, idx):
        biz = self.cbo_biz.currentData()
        self._fill_business_fields(biz)

    def _fill_business_fields(self, biz):
        if biz:
            self.current_business = biz
            self.txt_mst.setText(biz.get("tax_code", ""))
            self.txt_name.setText(biz.get("name", ""))
            self.txt_pwd.setText(biz.get("password", ""))
            if not self.is_admin:
                self.txt_mst.setReadOnly(True)
                self.txt_name.setReadOnly(True)
                self.txt_pwd.setReadOnly(True)
            else:
                self.txt_mst.setReadOnly(False)
                self.txt_name.setReadOnly(False)
                self.txt_pwd.setReadOnly(False)
        else:
            self.current_business = None
            self.txt_mst.clear()
            self.txt_name.clear()
            self.txt_pwd.clear()
            if not self.is_admin:
                self.txt_mst.setReadOnly(True)
                self.txt_name.setReadOnly(True)
                self.txt_pwd.setReadOnly(True)
            else:
                self.txt_mst.setReadOnly(False)
                self.txt_name.setReadOnly(False)
                self.txt_pwd.setReadOnly(False)
                self.txt_mst.setFocus()

    def _load_captcha(self):
        try:
            ckey, svg = self.client.get_captcha()
            self.current_ckey = ckey

            renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
            size = renderer.defaultSize()
            pixmap = QPixmap(size.width(), size.height())
            pixmap.fill(QColor("white"))
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()

            scaled = pixmap.scaled(
                self.lbl_captcha.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_captcha.setPixmap(scaled)
            self.txt_captcha.clear()
            self.txt_captcha.setFocus()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối Cổng Thuế", f"Không thể lấy mã captcha từ Tổng Cục Thuế:\n{e}")

    def _do_login(self):
        mst = self.txt_mst.text().strip()
        name = self.txt_name.text().strip()
        pwd = self.txt_pwd.text().strip()
        cval = self.txt_captcha.text().strip()

        if not mst or not pwd:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn doanh nghiệp có đầy đủ Mã số thuế và Mật khẩu!")
            return

        if not cval:
            QMessageBox.warning(self, "Thiếu Captcha", "Vui lòng nhập mã kiểm tra Captcha!")
            self.txt_captcha.setFocus()
            return

        if not name:
            name = f"Doanh nghiệp {mst}"

        self.btn_submit.setEnabled(False)
        self.btn_submit.setText("⏳ Đang xác thực với Cổng Thuế...")

        try:
            token = self.client.login(mst, pwd, cval, self.current_ckey)

            if self.is_admin:
                saved_biz = self.db.save_business(mst, name, pwd)
                self.db.update_business_token(saved_biz["id"], token)
                saved_biz["token"] = token
            else:
                if self.current_business:
                    self.db.update_business_token(self.current_business["id"], token)
                    self.current_business["token"] = token
                    saved_biz = self.current_business
                else:
                    saved_biz = {"tax_code": mst, "name": name, "token": token}

            QMessageBox.information(
                self,
                "Đăng nhập thành công",
                f"Đã đăng nhập thành công doanh nghiệp:\n{name} ({mst})\n\n"
                f"Phiên làm việc đã được lưu vào hệ thống. Bạn có thể tra cứu và tải hóa đơn mà không lo hết hạn captcha!"
            )
            self.login_success.emit(saved_biz, token)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Đăng nhập thất bại", str(e))
            self._load_captcha()
            self.btn_submit.setEnabled(True)
            self.btn_submit.setText("🚀 ĐĂNG NHẬP & LƯU PHIÊN LÀM VIỆC")
