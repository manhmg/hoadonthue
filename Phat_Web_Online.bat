@echo off
chcp 65001 >nul
title Phat Web Quan Ly Hoa Don (Cloudflare Tunnel)
cd /d "%~dp0"

echo ===================================================================
echo   PHAT HE THONG WEB HOA DON DIEN TU TRUC TUYEN CHO NHAN VIEN
echo   Ket noi Cong Thue truc tiep bang IP Viet Nam (Khong bao gio chan)
echo ===================================================================

python run_share_web.py
pause
