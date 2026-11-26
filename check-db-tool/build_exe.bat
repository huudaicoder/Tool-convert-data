@echo off
setlocal
cd /d "%~dp0"

tasklist /FI "IMAGENAME eq QLPNC10Checker.exe" 2>NUL | find /I "QLPNC10Checker.exe" >NUL
if not errorlevel 1 goto :app_running

rem Remove staging folders left by earlier one-off builds. Normal builds always use dist/ and build/.
for %%D in (dist_update dist_update2 dist_update3 build_update build_update2 build_update3) do (
  if exist "%%D" rmdir /s /q "%%D"
)

if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto :failed
)

call ".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

set "TCL_LIBRARY=%CD%\assets\tcl"
set "TK_LIBRARY=%CD%\assets\tk"
call ".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "QLPNC10Checker" ^
  --add-data "assets\schema_old.json;assets" ^
  --add-data "assets\schema_new.json;assets" ^
  --collect-all oracledb ^
  app.py
if errorlevel 1 goto :failed

echo.
echo Build thanh cong: dist\QLPNC10Checker.exe
exit /b 0

:failed
echo.
echo Build that bai. Kiem tra loi phia tren.
exit /b 1

:app_running
echo.
echo Hay dong tat ca cua so QLPNC10Checker.exe truoc khi build de cap nhat vao dist\QLPNC10Checker.exe.
exit /b 1
