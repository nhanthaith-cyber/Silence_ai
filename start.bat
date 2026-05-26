@echo off
echo ====================================================
echo   AI Customer Service Agent - Khoi dong he thong
echo ====================================================
echo.

set PYTHON=C:\Users\NEALAKADY\AppData\Local\Programs\Python\Python314\python.exe
set NODE_PATH=C:\Program Files\nodejs
set BACKEND_DIR=%~dp0backend
set FRONTEND_DIR=%~dp0frontend

:: Chay seed data (chi lan dau)
if not exist "%BACKEND_DIR%\cs_agent.db" (
    echo [0/2] Tao du lieu mau...
    "%PYTHON%" "%BACKEND_DIR%\seed_data.py"
    echo.
)

:: Chay Backend
echo [1/2] Khoi dong Backend (FastAPI - port 8000)...
start "CS Agent Backend" cmd /k "title Backend Server && set PATH=%NODE_PATH%;%PATH% && cd /d "%BACKEND_DIR%" && "%PYTHON%" -m uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

:: Chay Frontend  
echo [2/2] Khoi dong Frontend (Next.js - port 3000)...
start "CS Agent Frontend" cmd /k "title Frontend Server && set PATH=%NODE_PATH%;%PATH% && cd /d "%FRONTEND_DIR%" && npm run dev"

echo.
echo ====================================================
echo   He thong dang khoi dong...
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Frontend: http://localhost:3000
echo ====================================================
echo.
echo Dang cho 5 giay roi mo trinh duyet...
timeout /t 5 /nobreak >nul
start http://localhost:3000
