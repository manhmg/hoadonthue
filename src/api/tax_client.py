import os
import uuid
import requests
import json
import time
import logging
from urllib.parse import quote

logger = logging.getLogger("TaxClient")

BASE_URL = "https://hoadondientu.gdt.gov.vn"

class NoOriginalRecordError(Exception):
    """Raised when GDT indicates the invoice has no original XML/HTML record."""
    pass

class TaxClient:
    def __init__(self, token=None):
        self.session = requests.Session()
        self.token = token
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

    def set_token(self, token):
        self.token = token

    def _get_headers(self, action="", endpoint="/"):
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "request-id": str(uuid.uuid4()),
            "action": quote(action) if action else "",
            "end-point": endpoint
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def init_session(self):
        """Visit homepage to initialize session cookies."""
        try:
            r = self.session.get(f"{BASE_URL}/", headers=self._get_headers(), timeout=15)
            return r.status_code == 200
        except Exception as e:
            logger.error(f"Error initializing session: {e}")
            return False

    def get_captcha(self):
        """
        Fetch a new captcha from the GDT portal.
        Returns: (ckey, svg_content)
        """
        url = f"{BASE_URL}/api/captcha"
        headers = self._get_headers(action="", endpoint="/")
        r = self.session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("key"), data.get("content")
        else:
            raise Exception(f"Lỗi lấy captcha (HTTP {r.status_code}): {r.text}")

    def login(self, username, password, cvalue, ckey):
        """
        Authenticate with tax account.
        Returns: JWT token on success, raises Exception on failure.
        """
        url = f"{BASE_URL}/api/security-taxpayer/authenticate"
        headers = self._get_headers(action="", endpoint="/")
        payload = {
            "username": username.strip(),
            "password": password.strip(),
            "cvalue": cvalue.strip(),
            "ckey": ckey
        }
        r = self.session.post(url, headers=headers, json=payload, timeout=20)
        if r.status_code == 200:
            data = r.json()
            self.token = data.get("token")
            if not self.token:
                raise Exception("Không tìm thấy token trong phản hồi máy chủ.")
            # Prime session
            self._prime_session()
            return self.token
        else:
            try:
                err_data = r.json()
                msg = err_data.get("message", r.text)
            except Exception:
                msg = r.text
            raise Exception(f"Đăng nhập thất bại: {msg}")

    def check_token_valid(self):
        """Check if current Bearer token is still valid."""
        if not self.token:
            return False
        try:
            url = f"{BASE_URL}/api/security-taxpayer/profile"
            headers = self._get_headers(action="", endpoint="/")
            r = self.session.get(url, headers=headers, timeout=10)
            return r.status_code == 200
        except Exception:
            return False

    def _prime_session(self):
        """Perform profile check to prime session."""
        try:
            url = f"{BASE_URL}/api/security-taxpayer/profile"
            headers = self._get_headers(action="", endpoint="/")
            self.session.get(url, headers=headers, timeout=10)
        except Exception as e:
            logger.warning(f"Priming session failed (can be ignored): {e}")

    def _chunk_date_range(self, from_date_str, to_date_str):
        """Split a date range into subranges of at most 30 days."""
        from datetime import datetime, timedelta
        d1 = datetime.strptime(from_date_str, "%d/%m/%Y").date()
        d2 = datetime.strptime(to_date_str, "%d/%m/%Y").date()
        if d1 > d2:
            d1, d2 = d2, d1
        
        chunks = []
        cur_start = d1
        while cur_start <= d2:
            cur_end = min(cur_start + timedelta(days=29), d2)
            chunks.append((cur_start.strftime("%d/%m/%Y"), cur_end.strftime("%d/%m/%Y")))
            cur_start = cur_end + timedelta(days=1)
        return chunks

    def _search_invoices_single_window(self, inv_type, from_date_str, to_date_str, is_sco=False, progress_callback=None):
        """Internal helper to query a single <= 30 day window with 429 rate limit retry."""
        prefix = "sco-query" if is_sco else "query"
        endpoint_type = "purchase" if inv_type == "purchase" else "sold"
        base_query_url = f"{BASE_URL}/api/{prefix}/invoices/{endpoint_type}"

        search_query = f"tdlap=ge={from_date_str}T00:00:00;tdlap=le={to_date_str}T23:59:59"
        encoded_search = quote(search_query)

        window_invoices = []
        state = None

        while True:
            params = [
                "sort=tdlap:desc",
                "size=15",
                f"search={encoded_search}"
            ]
            if state:
                params.append(f"state={quote(state)}")

            url = f"{base_query_url}?{'&'.join(params)}"
            action_text = "Tra cứu hóa đơn mua vào" if inv_type == "purchase" else "Tra cứu hóa đơn bán ra"

            r = None
            for attempt in range(5):
                headers = self._get_headers(action=action_text, endpoint="/tra-cuu/tra-cuu-hoa-don")
                r = self.session.get(url, headers=headers, timeout=30)
                if r.status_code == 200:
                    break
                elif r.status_code == 429:
                    wait_time = 2.0 * (attempt + 1)
                    logger.warning(f"GDT Rate limit (429), chờ {wait_time}s rồi thử lại (lần {attempt+1}/5)...")
                    if progress_callback:
                        progress_callback(f"Máy chủ Thuế quá tải (429), đang tự động chờ {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    break

            if r is None or r.status_code != 200:
                try:
                    err = r.json().get("message", r.text) if r else "Không có phản hồi từ máy chủ"
                except Exception:
                    err = r.text if r else "Lỗi kết nối"
                status = r.status_code if r else 0
                raise Exception(f"Lỗi tra cứu hóa đơn ({status}): {err}")

            res_data = r.json()
            items = res_data.get("datas", [])
            if not items:
                break

            window_invoices.extend(items)
            state = res_data.get("state")
            if not state or len(items) < 15:
                break

            # Polite delay between pages
            time.sleep(1.0)

        return window_invoices

    def search_invoices(self, inv_type="purchase", from_date_str="26/09/2026", to_date_str="25/10/2026", is_sco=False, progress_callback=None):
        """
        Query invoices (inv_type='purchase' or 'sold') in date range.
        Format: DD/MM/YYYY. Automatically chunks long date ranges (>30 days).
        Includes rate-limiting retries and polite pauses to prevent 429 errors.
        Returns list of invoice items.
        """
        if not self.token:
            raise Exception("Chưa đăng nhập hệ thống.")

        chunks = self._chunk_date_range(from_date_str, to_date_str)
        all_invoices = []
        seen_keys = set()

        for idx, (chunk_from, chunk_to) in enumerate(chunks):
            if idx > 0:
                time.sleep(1.0) # Pause between chunks

            if progress_callback:
                progress_callback(f"Đang đồng bộ chặng {idx+1}/{len(chunks)} ({chunk_from} - {chunk_to})...")

            chunk_results = self._search_invoices_single_window(
                inv_type=inv_type,
                from_date_str=chunk_from,
                to_date_str=chunk_to,
                is_sco=is_sco,
                progress_callback=progress_callback
            )
            for inv in chunk_results:
                key = (inv.get("khhdon"), inv.get("shdon"), inv.get("nbmst"))
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_invoices.append(inv)

        return all_invoices

    def download_invoice_xml_zip(self, nbmst, khhdon, shdon, khmshdon, is_sco=False):
        """
        Download the invoice archive (ZIP) containing original XML.
        Returns: bytes of ZIP file
        Raises: NoOriginalRecordError if invoice has no original file on GDT (e.g. bank invoices).
        """
        if not self.token:
            raise Exception("Chưa đăng nhập hệ thống.")

        prefix = "sco-query" if is_sco else "query"
        url = (
            f"{BASE_URL}/api/{prefix}/invoices/export-xml?"
            f"nbmst={quote(str(nbmst))}&"
            f"khhdon={quote(str(khhdon))}&"
            f"shdon={quote(str(shdon))}&"
            f"khmshdon={quote(str(khmshdon))}"
        )

        r = None
        for attempt in range(5):
            headers = self._get_headers(action="Xuất xml", endpoint="/tra-cuu/tra-cuu-hoa-don")
            headers["Accept"] = "application/octet-stream, application/zip, */*"
            r = self.session.get(url, headers=headers, timeout=45)
            if r.status_code == 200:
                if r.headers.get("Content-Type", "").startswith("application/json"):
                    try:
                        err = r.json().get("message", "Không tồn tại hồ sơ gốc")
                    except Exception:
                        err = "Không tồn tại hồ sơ gốc"
                    if "Không tồn tại hồ sơ gốc" in err or "không có hồ sơ gốc" in err:
                        raise NoOriginalRecordError(err)
                    raise Exception(err)
                return r.content
            elif r.status_code == 429:
                wait_time = 2.0 * (attempt + 1)
                logger.warning(f"Rate limited (429) on HĐ {shdon}, waiting {wait_time}s (attempt {attempt+1}/5)...")
                time.sleep(wait_time)
            elif r.status_code == 500:
                try:
                    err_json = r.json()
                    err_msg = err_json.get("message", "")
                except Exception:
                    err_msg = r.text
                if "Không tồn tại hồ sơ gốc" in err_msg or "không có hồ sơ gốc" in err_msg:
                    raise NoOriginalRecordError(err_msg)
                raise Exception(f"Lỗi máy chủ Thuế (500): {err_msg}")
            else:
                break

        if r is None or r.status_code != 200:
            status = r.status_code if r else 0
            raise Exception(f"Lỗi tải file XML (HTTP {status})")
