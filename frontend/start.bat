@echo off
setlocal

echo Starting frontend dev server (LAN accessible)...

where npm.cmd >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] npm not found. Please install Node.js first.
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo node_modules not found, installing dependencies...
    call npm.cmd install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

call npm.cmd run dev

endlocal
