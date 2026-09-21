@echo off
REM Starts the Django backend and Vite frontend together in separate windows.
REM Verifies the backend actually comes up before starting the frontend, so
REM a broken backend gives a clear reason instead of a silent "can't reach
REM the server" error later inside the app.

setlocal enabledelayedexpansion
set ROOT_DIR=%~dp0

if not exist "%ROOT_DIR%backend\.env" (
  echo backend\.env not found - copying from .env.example
  copy "%ROOT_DIR%backend\.env.example" "%ROOT_DIR%backend\.env" >nul
)
if not exist "%ROOT_DIR%frontend\.env" (
  echo frontend\.env not found - copying from .env.example
  copy "%ROOT_DIR%frontend\.env.example" "%ROOT_DIR%frontend\.env" >nul
)

if not exist "%ROOT_DIR%backend\venv" (
  echo No backend\venv found - set it up first:
  echo   cd backend
  echo   python -m venv venv
  echo   venv\Scripts\activate
  echo   pip install -r requirements.txt
  exit /b 1
)
if not exist "%ROOT_DIR%frontend\node_modules" (
  echo frontend\node_modules not found - installing dependencies now...
  pushd "%ROOT_DIR%frontend"
  call npm install
  popd
)

echo Starting backend on http://localhost:8000 ...
start "Truvanta Backend" cmd /k "cd /d %ROOT_DIR%backend && venv\Scripts\activate && python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"

echo Waiting for backend to come up...
set BACKEND_UP=0
for /l %%i in (1,1,20) do (
  set "STATUS="
  curl -s -o nul -w "%%{http_code}" http://localhost:8000/api/auth/me/ > "%TEMP%\truvanta_check.txt" 2>nul
  set /p STATUS=<"%TEMP%\truvanta_check.txt"
  if not "!STATUS!"=="" (
    if not "!STATUS!"=="000" (
      set BACKEND_UP=1
      goto :backend_ready
    )
  )
  timeout /t 1 /nobreak >nul
)

:backend_ready
if "%BACKEND_UP%"=="0" (
  echo.
  echo The backend did not come up within 20 seconds.
  echo Check the "Truvanta Backend" window for the actual error.
  echo Common causes: dependencies not installed (pip install -r requirements.txt
  echo inside backend\venv^), a migration error, or port 8000 already in use by
  echo something else. See RUNNING.md ^> Troubleshooting for more.
  exit /b 1
)
echo Backend is up.

echo Starting frontend on http://localhost:5173 ...
start "Truvanta Frontend" cmd /k "cd /d %ROOT_DIR%frontend && npm run dev"

echo Both servers are starting in separate windows. Close those windows to stop them.
