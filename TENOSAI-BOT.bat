@echo off
setlocal

REM Change directory to the script's own directory to ensure paths are correct
cd /d %~dp0

REM Locate a Python interpreter (prefer the launcher when available).
set "PY_CMD="
py -3 --version >nul 2>&1 && set "PY_CMD=py -3"
if not defined PY_CMD (
    python --version >nul 2>&1 && set "PY_CMD=python"
)

if not defined PY_CMD (
    echo ERROR: Python 3.10 or newer is required but was not found on PATH.
    echo Install Python from https://www.python.org/downloads/ and try again.
    pause
    exit /b 1
)

echo Checking for virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Creating one now...
    %PY_CMD% -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create the virtual environment.
        echo Please make sure Python is installed correctly and added to your system's PATH.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
)

echo.
echo Activating virtual environment...
call "venv\Scripts\activate"
if errorlevel 1 (
    echo ERROR: Failed to activate the virtual environment even after creation/check.
    pause
    exit /b 1
)

echo.
echo Checking and installing required Python libraries...
python check_libraries.py
if errorlevel 1 (
    echo WARNING: An error occurred while checking or installing libraries.
    echo The configurator will still attempt to start, but it may not function correctly.
    echo Please review any error messages above.
    pause
)

echo.
echo Starting the configurator...
set "PYTHONW=venv\Scripts\pythonw.exe"
if not exist "%PYTHONW%" set "PYTHONW=venv\Scripts\python.exe"
start "TenosAIConfigEditor" "%PYTHONW%" config_editor_main.py

echo.
echo Configurator launch initiated. If it did not appear, run this batch file
echo from a command prompt (cmd.exe) and choose the "python config_editor_main.py"
echo line suggested above to review any startup errors.
