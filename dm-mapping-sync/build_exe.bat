@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo Khong tim thay Python 3.12 hoac .venv Python.
  exit /b 1
)

set "TCL_LIBRARY=%CD%\assets\tcl"
set "TK_LIBRARY=%CD%\assets\tk"
call "%PYTHON_EXE%" -m PyInstaller --noconfirm --clean QLPNDMSync.spec
if errorlevel 1 exit /b 1

echo.
echo Build thanh cong: dist\QLPNDMSync.exe
