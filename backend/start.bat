@echo off
setlocal

echo Starting backend server (LAN accessible)...

if exist ".venv\Scripts\activate.bat" (
    echo Detected venv: .venv
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo Detected venv: venv
    call "venv\Scripts\activate.bat"
) else (
    echo [WARNING] No .venv or venv found, using system Python.
)

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

endlocal
