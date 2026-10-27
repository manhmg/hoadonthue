# -*- coding: utf-8 -*-
"""
Tool Phát Web Hóa Đơn Trực Tuyến Qua Cloudflare Tunnel
Chạy cục bộ trên máy tính Việt Nam -> 100% không bị Cổng Thuế chặn Captcha/Timeout.
Nhân viên ở bất kỳ đâu cũng truy cập được qua đường link Cloudflare an toàn.
"""

import os
import sys
import time
import re
import subprocess
import threading
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CLOUDFLARED_EXE = BASE_DIR / "cloudflared.exe"

def ensure_cloudflared():
    if not CLOUDFLARED_EXE.exists():
        print("⏳ Đang tải Cloudflare Tunnel (cloudflared.exe) lần đầu tiên...")
        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        try:
            import urllib.request
            urllib.request.urlretrieve(download_url, str(CLOUDFLARED_EXE))
            print("✅ Đã tải xong cloudflared.exe!")
        except Exception as e:
            print(f"❌ Không thể tải tự động cloudflared: {e}")
            sys.exit(1)

def print_banner(public_url):
    border = "=" * 77
    print(f"\n{border}")
    print("  🎉 HỆ THỐNG QUẢN LÝ HÓA ĐƠN ĐIỆN TỬ ĐÃ PHÁT TRỰC TUYẾN THÀNH CÔNG!")
    print(border)
    print("  🌐 ĐƯỜNG LINK TRUY CẬP CHO NHÂN VIÊN (Ở BẤT KỲ ĐÂU):")
    print(f"  👉  {public_url}\n")
    print("  🏠 ĐƯỜNG LINK TRÊN MÁY NÀY (LOCAL):")
    print("  👉  http://localhost:8501\n")
    print("  🔑 MÃ TRUY CẬP CHO NHÂN VIÊN :  hoadon2026 (hoặc mã do Admin đã đổi)")
    print("  👑 QUYỀN QUẢN TRỊ VIÊN (ADMIN):  Nhập Mật khẩu Admin đã đặt để vào toàn quyền")
    print(border)
    print("  💡 LƯU Ý QUAN TRỌNG:")
    print("  • Hãy gửi đường link trên cho nhân viên truy cập trên máy tính hoặc điện thoại.")
    print("  • Giữ cửa sổ này mở để duy trì web hoạt động.")
    print("  • Toàn bộ kết nối Cổng Thuế chạy trực tiếp từ IP mạng Việt Nam của máy tính này,")
    print("    đảm bảo 100% KHÔNG BAO GIỜ bị chặn Captcha hay Timeout!")
    print(f"{border}\n")

def main():
    os.chdir(str(BASE_DIR))
    ensure_cloudflared()

    print("\n🚀 Đang khởi động máy chủ Web Hóa Đơn (Streamlit)...")
    st_proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", "web_app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--server.headless", "true"
        ],
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(2)

    print("🌐 Đang khởi tạo đường truyền bảo mật Cloudflare Tunnel...")
    cf_proc = subprocess.Popen(
        [str(CLOUDFLARED_EXE), "tunnel", "--url", "http://127.0.0.1:8501"],
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace"
    )

    public_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    def monitor_tunnel():
        nonlocal public_url
        for line in cf_proc.stdout:
            match = url_pattern.search(line)
            if match and not public_url:
                public_url = match.group(0)
                print_banner(public_url)
                try:
                    webbrowser.open(public_url)
                except Exception:
                    pass

    t = threading.Thread(target=monitor_tunnel, daemon=True)
    t.start()

    # Wait for URL or timeout
    waited = 0
    while not public_url and waited < 30:
        time.sleep(0.5)
        waited += 0.5

    if not public_url:
        print("⚠️ Chưa nhận diện được URL tự động. Vui lòng mở http://localhost:8501 để dùng trực tiếp.")

    try:
        while True:
            time.sleep(1)
            if st_proc.poll() is not None or cf_proc.poll() is not None:
                break
    except KeyboardInterrupt:
        print("\n🛑 Đang dừng hệ thống...")
    finally:
        st_proc.terminate()
        cf_proc.terminate()
        print("✅ Đã tắt ứng dụng an toàn.")

if __name__ == "__main__":
    main()
