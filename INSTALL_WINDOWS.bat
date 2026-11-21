@echo off
cd /d "%~dp0"
py -3 scripts\enable_usa_research_navigation.py
if errorlevel 1 (
  echo ERROR: Check messages above. No files were changed if anchors were not found.
  pause
  exit /b 1
)
pause
