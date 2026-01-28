@echo off
REM Batch file untuk menjalankan translate_xliff.py dengan virtual environment

echo ===================================
echo XLIFF Translator Runner
echo ===================================

REM Aktifkan virtual environment dan jalankan script
call "%~dp0venv\Scripts\activate.bat"

echo.
echo Checking dependencies...
pip show deepl >nul 2>&1 && echo [OK] deepl installed || (echo [MISSING] deepl - installing... && pip install deepl)
pip show requests >nul 2>&1 && echo [OK] requests installed || (echo [MISSING] requests - installing... && pip install requests)

echo.
echo Running translate_xliff.py...
echo ===================================
python "%~dp0translate_xliff.py"

echo.
echo ===================================
echo Done!
pause
