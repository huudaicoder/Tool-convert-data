@echo off
setlocal
cd /d "%~dp0"

tasklist /FI "IMAGENAME eq GopMaTinhThanh.exe" 2>NUL | find /I "GopMaTinhThanh.exe" >NUL
if not errorlevel 1 goto :app_running

set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
call "%PYTHON_EXE%" -c "import PyInstaller, oracledb, cryptography" >NUL 2>&1
if errorlevel 1 goto :missing_build_dependencies

set "TCL_LIBRARY=%CD%\assets\tcl"
set "TK_LIBRARY=%CD%\assets\tk"
call "%PYTHON_EXE%" -m PyInstaller --noconfirm --clean GopMaTinhThanh.spec
if errorlevel 1 goto :failed
if not exist "dist\province_fk_merge.csv" copy "province_fk_merge.csv" "dist\province_fk_merge.csv" >NUL

echo.
echo Build thanh cong: dist\GopMaTinhThanh.exe
echo Dat province_fk_merge.csv cung thu muc voi file EXE.
exit /b 0

:failed
echo.
echo Build that bai. Kiem tra loi phia tren.
exit /b 1

:missing_build_dependencies
echo.
echo Can PyInstaller, oracledb va cryptography. Cai requirements.txt trong .venv truoc.
exit /b 1

:app_running
echo.
echo Hay dong GopMaTinhThanh.exe truoc khi build de cap nhat file trong dist.
exit /b 1
