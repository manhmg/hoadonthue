@echo off
chcp 65001 >nul
title Quan Ly Hoa Don Dien Tu (Web Streamlit)
cd /d "%~dp0"

echo ===================================================================
echo   DANG KHOI CHAY UNG DUNG WEB QUAN LY HOA DON (STREAMLIT)...
echo   He thong se tu dong mo trinh duyet tai: http://localhost:8501
echo   Cac may khac trong mang truy cap qua IP may nay tren cong 8501
echo ===================================================================

start http://localhost:8501
python -m streamlit run web_app.py --server.port 8501 --server.address 0.0.0.0
pause
