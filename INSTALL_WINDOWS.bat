@echo off
cd /d "%~dp0"
py -3 scripts\install_usa_rankings_in_kpis.py
if errorlevel 1 (
 echo INSTALL FAILED - check the error above. No existing application code changed.
 pause
 exit /b 1
)
python -m compileall -q company_kpi_metrics.py usa_fundamental_rankings_ui.py
if errorlevel 1 (
 echo Python syntax check failed
 pause
 exit /b 1
)
echo SUCCESS. Commit and Push origin in GitHub Desktop.
pause
