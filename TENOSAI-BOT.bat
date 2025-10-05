@echo off
REM Change directory to the script's own directory to ensure paths are correct
cd /d %~dp0

echo Checking for virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Creating one now...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create the virtual environment.
        echo Please make sure Python is installed correctly and added to your system's PATH.
        pause
        goto :eof
    )
    echo Virtual environment created successfully.
)

echo.
echo Activating virtual environment...
call venv\Scripts\activate
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate the virtual environment even after creation/check.
    pause
    goto :eof
)

echo.
echo Checking and installing required Python libraries...
python check_libraries.py
if %ERRORLEVEL% neq 0 (
    echo WARNING: An error occurred while checking or installing libraries.
    echo The configurator will still attempt to start, but it may not function correctly.
    echo Please review any error messages above.
    pause
)

echo.
echo Starting the configurator...
REM Use start "title" pythonw.exe to launch without a console window that stays open.
start "TenosAIConfigEditor" /B pythonw.exe config_editor_main.py

echo.
REM This message might flash briefly or not be seen if the launch is quick.
echo Configurator launch initiated. If it did not appear, run this batch file
echo from a command prompt (cmd.exe) without the 'start /B pythonw.exe' part
echo (i.e., just 'python config_editor_main.py') to see any startup errors.
