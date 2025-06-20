@echo off
REM Change directory to the script's own directory
cd /d %~dp0

echo Activating virtual environment...
call venv\Scripts\activate
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment. Check if 'venv' folder exists and is correct.
    pause
    goto :eof
)

echo.
echo Checking and installing required libraries...
python check_libraries.py
if %ERRORLEVEL% neq 0 (
    echo WARNING: An error occurred while checking or installing libraries.
    echo The configurator will still attempt to start, but it may not function correctly.
    echo Please review any error messages above from check_libraries.py.
    pause
)

echo.
echo Starting the configurator...
REM Use start "title" pythonw.exe to launch without a console window that stays open.
REM The first empty quotes "" are for the title of the new window if it were a console app;
REM for pythonw, it's often not strictly needed but is good practice with start.
start "TenosAIConfigEditor" /B pythonw.exe config_editor_main.py

REM The /B flag for start attempts to start the application without creating a new window,
REM but pythonw.exe itself is what prevents the console from showing for the Python script.
REM If pythonw.exe successfully launches the GUI, this batch file will continue and exit.

echo.
REM This message might flash briefly or not be seen if the launch is quick.
echo Configurator launch initiated. If it did not appear, run this batch file
echo from a command prompt (cmd.exe) without the 'start /B pythonw.exe' part
echo (i.e., just 'python config_editor_main.py') to see any errors.
REM No pause here, so the window closes.