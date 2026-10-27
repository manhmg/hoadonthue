import sys
import os
import shutil
import zipfile
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from playwright.sync_api import sync_playwright
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger("InvoiceService")

class InvoiceService:
    def __init__(self, assets_dir=None, db=None):
        if assets_dir is None:
            if hasattr(sys, '_MEIPASS') and (Path(sys._MEIPASS) / "assets").exists():
                self.assets_dir = Path(sys._MEIPASS) / "assets"
            elif getattr(sys, 'frozen', False) and (Path(sys.executable).resolve().parent / "assets").exists():
                self.assets_dir = Path(sys.executable).resolve().parent / "assets"
            else:
                self.assets_dir = Path(__file__).resolve().parent.parent.parent / "assets"
        else:
            self.assets_dir = Path(assets_dir)
        self.db = db

    def ensure_viewer_assets(self, target_folder):
        """
        Copy details.js, viewinvoice-bg.jpg, and sign-check.jpg to target folder
        so that invoice HTML can render properly.
        """
        target_path = Path(target_folder)
        target_path.mkdir(parents=True, exist_ok=True)

        required_files = ["details.js", "viewinvoice-bg.jpg", "sign-check.jpg"]
        for f in required_files:
            src_file = self.assets_dir / f
            dst_file = target_path / f
            if src_file.exists():
                try:
                    shutil.copy2(src_file, dst_file)
                except Exception as e:
                    logger.warning(f"Could not copy asset {f}: {e}")

    def parse_xml_line_items(self, xml_path):
        """
        Extract detailed merchandise line items from invoice XML.
        Returns list of dicts.
        """
        items = []
        if not os.path.exists(xml_path):
            return items

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Remove namespace prefixes if any
            for elem in root.iter():
                if "}" in elem.tag:
                    elem.tag = elem.tag.split("}", 1)[1]

            # Find all <HHDVu> or line item nodes
            hhdvu_nodes = root.findall(".//HHDVu")
            for idx, node in enumerate(hhdvu_nodes):
                ten = node.findtext("THHDVu") or node.findtext("TenHHDVu") or ""
                dvt = node.findtext("DVTinh") or ""
                sl_str = node.findtext("SLuong") or "0"
                dg_str = node.findtext("DGia") or "0"
                tt_str = node.findtext("ThTien") or "0"
                ts_str = node.findtext("TSuat") or ""
                tthue_str = node.findtext("TThue") or "0"

                def to_float(val):
                    try:
                        return float(str(val).replace(",", "").strip())
                    except Exception:
                        return 0.0

                items.append({
                    "stt": idx + 1,
                    "ten_hang": ten.strip(),
                    "dvt": dvt.strip(),
                    "so_luong": to_float(sl_str),
                    "don_gia": to_float(dg_str),
                    "thanh_tien": to_float(tt_str),
                    "thue_suat": ts_str.strip(),
                    "tien_thue": to_float(tthue_str)
                })
        except Exception as e:
            logger.warning(f"Error parsing XML line items from {xml_path}: {e}")

        return items

    def process_invoice_zip(self, zip_bytes, output_dir, file_prefix="HD", invoice_db_id=None, convert_pdf=True):
        """
        Process the downloaded ZIP bytes:
        - Extracts XML and HTML files.
        - Parses line items from XML and saves to DB.
        - Converts HTML to PDF via headless Chromium (if convert_pdf=True).
        - Returns dict with paths: {'pdf': path, 'xml': path, 'html': path, 'items': [...]}
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        self.ensure_viewer_assets(output_path)

        temp_zip_file = output_path / f"temp_{file_prefix}.zip"
        with open(temp_zip_file, "wb") as f:
            f.write(zip_bytes)

        extracted_xml = None
        extracted_html = None
        extracted_pdf = None

        try:
            with zipfile.ZipFile(temp_zip_file, "r") as zf:
                for member in zf.namelist():
                    lower_name = member.lower()
                    if lower_name.endswith(".xml"):
                        zf.extract(member, output_path)
                        orig_xml = output_path / member
                        final_xml = output_path / f"{file_prefix}.xml"
                        if orig_xml.exists():
                            if final_xml.exists():
                                final_xml.unlink()
                            orig_xml.rename(final_xml)
                            extracted_xml = str(final_xml)
                    elif lower_name.endswith(".html"):
                        zf.extract(member, output_path)
                        orig_html = output_path / member
                        final_html = output_path / f"{file_prefix}.html"
                        if orig_html.exists():
                            if final_html.exists():
                                final_html.unlink()
                            orig_html.rename(final_html)
                            extracted_html = str(final_html)
                    elif lower_name.endswith(".pdf"):
                        zf.extract(member, output_path)
                        orig_pdf = output_path / member
                        final_pdf = output_path / f"{file_prefix}.pdf"
                        if orig_pdf.exists():
                            if final_pdf.exists():
                                final_pdf.unlink()
                            orig_pdf.rename(final_pdf)
                            extracted_pdf = str(final_pdf)
        finally:
            if temp_zip_file.exists():
                try:
                    temp_zip_file.unlink()
                except Exception:
                    pass

        # Parse line items and save to DB
        items = []
        if extracted_xml:
            items = self.parse_xml_line_items(extracted_xml)
            if self.db and invoice_db_id:
                try:
                    self.db.save_invoice_items(invoice_db_id, items)
                except Exception as e:
                    logger.warning(f"Error saving line items to DB: {e}")

        # If PDF wasn't directly in ZIP, convert HTML to PDF (if requested)
        if convert_pdf and not extracted_pdf and extracted_html:
            pdf_path = output_path / f"{file_prefix}.pdf"
            try:
                self.convert_html_to_pdf(extracted_html, str(pdf_path))
                if pdf_path.exists():
                    extracted_pdf = str(pdf_path)
            except Exception as e:
                logger.error(f"Failed to convert HTML to PDF: {e}")

        # Update DB with paths
        if self.db and invoice_db_id:
            try:
                self.db.update_invoice_files(
                    invoice_id=invoice_db_id,
                    xml_path=extracted_xml,
                    pdf_path=extracted_pdf,
                    xml_status=1 if extracted_xml else 0
                )
            except Exception as e:
                logger.warning(f"Error updating invoice file paths: {e}")

        return {
            "pdf": extracted_pdf,
            "xml": extracted_xml,
            "html": extracted_html,
            "items": items
        }

    def _launch_browser(self, p):
        """
        Launch Chromium browser with robust fallbacks for portable/standalone deployment.
        Falls back to Microsoft Edge / Chrome if ms-playwright binaries are not present.
        """
        candidate_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        for c_path in candidate_paths:
            if os.path.exists(c_path):
                try:
                    return p.chromium.launch(executable_path=c_path, headless=True)
                except Exception as e:
                    logger.warning(f"Could not launch browser at {c_path}: {e}")

        return p.chromium.launch(headless=True)

    def convert_html_to_pdf(self, html_path, pdf_path):
        """
        Convert an HTML invoice file to PDF using headless Chromium.
        """
        html_uri = Path(html_path).resolve().as_uri()
        with sync_playwright() as p:
            browser = self._launch_browser(p)
            page = browser.new_page()
            page.goto(html_uri, wait_until="load")
            page.wait_for_timeout(500)

            # Inject print style for pure white background without watermark patterns
            page.evaluate("""() => {
                const style = document.createElement('style');
                style.innerHTML = `
                @media print {
                    body {
                        -webkit-print-color-adjust: exact;
                        print-color-adjust: exact;
                        background-color: #ffffff !important;
                        background-image: url(viewinvoice-bg.jpg) !important;
                        background-repeat: no-repeat;
                        background-position: center center;
                        background-size: cover;
                    }
                    .watermark, #watermark, [class*="watermark"], [id*="watermark"], .bg-invoice {
                        display: none !important;
                        background: none !important;
                    }
                }
                `;
                document.head.appendChild(style);
            }""")

            page.pdf(
                path=pdf_path,
                format="A4",
                print_background=True,
                margin={"top": "0.4in", "right": "0.4in", "bottom": "0.4in", "left": "0.4in"}
            )
            browser.close()

    # ================= EXPORT EXCEL =================

    def export_excel(self, invoices, export_type, output_filepath):
        """
        Export invoices to Excel.
        export_type: 'standard' (Bảng kê tiêu chuẩn) or 'detailed' (Bảng kê chi tiết hàng hóa)
        """
        wb = openpyxl.Workbook()
        ws = wb.active

        # Styling definitions
        font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        fill_header = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Navy blue
        font_title = Font(name="Segoe UI", size=14, bold=True, color="1E3A8A")
        font_body = Font(name="Segoe UI", size=10)
        border_thin = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1")
        )
        align_center = Alignment(horizontal="center", vertical="center")
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")

        if export_type == "detailed":
            ws.title = "Chi Tiết Hàng Hóa"
            # Title row
            ws.merge_cells("A1:N1")
            ws["A1"] = "BẢNG KÊ CHI TIẾT HÀNG HÓA - DỊCH VỤ HÓA ĐƠN"
            ws["A1"].font = font_title
            ws["A1"].alignment = align_center

            headers = [
                "STT", "Ký hiệu", "Số HĐ", "Ngày lập", "MST Người bán", "Tên Người bán",
                "Tên hàng hóa, dịch vụ", "ĐVT", "Số lượng", "Đơn giá", "Thành tiền chưa thuế",
                "Thuế suất", "Tiền thuế", "Tổng tiền thanh toán"
            ]
            ws.append([]) # row 2 empty
            ws.append(headers) # row 3

            current_row = 4
            stt = 1
            for inv in invoices:
                shdon = inv.get("shdon", "")
                khhdon = inv.get("khhdon", "")
                tdlap = str(inv.get("tdlap", ""))[:10]
                nbmst = inv.get("nbmst", "")
                nbten = inv.get("nbten", "")
                tgtttbso = float(inv.get("tgtttbso") or 0)

                # Get line items from DB or parse XML
                items = []
                inv_id = inv.get("id")
                if self.db and inv_id:
                    items = self.db.get_invoice_items(inv_id)
                elif inv.get("xml_path") and os.path.exists(inv.get("xml_path")):
                    items = self.parse_xml_line_items(inv["xml_path"])

                if not items:
                    # If no items parsed, output single invoice row
                    ws.append([
                        stt, khhdon, shdon, tdlap, nbmst, nbten,
                        "(Không có chi tiết)", "", 0, 0,
                        float(inv.get("tgtcthue") or 0), "", float(inv.get("tgtthue") or 0), tgtttbso
                    ])
                    stt += 1
                    current_row += 1
                else:
                    for item in items:
                        ws.append([
                            stt, khhdon, shdon, tdlap, nbmst, nbten,
                            item.get("ten_hang", ""),
                            item.get("dvt", ""),
                            item.get("so_luong", 0),
                            item.get("don_gia", 0),
                            item.get("thanh_tien", 0),
                            item.get("thue_suat", ""),
                            item.get("tien_thue", 0),
                            tgtttbso
                        ])
                        stt += 1
                        current_row += 1

        else: # standard
            ws.title = "Bảng Kê Tiêu Chuẩn"
            ws.merge_cells("A1:L1")
            ws["A1"] = "BẢNG KÊ TIÊU CHUẨN HÓA ĐƠN"
            ws["A1"].font = font_title
            ws["A1"].alignment = align_center

            headers = [
                "STT", "Ký hiệu mẫu", "Ký hiệu HĐ", "Số HĐ", "Ngày lập",
                "MST Người bán", "Tên Người bán", "MST Người mua", "Tên Người mua",
                "Tiền chưa thuế", "Tiền thuế", "Tổng tiền thanh toán"
            ]
            ws.append([]) # row 2 empty
            ws.append(headers) # row 3

            for idx, inv in enumerate(invoices):
                ws.append([
                    idx + 1,
                    inv.get("khmshdon", "1"),
                    inv.get("khhdon", ""),
                    inv.get("shdon", ""),
                    str(inv.get("tdlap", ""))[:10],
                    inv.get("nbmst", ""),
                    inv.get("nbten", ""),
                    inv.get("nmmst", ""),
                    inv.get("nmten", ""),
                    float(inv.get("tgtcthue") or 0),
                    float(inv.get("tgtthue") or 0),
                    float(inv.get("tgtttbso") or 0)
                ])

        # Style header row (row 3)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=3, column=col_idx)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center
            cell.border = border_thin

        # Style data cells
        for row in range(4, ws.max_row + 1):
            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=row, column=col)
                cell.font = font_body
                cell.border = border_thin
                val = cell.value
                if isinstance(val, (int, float)):
                    cell.number_format = "#,##0"
                    cell.alignment = align_right
                else:
                    if col in [1, 2, 3, 4, 5, 8]:
                        cell.alignment = align_center
                    else:
                        cell.alignment = align_left

        # Adjust column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.row >= 3 and cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        wb.save(output_filepath)
        return output_filepath
