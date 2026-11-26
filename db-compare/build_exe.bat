@echo off
REM Dong goi gui.py thanh 1 file .exe doc lap (khong can cai Python tren may chay).
REM Chay tu thu muc db-compare: build_exe.bat

cd /d "%~dp0"
pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :eof

pyinstaller --noconfirm --onefile --windowed --name "SoSanhQLPN" ^
  --add-data "schema_old.json;." ^
  --add-data "schema_new.json;." ^
  --collect-all cryptography ^
  gui.py

echo.
echo Xong. File .exe nam o: dist\SoSanhQLPN.exe
