@echo off
title Cong Cu Khop Ranh Xa Phuong & Ranh Nghien Cuu
chcp 65001 >nul
echo Dang khoi dong ung dung...
start "" pythonw "%~dp0main.py"
if errorlevel 1 (
    echo Co loi khi khoi dong pythonw, thu lai voi python...
    python "%~dp0main.py"
    pause
)
