@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist "GIS_Khop_Ranh.exe" (
    echo Khong tim thay GIS_Khop_Ranh.exe.
    echo Hay giu nguyen toan bo thu muc da dong goi khi sao chep sang may khac.
    pause
    exit /b 1
)

start "" "%~dp0GIS_Khop_Ranh.exe"
