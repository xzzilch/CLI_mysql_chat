@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    where python >nul 2>nul
    if errorlevel 1 goto :no_python
    set PYTHON=python
) else (
    set PYTHON=py -3
)

%PYTHON% -c "import sys; raise SystemExit(sys.version_info < (3, 10))"
if errorlevel 1 (
    echo Python 3.10 or later is required. Install it from https://www.python.org/downloads/
    echo During setup, enable "Add Python to PATH".
    pause
    exit /b 1
)

if not exist .venv\Scripts\python.exe (
    %PYTHON% -m venv .venv
    if errorlevel 1 goto :failed
)

.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo Installation complete.
echo Start the chat with start_chat_windows.bat
echo To provision a new database, run: .venv\Scripts\python.exe provision_database.py
pause
exit /b 0

:no_python
echo Python 3.10 or later was not found. Install it from https://www.python.org/downloads/
echo During setup, enable "Add Python to PATH".
pause
exit /b 1

:failed
echo.
echo Setup failed. Check the Python installation and internet connection, then run this file again.
pause
exit /b 1
