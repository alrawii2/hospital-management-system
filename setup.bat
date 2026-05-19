@echo off
echo ======================================
echo Hospital Management System - Setup
echo ======================================

SET SCRIPT_DIR=%~dp0
SET FRONTEND_DIR=%SCRIPT_DIR%Frontend\hospital-frontend

echo.
echo Installing backend dependencies...
pip install -r "%SCRIPT_DIR%requirements.txt"

echo.
echo Setting up database...
cd /d "%SCRIPT_DIR%"
python manage.py migrate

echo.
echo Creating test users...
python manage.py shell < seed.py

echo.
echo Starting Django backend...
start "Django Backend" python manage.py runserver

echo.
echo Installing frontend dependencies...
cd /d "%FRONTEND_DIR%"
call npm install

echo.
echo Starting React frontend...
start "React Frontend" npm run dev

timeout /t 3 /nobreak > nul

echo.
echo Opening browser...
start http://localhost:5173

echo.
echo ======================================
echo Website is ready!
echo Go to: http://localhost:5173
echo Username: patient1 / Password: test123
echo ======================================
pause