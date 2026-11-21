@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 scripts\install_research_navigation.py
) else (
  python scripts\install_research_navigation.py
)
if errorlevel 1 (
  echo.
  echo Installation FAILED. Copy this entire folder's contents into your local repository root first.
  pause
  exit /b 1
)
echo.
echo SUCCESS. Open GitHub Desktop, review, COMMIT TO MAIN, then PUSH ORIGIN.
pause
