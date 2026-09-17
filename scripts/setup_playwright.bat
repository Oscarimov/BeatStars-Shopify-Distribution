@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo   BeatStars-Shopify Tool - Playwright setup
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on PATH.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    echo ^(check "Add python.exe to PATH" during install^) then run this again.
    pause
    exit /b 1
)

echo [1/3] Installing Python dependencies from requirements.txt...
python -m pip install --upgrade pip >nul
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo [ERROR] pip install failed. See the output above.
    pause
    exit /b 1
)

echo.
echo [2/3] Installing the Chromium browser for Playwright...
python -m playwright install chromium
if errorlevel 1 (
    echo [ERROR] "playwright install chromium" failed. See the output above.
    pause
    exit /b 1
)

echo.
echo [3/3] Verifying the browser actually launches...
python "%~dp0_verify_playwright.py"
if errorlevel 1 (
    echo.
    echo The first install looks corrupted or incomplete ^(this can happen with
    echo network issues or antivirus interference^). Retrying with a clean
    echo reinstall...
    python -m playwright install chromium --force
    python "%~dp0_verify_playwright.py"
    if errorlevel 1 (
        echo.
        echo ============================================================
        echo   STILL FAILING
        echo ============================================================
        echo This is very likely caused by the Microsoft Visual C++
        echo Redistributable ^(x64^) being missing or out of date on this PC.
        echo Chromium needs it to start, regardless of Python/Playwright.
        echo.
        echo 1. Download and install it from:
        echo    https://aka.ms/vs/17/release/vc_redist.x64.exe
        echo 2. REBOOT your PC ^(the installer often needs a restart to apply^)
        echo 3. Run this setup script again
        echo ============================================================
        pause
        exit /b 1
    )
)

echo.
echo ============================================================
echo   Setup complete! You can now run the tool.
echo ============================================================
pause
