@echo off
REM ========================================================================
REM  UnRAR Setup for Windows
REM  Automatically downloads and sets up UnRAR tool
REM ========================================================================

echo.
echo ========================================================================
echo   UNRAR SETUP FOR WINDOWS
echo ========================================================================
echo.

REM Check if tools folder exists
if not exist "tools" (
    echo [*] Creating tools\ folder...
    mkdir tools
)

REM Check if unrar.exe already exists
if exist "tools\unrar.exe" (
    echo [OK] UnRAR.exe is already installed!
    echo      Location: tools\unrar.exe
    echo.
    echo [*] Testing UnRAR...
    tools\unrar.exe
    if errorlevel 0 (
        echo [OK] UnRAR is working correctly!
    )
    echo.
    pause
    exit /b 0
)

echo [*] UnRAR.exe not found in tools\
echo [*] Starting download...
echo.

REM Use PowerShell to download UnRAR
echo [*] Downloading UnRAR from rarlab.com...
echo     This may take a moment...
echo.

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $url = 'https://www.rarlab.com/rar/unrarw32.exe'; $output = 'tools\unrar_setup.exe'; Write-Host '[*] Downloading...' -ForegroundColor Yellow; try { (New-Object System.Net.WebClient).DownloadFile($url, $output); Write-Host '[OK] Download complete!' -ForegroundColor Green } catch { Write-Host '[ERROR] Download failed!' -ForegroundColor Red; Write-Host $_.Exception.Message -ForegroundColor Red; exit 1 }}"

if errorlevel 1 (
    echo.
    echo [ERROR] Download failed!
    echo.
    echo ========================================================================
    echo   MANUAL INSTALLATION REQUIRED
    echo ========================================================================
    echo.
    echo Please follow these steps:
    echo   1. Visit: https://www.rarlab.com/rar_add.htm
    echo   2. Download "UnRAR for Windows"
    echo   3. Extract UnRAR.exe
    echo   4. Place it in: tools\unrar.exe
    echo   5. Re-run this script to verify
    echo.
    pause
    exit /b 1
)

REM Check if download was successful
if not exist "tools\unrar_setup.exe" (
    echo [ERROR] Download failed - file not found!
    goto manual_install
)

echo.
echo ========================================================================
echo   EXTRACTION REQUIRED
echo ========================================================================
echo.
echo [*] Downloaded UnRAR installer to: tools\unrar_setup.exe
echo.
echo Next steps:
echo   1. Extract UnRAR.exe from the installer
echo   2. Place it in: tools\unrar.exe
echo   3. Re-run this script to verify
echo.
echo [*] Opening installer location...
start explorer "tools"

echo.
echo Press any key when you've completed the extraction...
pause >nul

REM Check again after user extraction
if exist "tools\unrar.exe" (
    echo.
    echo [OK] UnRAR.exe found!
    echo [*] Testing UnRAR...
    tools\unrar.exe
    echo.
    echo [OK] Setup complete!
    echo.
) else (
    echo.
    echo [!] UnRAR.exe not found in tools\
    echo     Please make sure you extracted it to the correct location.
    echo.
)

echo ========================================================================
echo   SETUP COMPLETE
echo ========================================================================
echo.
echo You can now run the BeatStars-Shopify Tool!
echo.
pause
exit /b 0

:manual_install
echo.
echo ========================================================================
echo   MANUAL INSTALLATION REQUIRED
echo ========================================================================
echo.
echo Please follow these steps:
echo   1. Visit: https://www.rarlab.com/rar_add.htm
echo   2. Download "UnRAR for Windows"  
echo   3. Extract UnRAR.exe
echo   4. Place it in: tools\unrar.exe
echo   5. Re-run this script to verify
echo.
pause
exit /b 1