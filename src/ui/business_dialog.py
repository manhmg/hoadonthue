import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from src.ui.admin_dialog import AdminVerifyDialog, AdminChangePasswordDialog

STYLESHEET_BIZ = """
QDialog {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: 'Segoe UI', Tahoma, sans-serif;
    font-size: 13px;
}
QLabel {
    color: #e2e8f0;
    font-size: 13px;
}
QLabel.section-title {
    font-size: 15px;
    font-weight: 700;
    color: #94a3b8;
    margin-bottom: 8px;
}
QLabel.admin-banner {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 12px;
    font-weight: 700;
}
QLabel.emp-notice {
    color: #fbbf24;
    background-color: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 6px;
    padding: 10px;
    font-size: 12px;
}
QLineEdit {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 10px;
    color: #f8fafc;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #38bdf8;
    background-color: #0f172a;
}
QLineEdit:read-only {
    background-color: #182234;
    color: #94a3b8;
    border: 1px solid #293548;
}
QListWidget {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #f8fafc;
    padding: 4px;
}
QListWidget::item {
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 4px;
}
QListWidget::item:selected {
    background-color: #0284c7;
    color: white;
    font-weight: 700;
}
QListWidget::item:hover {
    background-color: #334155;
}
QPushButton {
    border: none;
    border-radius: 6px;
    padding: 9px 16px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton.btn-save {
    background-color: #10b981;
    color: white;
}
QPushButton.btn-save:hover {
    background-color: #059669;
}
QPushButton.btn-delete {
    background-color: #f87171;
    color: white;
}
QPushButton.btn-delete:hover {
    background-color: #ef4444;
}
QPushButton.btn-clear {
    background-color: #334155;
    color: #f8fafc;
}
QPushButton.btn-clear:hover {
    background-color: #475569;
}
QPushButton.btn-select {
    background-color: #334155;
    color: #f8fafc;
    padding: 11px;
    font-size: 13px;
}
QPushButton.btn-select:hover {
    background-color: #0284c7;
    color: white;
}
QPushButton.btn-admin-unlock {
    background-color: #f59e0b;
    color: #0f172a;
    font-weight: 800;
    padding: 7px 14px;
}
QPushButton.btn-admin-unlock:hover {
    background-color: #d97706;
}
QPushButton.btn-admin-sub {
    background-color: #334155;
    color: #e2e8f0;
    font-size: 12px;
    padding: 6px 12px;
}
QPushButton.btn-admin-sub:hover {
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

class BusinessDialog(QDialog):
    business_selected = pyqtSignal(dict)
    business_login_requested = pyqtSignal(dict)
    admin_mode_changed = pyqtSignal(bool)

    def __init__(self, db, is_admin=False, parent=None):
        super().__init__(parent)
        self.db = db
        self.is_admin = is_admin
        self.setWindowTitle("Quản lý Thông Tin Doanh Nghiệp v1.0")
        icon_path = (Path(sys.executable).resolve().parent / "assets" / "logo.ico") if getattr(sys, 'frozen', False) else (Path(__file__).resolve().parent.parent.parent / "assets" / "logo.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(800, 520)
        self.setStyleSheet(STYLESHEET_BIZ)
        self.current_biz_id = None

        self._setup_ui()
        self._load_businesses()
        self._update_admin_ui_state()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 14, 16, 14)
        root_layout.setSpacing(12)

        # ================= TOP ADMIN / ROLE BAR =================
        self.role_bar = QHBoxLayout()
        self.lbl_role = QLabel()
        self.lbl_role.setProperty("class", "admin-banner")
        self.role_bar.addWidget(self.lbl_role)

        self.role_bar.addStretch()

        self.btn_unlock_admin = QPushButton("🔐 Mở khóa Quyền Quản Trị (Admin)")
        self.btn_unlock_admin.setProperty("class", "btn-admin-unlock")
        self.btn_unlock_admin.clicked.connect(self._unlock_admin)
        self.role_bar.addWidget(self.btn_unlock_admin)

        self.btn_change_pwd = QPushButton("🔑 Đổi MK Admin")
        self.btn_change_pwd.setProperty("class", "btn-admin-sub")
        self.btn_change_pwd.clicked.connect(self._change_admin_pwd)
        self.role_bar.addWidget(self.btn_change_pwd)

        self.btn_lock_admin = QPushButton("🔒 Khóa lại (Về quyền nhân viên)")
        self.btn_lock_admin.setProperty("class", "btn-admin-sub")
        self.btn_lock_admin.clicked.connect(self._lock_admin)
        self.role_bar.addWidget(self.btn_lock_admin)

        root_layout.addLayout(self.role_bar)

        # ================= MAIN BODY (SPLIT LEFT / RIGHT) =================
        main_layout = QHBoxLayout()
        main_layout.setSpacing(16)

        # ---------------- LEFT: Danh sách doanh nghiệp ----------------
        left_box = QVBoxLayout()
        left_title = QLabel("Danh Sách Doanh Nghiệp Cấu Hình")
        left_title.setProperty("class", "section-title")
        left_box.addWidget(left_title)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        left_box.addWidget(self.list_widget)

        sel_row = QHBoxLayout()
        self.btn_select_this = QPushButton("Chọn doanh nghiệp")
        self.btn_select_this.setProperty("class", "btn-select")
        self.btn_select_this.clicked.connect(self._select_current_business)
        sel_row.addWidget(self.btn_select_this)

        self.btn_login_this = QPushButton("🔑 Đăng nhập thuế")
        self.btn_login_this.setProperty("class", "btn-save")
        self.btn_login_this.clicked.connect(self._login_current_business)
        sel_row.addWidget(self.btn_login_this)
        left_box.addLayout(sel_row)

        # ---------------- RIGHT: Form thông tin ----------------
        right_box = QVBoxLayout()
        right_box.setSpacing(10)

        self.right_title = QLabel("Thông Tin Chi Tiết")
        self.right_title.setProperty("class", "section-title")
        right_box.addWidget(self.right_title)

        # Notice for employee
        self.lbl_emp_notice = QLabel(
            "🔒 Chế độ Nhân viên: Mật khẩu thuế được bảo mật và tự động điền. "
            "Để Thêm / Sửa / Xóa doanh nghiệp, vui lòng bấm nút 'Mở khóa Quyền Quản Trị (Admin)' phía trên."
        )
        self.lbl_emp_notice.setWordWrap(True)
        self.lbl_emp_notice.setProperty("class", "emp-notice")
        right_box.addWidget(self.lbl_emp_notice)

        right_box.addWidget(QLabel("Mã số thuế (MST):"))
        self.txt_mst = QLineEdit()
        self.txt_mst.setPlaceholderText("Ví dụ: 0111170818")
        right_box.addWidget(self.txt_mst)

        right_box.addWidget(QLabel("Tên doanh nghiệp:"))
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Ví dụ: CÔNG TY TNHH KAOPIZ SOFTWARE")
        right_box.addWidget(self.txt_name)

        right_box.addWidget(QLabel("Mật khẩu trang https://hoadondientu.gdt.gov.vn:"))
        self.txt_pwd = QLineEdit()
        self.txt_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pwd.setPlaceholderText("Mật khẩu Cổng Thuế...")
        right_box.addWidget(self.txt_pwd)

        # Action Buttons (Admin only)
        self.btn_row_widget = QWidget()
        btn_row = QHBoxLayout(self.btn_row_widget)
        btn_row.setContentsMargins(0, 4, 0, 0)
        btn_row.setSpacing(10)

        self.btn_save = QPushButton("💾 Lưu / Cập nhật")
        self.btn_save.setProperty("class", "btn-save")
        self.btn_save.clicked.connect(self._save_business)
        btn_row.addWidget(self.btn_save)

        self.btn_delete = QPushButton("🗑️ Xóa")
        self.btn_delete.setProperty("class", "btn-delete")
        self.btn_delete.clicked.connect(self._delete_business)
        btn_row.addWidget(self.btn_delete)

        self.btn_clear = QPushButton("➕ Thêm mới")
        self.btn_clear.setProperty("class", "btn-clear")
        self.btn_clear.clicked.connect(self._clear_form)
        btn_row.addWidget(self.btn_clear)

        right_box.addWidget(self.btn_row_widget)
        right_box.addStretch()

        # Divider line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #334155;")

        main_layout.addLayout(left_box, 4)
        main_layout.addWidget(line)
        main_layout.addLayout(right_box, 6)

        root_layout.addLayout(main_layout)

    def _update_admin_ui_state(self):
        """Cập nhật giao diện phụ thuộc vào quyền Admin hay Nhân viên."""
        if self.is_admin:
            self.lbl_role.setText("👑 QUYỀN QUẢN TRỊ VIÊN (ADMIN)")
            self.lbl_role.setStyleSheet("color: #38bdf8; background-color: rgba(56, 189, 248, 0.1); border: 1px solid #0284c7; border-radius: 6px; padding: 6px 12px; font-weight: 800;")
            self.btn_unlock_admin.setVisible(False)
            self.btn_change_pwd.setVisible(True)
            self.btn_lock_admin.setVisible(True)

            self.right_title.setText("Thông Tin Quản Trị (Toàn quyền)")
            self.lbl_emp_notice.setVisible(False)
            self.txt_mst.setReadOnly(False)
            self.txt_name.setReadOnly(False)
            self.txt_pwd.setReadOnly(False)
            self.btn_row_widget.setVisible(True)
        else:
            self.lbl_role.setText("👤 CHẾ ĐỘ NHÂN VIÊN (Chỉ tra cứu & đăng nhập)")
            self.lbl_role.setStyleSheet("color: #94a3b8; background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; font-weight: 700;")
            self.btn_unlock_admin.setVisible(True)
            self.btn_change_pwd.setVisible(False)
            self.btn_lock_admin.setVisible(False)

            self.right_title.setText("Thông Tin Doanh Nghiệp (Chế độ xem)")
            self.lbl_emp_notice.setVisible(True)
            self.txt_mst.setReadOnly(True)
            self.txt_name.setReadOnly(True)
            self.txt_pwd.setReadOnly(True)
            self.btn_row_widget.setVisible(False)

        # Refresh currently displayed item
        item = self.list_widget.currentItem()
        if item:
            self._on_item_clicked(item)

    def _unlock_admin(self):
        dlg = AdminVerifyDialog(self.db, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.is_admin = True
            self._update_admin_ui_state()
            self.admin_mode_changed.emit(True)
            QMessageBox.information(self, "Đã mở khóa", "Đã chuyển sang Quyền Quản Trị Viên (Admin) thành công!")

    def _lock_admin(self):
        self.is_admin = False
        self._update_admin_ui_state()
        self.admin_mode_changed.emit(False)
        QMessageBox.information(self, "Đã khóa", "Đã chuyển về Chế độ Nhân viên an toàn.")

    def _change_admin_pwd(self):
        dlg = AdminChangePasswordDialog(self.db, self)
        dlg.exec()

    def _load_businesses(self):
        self.list_widget.clear()
        businesses = self.db.get_all_businesses()
        for biz in businesses:
            text = f"{biz['name']}\nMST: {biz['tax_code']}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, biz)
            self.list_widget.addItem(item)

        if businesses:
            self.list_widget.setCurrentRow(0)
            self._on_item_clicked(self.list_widget.item(0))
        else:
            self._clear_form()

    def _on_item_clicked(self, item):
        if not item:
            return
        biz = item.data(Qt.ItemDataRole.UserRole)
        self.current_biz_id = biz.get("id")
        self.txt_mst.setText(biz.get("tax_code", ""))
        self.txt_name.setText(biz.get("name", ""))

        if self.is_admin:
            # Admin sees actual password
            self.txt_pwd.setText(biz.get("password", ""))
        else:
            # Employee only sees masked bullet characters
            self.txt_pwd.setText("●●●●●●●●●●●●")

    def _on_item_double_clicked(self, item):
        self._select_current_business()

    def _clear_form(self):
        if not self.is_admin:
            return
        self.current_biz_id = None
        self.txt_mst.clear()
        self.txt_name.clear()
        self.txt_pwd.clear()
        self.txt_mst.setFocus()
        self.list_widget.clearSelection()

    def _save_business(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Từ chối truy cập", "Chỉ Quản trị viên (Admin) mới có quyền lưu thông tin doanh nghiệp!")
            return

        mst = self.txt_mst.text().strip()
        name = self.txt_name.text().strip()
        pwd = self.txt_pwd.text().strip()

        if not mst or not pwd:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Mã số thuế và Mật khẩu!")
            return

        if not name:
            name = f"Doanh nghiệp {mst}"

        biz = self.db.save_business(mst, name, pwd)
        self._load_businesses()

        # Select saved business
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            b = item.data(Qt.ItemDataRole.UserRole)
            if b.get("tax_code") == mst:
                self.list_widget.setCurrentRow(i)
                self._on_item_clicked(item)
                break

        QMessageBox.information(self, "Thành công", f"Đã lưu và mã hóa thông tin doanh nghiệp:\n{name} ({mst})")

    def _delete_business(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Từ chối truy cập", "Chỉ Quản trị viên (Admin) mới có quyền xóa doanh nghiệp!")
            return

        if not self.current_biz_id:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn doanh nghiệp cần xóa từ danh sách!")
            return

        mst = self.txt_mst.text()
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa doanh nghiệp MST {mst} và toàn bộ dữ liệu hóa đơn liên quan khỏi hệ thống?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_business(self.current_biz_id)
            self._clear_form()
            self._load_businesses()

    def _select_current_business(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn doanh nghiệp từ danh sách!")
            return
        biz = item.data(Qt.ItemDataRole.UserRole)
        self.business_selected.emit(biz)
        self.accept()

    def _login_current_business(self):
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn doanh nghiệp từ danh sách!")
            return
        biz = item.data(Qt.ItemDataRole.UserRole)
        self.business_login_requested.emit(biz)
        self.accept()
