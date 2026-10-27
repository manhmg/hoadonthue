import sqlite3
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("Database")

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent

from src.db.security import (
    hash_password, verify_password, encrypt_text, decrypt_text, secrets
)

DB_PATH = get_base_dir() / "data" / "hoadon.db"

class Database:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            
            # 0. Bảng cấu hình hệ thống (System Settings & Admin Security)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
            """)

            # Đảm bảo có seed mã hóa dữ liệu
            cur.execute("SELECT value FROM system_settings WHERE key = 'db_seed'")
            if not cur.fetchone():
                seed = secrets.token_hex(16)
                cur.execute("INSERT INTO system_settings (key, value) VALUES ('db_seed', ?)", (seed,))

            # 1. Bảng doanh nghiệp (Businesses)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS businesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tax_code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    password TEXT NOT NULL,
                    token TEXT,
                    token_updated_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Bảng hóa đơn (Invoices)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_id INTEGER NOT NULL,
                    inv_type TEXT NOT NULL DEFAULT 'purchase',
                    shdon TEXT NOT NULL,
                    khhdon TEXT NOT NULL,
                    khmshdon TEXT DEFAULT '1',
                    tdlap TEXT NOT NULL,
                    nbmst TEXT,
                    nbten TEXT,
                    nmmst TEXT,
                    nmten TEXT,
                    tgtcthue REAL DEFAULT 0,
                    tgtthue REAL DEFAULT 0,
                    tgtttbso REAL DEFAULT 0,
                    ttxly TEXT,
                    xml_path TEXT,
                    pdf_path TEXT,
                    xml_status INTEGER DEFAULT 0,
                    raw_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(business_id, inv_type, khhdon, shdon, nbmst)
                );
            """)

            # 3. Bảng chi tiết hàng hóa (Invoice Line Items)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoice_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER NOT NULL,
                    stt INTEGER,
                    ten_hang TEXT,
                    dvt TEXT,
                    so_luong REAL DEFAULT 0,
                    don_gia REAL DEFAULT 0,
                    thanh_tien REAL DEFAULT 0,
                    thue_suat TEXT,
                    tien_thue REAL DEFAULT 0,
                    FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
                );
            """)

            conn.commit()

    # ================= QUẢN TRỊ ADMIN & BẢO MẬT =================

    def _get_db_seed(self) -> str:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM system_settings WHERE key = 'db_seed'")
            row = cur.fetchone()
            if row and row["value"]:
                return row["value"]
            seed = secrets.token_hex(16)
            cur.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('db_seed', ?)", (seed,))
            conn.commit()
            return seed

    def is_admin_password_set(self) -> bool:
        """Kiểm tra xem hệ thống đã thiết lập mật khẩu Admin chưa."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM system_settings WHERE key = 'admin_pwd_hash'")
            return cur.fetchone() is not None

    def set_admin_password(self, password: str) -> bool:
        """Thiết lập hoặc đổi mật khẩu Admin (lưu hash + salt)."""
        pwd_hash, salt = hash_password(password)
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('admin_pwd_hash', ?)", (pwd_hash,))
            cur.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('admin_pwd_salt', ?)", (salt,))
            conn.commit()
            return True

    def verify_admin_password(self, password: str) -> bool:
        """Xác thực mật khẩu Admin."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM system_settings WHERE key = 'admin_pwd_hash'")
            h_row = cur.fetchone()
            cur.execute("SELECT value FROM system_settings WHERE key = 'admin_pwd_salt'")
            s_row = cur.fetchone()
            if not h_row or not s_row:
                return False
            return verify_password(password, h_row["value"], s_row["value"])

    def get_employee_access_code(self) -> str:
        """Lấy mã truy cập nội bộ cho nhân viên (đã giải mã)."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM system_settings WHERE key = 'employee_access_code'")
            row = cur.fetchone()
            if row and row["value"]:
                return decrypt_text(row["value"], self._get_db_seed())
            default_code = "hoadon2026"
            self.set_employee_access_code(default_code)
            return default_code

    def set_employee_access_code(self, code: str) -> bool:
        """Thiết lập hoặc đổi mã truy cập nội bộ cho nhân viên (lưu mã hóa)."""
        enc_code = encrypt_text(code.strip(), self._get_db_seed())
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('employee_access_code', ?)", (enc_code,))
            conn.commit()
            return True

    def verify_employee_access_code(self, code: str) -> bool:
        """Kiểm tra mã truy cập nội bộ của nhân viên."""
        if not code:
            return False
        current_code = self.get_employee_access_code()
        return secrets.compare_digest(code.strip(), current_code.strip())

    def _decrypt_biz_row(self, row):
        if not row:
            return None
        d = dict(row)
        if "password" in d and d["password"]:
            d["password"] = decrypt_text(d["password"], self._get_db_seed())
        return d

    # ================= CRUD DOANH NGHIỆP =================

    def get_all_businesses(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM businesses ORDER BY id DESC")
            return [self._decrypt_biz_row(row) for row in cur.fetchall()]

    def get_business_by_id(self, biz_id):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM businesses WHERE id = ?", (biz_id,))
            row = cur.fetchone()
            return self._decrypt_biz_row(row) if row else None

    def get_business_by_tax_code(self, tax_code):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM businesses WHERE tax_code = ?", (tax_code.strip(),))
            row = cur.fetchone()
            return self._decrypt_biz_row(row) if row else None

    def save_business(self, tax_code, name, password):
        tax_code = tax_code.strip()
        name = name.strip()
        raw_pwd = password.strip()
        # Mã hóa mật khẩu thuế trước khi lưu vào SQLite để bảo mật
        encrypted_pwd = encrypt_text(raw_pwd, self._get_db_seed())
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO businesses (tax_code, name, password)
                VALUES (?, ?, ?)
                ON CONFLICT(tax_code) DO UPDATE SET
                    name = excluded.name,
                    password = excluded.password
            """, (tax_code, name, encrypted_pwd))
            conn.commit()
            return self.get_business_by_tax_code(tax_code)

    def delete_business(self, biz_id):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM invoices WHERE business_id = ?", (biz_id,))
            cur.execute("DELETE FROM businesses WHERE id = ?", (biz_id,))
            conn.commit()
            return True

    def update_business_token(self, biz_id, token):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE businesses
                SET token = ?, token_updated_at = ?
                WHERE id = ?
            """, (token, datetime.now().isoformat(), biz_id))
            conn.commit()

    # ================= CRUD HÓA ĐƠN =================

    def upsert_invoice(self, business_id, inv_type, inv_data):
        shdon = str(inv_data.get("shdon", "")).strip()
        khhdon = str(inv_data.get("khhdon", "")).strip()
        khmshdon = str(inv_data.get("khmshdon", "1")).strip()
        tdlap = str(inv_data.get("tdlap", "")).strip()
        nbmst = str(inv_data.get("nbmst", "")).strip()
        nbten = str(inv_data.get("nbten", "")).strip()
        nmmst = str(inv_data.get("nmmst", "")).strip()
        nmten = str(inv_data.get("nmten", "")).strip()
        
        tgtcthue = float(inv_data.get("tgtcthue") or 0)
        tgtthue = float(inv_data.get("tgtthue") or 0)
        tgtttbso = float(inv_data.get("tgtttbso") or 0)
        ttxly = str(inv_data.get("ttxly", "")).strip()

        raw_json_str = json.dumps(inv_data, ensure_ascii=False)

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO invoices (
                    business_id, inv_type, shdon, khhdon, khmshdon, tdlap,
                    nbmst, nbten, nmmst, nmten, tgtcthue, tgtthue, tgtttbso,
                    ttxly, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(business_id, inv_type, khhdon, shdon, nbmst) DO UPDATE SET
                    khmshdon = excluded.khmshdon,
                    tdlap = excluded.tdlap,
                    nbten = excluded.nbten,
                    nmmst = excluded.nmmst,
                    nmten = excluded.nmten,
                    tgtcthue = excluded.tgtcthue,
                    tgtthue = excluded.tgtthue,
                    tgtttbso = excluded.tgtttbso,
                    ttxly = excluded.ttxly,
                    raw_json = excluded.raw_json
            """, (
                business_id, inv_type, shdon, khhdon, khmshdon, tdlap,
                nbmst, nbten, nmmst, nmten, tgtcthue, tgtthue, tgtttbso,
                ttxly, raw_json_str
            ))
            conn.commit()
            return cur.lastrowid

    def update_invoice_files(self, invoice_id, xml_path=None, pdf_path=None, xml_status=1):
        with self._get_connection() as conn:
            cur = conn.cursor()
            updates = []
            params = []
            if xml_path:
                updates.append("xml_path = ?")
                params.append(xml_path)
            if pdf_path:
                updates.append("pdf_path = ?")
                params.append(pdf_path)
            updates.append("xml_status = ?")
            params.append(xml_status)
            
            params.append(invoice_id)
            cur.execute(f"UPDATE invoices SET {', '.join(updates)} WHERE id = ?", tuple(params))
            conn.commit()

    def save_invoice_items(self, invoice_id, items):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
            for item in items:
                cur.execute("""
                    INSERT INTO invoice_items (
                        invoice_id, stt, ten_hang, dvt, so_luong, don_gia, thanh_tien, thue_suat, tien_thue
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice_id,
                    item.get("stt", 1),
                    item.get("ten_hang", ""),
                    item.get("dvt", ""),
                    float(item.get("so_luong") or 0),
                    float(item.get("don_gia") or 0),
                    float(item.get("thanh_tien") or 0),
                    str(item.get("thue_suat", "")),
                    float(item.get("tien_thue") or 0)
                ))
            conn.commit()

    def get_invoice_items(self, invoice_id):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM invoice_items WHERE invoice_id = ? ORDER BY stt ASC", (invoice_id,))
            return [dict(row) for row in cur.fetchall()]

    # ================= TRA CỨU NỘI BỘ =================

    def search_local_invoices(self, business_id, inv_type, from_date_str=None, to_date_str=None, search_keyword=None):
        """
        Tra cứu nội bộ từ SQLite.
        Dates in DD/MM/YYYY or YYYY-MM-DD
        """
        query = "SELECT * FROM invoices WHERE business_id = ? AND inv_type = ?"
        params = [business_id, inv_type]

        if from_date_str and to_date_str:
            # Parse dates for comparison
            # In SQLite tdlap can be '2026-10-25T14:00:00' or '25/10/2026'
            # We convert comparison strings
            try:
                dt_from = datetime.strptime(from_date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                dt_to = datetime.strptime(to_date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                query += " AND (substr(tdlap, 1, 10) >= ? AND substr(tdlap, 1, 10) <= ?)"
                params.extend([dt_from, dt_to])
            except Exception:
                pass

        if search_keyword:
            kw = f"%{search_keyword.strip()}%"
            query += " AND (shdon LIKE ? OR khhdon LIKE ? OR nbmst LIKE ? OR nbten LIKE ? OR nmmst LIKE ? OR nmten LIKE ?)"
            params.extend([kw, kw, kw, kw, kw, kw])

        query += " ORDER BY tdlap DESC"

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, tuple(params))
            return [dict(row) for row in cur.fetchall()]
