import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

STYLESHEET_ADMIN = """
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
    font-size: 16px;
    font-weight: 800;
    color: #38bdf8;
    margin-bottom: 2px;
}
QLabel.subtitle {
    font-size: 12px;
    color: #94a3b8;
    margin-bottom: 12px;
}
QLineEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 9px 12px;
    color: #f8fafc;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #38bdf8;
    background-color: #0f172a;
}
QPushButton {
    border: none;
    border-radius: 6px;
    padding: 10px 18px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton.btn-confirm {
    background-color: #0284c7;
    color: white;
}
QPushButton.btn-confirm:hover {
    background-color: #0369a1;
}
QPushButton.btn-cancel {
    background-color: #334155;
    color: #f8fafc;
}
QPushButton.btn-cancel:hover {
    background-color: #475569;
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
"""

def _set_icon(dialog: QDialog):
    icon_path = (Path(sys.executable).resolve().parent / "assets" / "logo.ico") if getattr(sys, 'frozen', False) else (Path(__file__).resolve().parent.parent.parent / "assets" / "logo.ico")
    if icon_path.exists():
        dialog.setWindowIcon(QIcon(str(icon_path)))

class AdminSetupDialog(QDialog):
    """Hộp thoại thiết lập Mật khẩu Admin lần đầu tiên."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Thiết lập Mật khẩu Quản trị viên (Admin)")
        _set_icon(self)
        self.setFixedWidth(440)
        self.setStyleSheet(STYLESHEET_ADMIN)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("👑 THIẾT LẬP MẬT KHẨU ADMIN")
        title.setProperty("class", "title")
        subtitle = QLabel(
            "Vui lòng đặt mật khẩu Admin để bảo vệ hệ thống. "
            "Chỉ người có mật khẩu này mới có quyền Thêm / Sửa / Xóa doanh nghiệp."
        )
        subtitle.setWordWrap(True)
        subtitle.setProperty("class", "subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addWidget(QLabel("Mật khẩu Quản trị mới:"))
        self.txt_pwd = QLineEdit()
        self.txt_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pwd.setPlaceholderText("Nhập mật khẩu Admin...")
        layout.addWidget(self.txt_pwd)

        layout.addWidget(QLabel("Xác nhận lại mật khẩu:"))
        self.txt_pwd_confirm = QLineEdit()
        self.txt_pwd_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pwd_confirm.setPlaceholderText("Nhập lại mật khẩu...")
        layout.addWidget(self.txt_pwd_confirm)

        layout.addSpacing(10)
        btn_row = QHBoxLayout()
        self.btn_submit = QPushButton("Xác nhận & Kích hoạt Admin")
        self.btn_submit.setProperty("class", "btn-confirm")
        self.btn_submit.clicked.connect(self._do_setup)
        btn_row.addWidget(self.btn_submit)

        layout.addLayout(btn_row)

    def _do_setup(self):
        pwd = self.txt_pwd.text().strip()
        pwd2 = self.txt_pwd_confirm.text().strip()

        if not pwd:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập mật khẩu Admin!")
            self.txt_pwd.setFocus()
            return

        if len(pwd) < 4:
            QMessageBox.warning(self, "Lỗi", "Mật khẩu Admin phải có ít nhất 4 ký tự!")
            self.txt_pwd.setFocus()
            return

        if pwd != pwd2:
            QMessageBox.warning(self, "Lỗi", "Hai mật khẩu không khớp nhau!")
            self.txt_pwd_confirm.setFocus()
            return

        self.db.set_admin_password(pwd)
        QMessageBox.information(
            self,
            "Thành công",
            "Đã thiết lập Mật khẩu Quản trị (Admin) thành công!\n"
            "Bạn đang ở quyền Quản trị viên và có thể bắt đầu thêm doanh nghiệp."
        )
        self.accept()


class AdminVerifyDialog(QDialog):
    """Hộp thoại xác thực Mật khẩu Admin để mở khóa."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Xác thực Quyền Quản trị viên (Admin)")
        _set_icon(self)
        self.setFixedWidth(420)
        self.setStyleSheet(STYLESHEET_ADMIN)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("🔐 MỞ KHÓA QUYỀN ADMIN")
        title.setProperty("class", "title")
        subtitle = QLabel("Vui lòng nhập Mật khẩu Quản trị để quản lý doanh nghiệp.")
        subtitle.setWordWrap(True)
        subtitle.setProperty("class", "subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addWidget(QLabel("Mật khẩu Quản trị (Admin):"))
        self.txt_pwd = QLineEdit()
        self.txt_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pwd.setPlaceholderText("Nhập mật khẩu Admin...")
        self.txt_pwd.returnPressed.connect(self._do_verify)
        layout.addWidget(self.txt_pwd)

        layout.addSpacing(8)
        btn_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Hủy bỏ")
        self.btn_cancel.setProperty("class", "btn-cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_submit = QPushButton("Mở khóa Admin")
        self.btn_submit.setProperty("class", "btn-confirm")
        self.btn_submit.clicked.connect(self._do_verify)
        btn_row.addWidget(self.btn_submit)

        layout.addLayout(btn_row)
        self.txt_pwd.setFocus()

    def _do_verify(self):
        pwd = self.txt_pwd.text().strip()
        if not pwd:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập mật khẩu Admin!")
            return

        if self.db.verify_admin_password(pwd):
            self.accept()
        else:
            QMessageBox.critical(self, "Thất bại", "Mật khẩu Admin không chính xác!")
            self.txt_pwd.selectAll()
            self.txt_pwd.setFocus()


class AdminChangePasswordDialog(QDialog):
    """Hộp thoại đổi Mật khẩu Admin."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Đổi Mật khẩu Quản trị viên (Admin)")
        _set_icon(self)
        self.setFixedWidth(420)
        self.setStyleSheet(STYLESHEET_ADMIN)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("🔑 ĐỔI MẬT KHẨU ADMIN")
        title.setProperty("class", "title")
        subtitle = QLabel("Nhập mật khẩu Admin hiện tại và thiết lập mật khẩu mới.")
        subtitle.setProperty("class", "subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addWidget(QLabel("Mật khẩu Admin hiện tại:"))
        self.txt_old_pwd = QLineEdit()
        self.txt_old_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.txt_old_pwd)

        layout.addWidget(QLabel("Mật khẩu Admin mới:"))
        self.txt_new_pwd = QLineEdit()
        self.txt_new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.txt_new_pwd)

        layout.addWidget(QLabel("Xác nhận lại mật khẩu mới:"))
        self.txt_confirm_pwd = QLineEdit()
        self.txt_confirm_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.txt_confirm_pwd)

        layout.addSpacing(8)
        btn_row = QHBoxLayout()
        self.btn_cancel = QPushButton("Hủy bỏ")
        self.btn_cancel.setProperty("class", "btn-cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_submit = QPushButton("Lưu mật khẩu mới")
        self.btn_submit.setProperty("class", "btn-confirm")
        self.btn_submit.clicked.connect(self._do_change)
        btn_row.addWidget(self.btn_submit)

        layout.addLayout(btn_row)

    def _do_change(self):
        old_pwd = self.txt_old_pwd.text().strip()
        new_pwd = self.txt_new_pwd.text().strip()
        confirm_pwd = self.txt_confirm_pwd.text().strip()

        if not self.db.verify_admin_password(old_pwd):
            QMessageBox.critical(self, "Lỗi", "Mật khẩu Admin hiện tại không đúng!")
            self.txt_old_pwd.selectAll()
            self.txt_old_pwd.setFocus()
            return

        if len(new_pwd) < 4:
            QMessageBox.warning(self, "Lỗi", "Mật khẩu Admin mới phải có ít nhất 4 ký tự!")
            self.txt_new_pwd.setFocus()
            return

        if new_pwd != confirm_pwd:
            QMessageBox.warning(self, "Lỗi", "Mật khẩu xác nhận không khớp!")
            self.txt_confirm_pwd.setFocus()
            return

        self.db.set_admin_password(new_pwd)
        QMessageBox.information(self, "Thành công", "Đã cập nhật Mật khẩu Admin mới thành công!")
        self.accept()
