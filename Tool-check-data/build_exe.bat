@echo off
setlocal
cd /d "%~dp0"

tasklist /FI "IMAGENAME eq QLPNC10Checker.exe" 2>NUL | find /I "QLPNC10Checker.exe" >NUL
if not errorlevel 1 goto :app_running

set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

rem Prefer the project environment when it can build; otherwise use installed Python.
call "%PYTHON_EXE%" -c "import PyInstaller, oracledb, cryptography, openpyxl" >NUL 2>&1
if errorlevel 1 set "PYTHON_EXE=python"
call "%PYTHON_EXE%" -c "import PyInstaller, oracledb, cryptography, openpyxl" >NUL 2>&1
if errorlevel 1 goto :missing_build_dependencies

set "TCL_LIBRARY=%CD%\assets\tcl"
set "TK_LIBRARY=%CD%\assets\tk"
call "%PYTHON_EXE%" -m PyInstaller --noconfirm --clean QLPNC10Checker.spec
if errorlevel 1 goto :failed
if not exist "dist\province_fk_merge.csv" copy "province_fk_merge.csv" "dist\province_fk_merge.csv" >NUL

echo.
echo Build thanh cong: dist\QLPNC10Checker.exe
exit /b 0

:failed
echo.
echo Build that bai. Kiem tra loi phia tren.
exit /b 1

:missing_build_dependencies
echo.
echo Python can PyInstaller, oracledb, cryptography va openpyxl de build. Hay cai dat cac goi theo requirements.txt.
exit /b 1

:app_running
echo.
echo Hay dong tat ca cua so QLPNC10Checker.exe truoc khi build de cap nhat vao dist\QLPNC10Checker.exe.
exit /b 1
