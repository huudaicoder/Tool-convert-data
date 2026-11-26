@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
"%PYTHON_EXE%" -c "import PyInstaller,oracledb,cryptography" >NUL 2>&1
if errorlevel 1 (
 echo Python can PyInstaller, oracledb va cryptography de build. Cai dat: pip install -r requirements.txt
 exit /b 1
)
set "TCL_LIBRARY=%CD%\assets\tcl"
set "TK_LIBRARY=%CD%\assets\tk"
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean ChuyenDiaPhuongTienAn.spec
if errorlevel 1 exit /b 1
echo Build thanh cong: dist\ChuyenDiaPhuongTienAn.exe
