@echo off
REM Batch file untuk setup/recreate virtual environment

echo ===================================
echo Virtual Environment Setup
echo ===================================

cd /d "%~dp0"

REM Check if venv exists
if exist "venv" (
    echo [INFO] Virtual environment already exists.
    set /p choice="Recreate venv? (y/n): "
    if /i "!choice!"=="y" (
        echo Removing old venv...
        rmdir /s /q venv
    ) else (
        goto INSTALL
    )
)

echo Creating new virtual environment...
python -m venv venv

:INSTALL
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo.
echo ===================================
echo Setup complete!
echo.
echo Dependencies installed:
pip list
echo.
echo To run the translator, use: run_translate.bat
echo ===================================
pause
