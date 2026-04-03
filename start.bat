@echo off
setlocal

cd /d "%~dp0"

:: Check .env
if not exist .env (
    echo ERROR: .env not found.
    echo Copy .env.author.example to .env and add your ANTHROPIC_API_KEY.
    pause
    exit /b 1
)

:: Download cloudflared if missing
if not exist cloudflared.exe (
    echo Downloading cloudflared...
    curl -L "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -o cloudflared.exe
    if errorlevel 1 (
        echo Failed to download cloudflared. Check your internet connection.
        pause
        exit /b 1
    )
)

echo Starting Author Agent Network...
echo.

:: Start Flask in a new window
start "Flask App" /min python web\app.py

:: Wait for Flask to be ready
echo Waiting for app to start...
:wait
timeout /t 1 /nobreak >nul
curl -sf http://localhost:5000 >nul 2>&1
if errorlevel 1 goto wait

echo App is running.
echo.
echo Starting Cloudflare tunnel...
echo Your public URL will appear below -- open it in any browser.
echo ---------------------------------------------------------------
echo Press Ctrl+C to stop the tunnel (close the Flask window too).
echo.

cloudflared.exe tunnel --url http://localhost:5000 --no-autoupdate 2>&1 | findstr /i "trycloudflare https://"
