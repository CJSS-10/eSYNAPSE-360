@echo off
chcp 65001 >nul
:: eSYNAPSE 360 - Inicia backend (Django) y frontend (React) en dos ventanas.
:: Antes de arrancar verifica si hay actualizaciones de base de datos
:: pendientes y las aplica (el servidor aun no esta corriendo, es seguro).
title eSYNAPSE 360 - Lanzador

cd /d "%~dp0backend"
call venv\Scripts\activate

set /p VERSION=<VERSION
echo ============================================================
echo   eSYNAPSE 360  -  version %VERSION%
echo ============================================================
echo.

python manage.py migrate --check >nul 2>&1
if errorlevel 1 (
  echo  Hay actualizaciones de base de datos pendientes. Aplicando...
  python manage.py migrate
  echo.
  echo  Actualizacion aplicada.
  echo.
)

echo  Iniciando backend y frontend...
start "eSYNAPSE 360 - Backend (Django) v%VERSION%" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate && python manage.py runserver"
start "eSYNAPSE 360 - Frontend (React)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 5 /nobreak > nul
start http://localhost:5173

exit
