@echo off
setlocal
REM Opens a REAL, plain Chrome window on a dedicated profile - no automation,
REM no debugging flags, nothing. Log into Shopify here by hand (captcha/2FA
REM will display normally, since nothing is automating this window).
REM
REM Once you're on the Shopify admin dashboard, CLOSE this Chrome window,
REM then run the tool (main.py / single_upload.py / debug_digital_downloads.py)
REM as usual - it will reuse this same profile, already logged in.

set "PROFILE_DIR=%~dp0chrome_profile"
set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"

if exist "%CHROME_EXE%" goto :launch

set "CHROME_EXE=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if exist "%CHROME_EXE%" goto :launch

echo Google Chrome not found. Install it from https://www.google.com/chrome/
pause
exit /b 1

:launch
echo Opening Chrome on a dedicated profile for Shopify login...
echo Profile folder: %PROFILE_DIR%
echo.
echo Log into Shopify normally in the window that opens, then CLOSE Chrome
echo and run the tool.

start "" "%CHROME_EXE%" --user-data-dir="%PROFILE_DIR%" "https://admin.shopify.com"
