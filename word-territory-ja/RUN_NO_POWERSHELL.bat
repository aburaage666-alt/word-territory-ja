@echo off
setlocal
cd /d "%~dp0"
echo === Word Territory JP v28 FULL ENGINE - NO POWERSHELL ===
echo This script uses Python, not PowerShell.

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py RUN_APPLY_AND_TEST_JP_V28_FULL_ENGINE_NO_POWERSHELL.py
) else (
  where python >nul 2>nul
  if %ERRORLEVEL%==0 (
    python RUN_APPLY_AND_TEST_JP_V28_FULL_ENGINE_NO_POWERSHELL.py
  ) else (
    echo Python launcher not found. Please install Python or make sure py/python is available.
    pause
    exit /b 1
  )
)

set RC=%ERRORLEVEL%
echo.
if %RC%==0 (
  echo DONE: success. Upload the generated bot_match_results/summary/json files.
) else (
  echo STOPPED: validation failed or an error occurred. Upload *_FAILED files if they were created.
)
echo.
pause
exit /b %RC%
