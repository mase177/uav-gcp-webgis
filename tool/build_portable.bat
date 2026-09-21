@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Khong tim thay Python de tao ban dong goi.
    echo Cai Python 3.10-3.12, sau do chay lai file nay.
    pause
    exit /b 1
)

if not exist ".buildenv\Scripts\python.exe" (
    echo Dang tao moi truong dong goi...
    py -3 -m venv .buildenv
    if errorlevel 1 goto :error
)

echo Dang cai dat thu vien dong goi...
.buildenv\Scripts\python.exe -m pip install --upgrade pip
.buildenv\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 goto :error

echo Dang tao ban portable...
.buildenv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name GIS_Khop_Ranh --collect-data matplotlib --hidden-import matplotlib.backends.backend_qt5agg --hidden-import lxml.etree --exclude-module matplotlib.tests --exclude-module pandas.tests --exclude-module numpy.tests --exclude-module PyQt5.QtDesigner --exclude-module PyQt5.QtQuick --exclude-module PyQt5.QtQml main.py
if errorlevel 1 goto :error

if not exist "release\GIS_Khop_Ranh" mkdir "release\GIS_Khop_Ranh"
xcopy /E /I /Y "dist\GIS_Khop_Ranh\*" "release\GIS_Khop_Ranh\" >nul
copy /Y "Chay_Cong_Cu.bat" "release\GIS_Khop_Ranh\Chay_Cong_Cu.bat" >nul
copy /Y "HUONG_DAN_SU_DUNG.txt" "release\GIS_Khop_Ranh\HUONG_DAN_SU_DUNG.txt" >nul
powershell -NoProfile -Command "$bin = Join-Path $PWD 'release\GIS_Khop_Ranh\_internal\PyQt5\Qt5\bin'; $keep = @('Qt5Core.dll','Qt5Gui.dll','Qt5Widgets.dll','Qt5Network.dll','Qt5Svg.dll'); Get-ChildItem -LiteralPath $bin -Filter 'Qt5*.dll' | Where-Object { $_.Name -notin $keep } | Remove-Item -Force; Remove-Item -LiteralPath (Join-Path (Split-Path $bin) 'translations') -Recurse -Force"
powershell -NoProfile -Command "Compress-Archive -Path 'release\GIS_Khop_Ranh' -DestinationPath 'release\GIS_Khop_Ranh_Portable.zip' -Force"

echo.
echo Da tao xong: release\GIS_Khop_Ranh_Portable.zip
echo Giai nen file ZIP tren may khac, sau do chay Chay_Cong_Cu.bat.
pause
exit /b 0

:error
echo.
echo Dong goi that bai. Hay gui toan bo noi dung cua cua so nay de kiem tra.
pause
exit /b 1
