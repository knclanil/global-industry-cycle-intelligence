@echo off
setlocal
cd /d "%~dp0"
echo === USA Graph Ranking Integration ===
if not exist "regional_rotation_graph.py" (
  echo ERROR: regional_rotation_graph.py is missing here.
  echo Copy the CONTENTS of this ZIP into the MAIN GitHub repository folder first.
  pause
  exit /b 1
)
if not exist "usa_graph_membership_ranks.py" (
  echo ERROR: usa_graph_membership_ranks.py is missing here.
  pause
  exit /b 1
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 scripts\apply_usa_graph_ranks.py
) else (
  python scripts\apply_usa_graph_ranks.py
)
if errorlevel 1 (
  echo ERROR: Patch not applied. See above output.
  pause
  exit /b 1
)
echo.
echo IMPORTANT: Open GitHub Desktop now.
echo Commit regional_rotation_graph.py AND usa_graph_membership_ranks.py.
echo Then click Push origin to update Streamlit.
pause
