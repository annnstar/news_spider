@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo Running spider with --limit 5 ...
".venv\Scripts\python.exe" spider.py --limit 5
echo.
echo Done. Check data\books.csv
pause
