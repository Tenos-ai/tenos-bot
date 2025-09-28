@echo off
setlocal

REM Ensure we are running from the repository root
cd /d %~dp0

REM Locate a Python 3 interpreter
set "PY_CMD="
where python >nul 2>&1 && set "PY_CMD=python"
if not defined PY_CMD (
    where py >nul 2>&1 && set "PY_CMD=py -3"
)

if not defined PY_CMD (
    echo ERROR: Python 3.10 or newer is required but was not found on PATH.
    echo Install Python from https://www.python.org/downloads/ and re-run this launcher.
    pause
    exit /b 1
)

set "INSTALLER=scripts\windows\install_and_launch.py"
if not exist "%INSTALLER%" (
    echo ERROR: Unable to locate %INSTALLER%.
    echo Please verify the repository was cloned completely.
    pause
    exit /b 1
)

echo Running Tenos.ai provisioning helper...
if /I "%PY_CMD%"=="py -3" (
    py -3 "%INSTALLER%" %*
) else (
    %PY_CMD% "%INSTALLER%" %*
)
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo The installer reported an error (exit code %EXIT_CODE%). Review the log above for details.
    pause
    exit /b %EXIT_CODE%
)

echo.
echo Tenos.ai Material configurator should now be running.
echo A shortcut named TenosAIConfigurator.lnk will appear here after a successful build.
pause
endlocal
