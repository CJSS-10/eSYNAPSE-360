@echo off
:: eSYNAPSE 360 - Inicia backend (Django) y frontend (React) en dos ventanas
title eSYNAPSE 360 - Lanzador

echo Iniciando eSYNAPSE 360...

start "eSYNAPSE 360 - Backend (Django)" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate && python manage.py runserver"

start "eSYNAPSE 360 - Frontend (React)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 5 /nobreak > nul
start http://localhost:5173

exit
