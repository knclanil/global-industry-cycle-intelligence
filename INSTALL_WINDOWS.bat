@echo off
cd /d "%~dp0"
python scripts\install_usa_graph_rankings.py
if errorlevel 1 (
  echo ERROR: install failed. No source was changed if anchor was missing.
  pause
  exit /b 1
)
echo.
echo Done. Commit regional_rotation_graph.py and usa_graph_membership_ranks.py in GitHub Desktop.
pause
