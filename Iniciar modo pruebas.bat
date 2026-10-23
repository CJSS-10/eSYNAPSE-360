@echo off
chcp 65001 >nul
:: eSYNAPSE 360 - MODO PRUEBAS
:: Levanta el sistema sobre una COPIA de la base (backend\db_pruebas.sqlite3) y de
:: los archivos subidos (backend\media_pruebas). Lo que se registre aqui no toca
:: los datos reales. Usa otros puertos (8001 y 5174): puede correr al mismo
:: tiempo que el sistema normal.
title eSYNAPSE 360 - Modo pruebas

cd /d "%~dp0backend"
call venv\Scripts\activate
set ESYNAPSE_MODO=pruebas
set ESYNAPSE_API=http://127.0.0.1:8001

set /p VERSION=<VERSION
echo ============================================================
echo   eSYNAPSE 360  -  version %VERSION%  -  MODO PRUEBAS
echo ============================================================
echo.

set RENOVAR=S
if exist db_pruebas.sqlite3 (
  echo  Ya existe una copia de pruebas.
  set RENOVAR=N
  set /p RENOVAR=" Renovarla desde la base real? Se pierde lo registrado en pruebas (S/N): "
)
if /I "%RENOVAR%"=="S" (
  echo  Copiando la base real...
  python -c "import sqlite3; o=sqlite3.connect('db.sqlite3'); d=sqlite3.connect('db_pruebas.sqlite3'); o.backup(d); d.close(); o.close()"
  if errorlevel 1 (
    echo  No se pudo copiar la base. Revise que exista backend\db.sqlite3.
    pause
    exit /b 1
  )
  echo  Copiando los archivos subidos...
  robocopy media media_pruebas /MIR /NFL /NDL /NJH /NJS /NP >nul
  echo  Copia lista.
  echo.
)

python manage.py migrate --check >nul 2>&1
if errorlevel 1 (
  echo  Aplicando actualizaciones de base de datos a la copia de pruebas...
  python manage.py migrate
  echo.
)

echo  Iniciando backend 8001 y pantalla 5174 en modo pruebas...
start "eSYNAPSE 360 - PRUEBAS Backend 8001" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate && python manage.py runserver 8001"
start "eSYNAPSE 360 - PRUEBAS Frontend 5174" cmd /k "cd /d "%~dp0frontend" && npm run dev -- --port 5174 --strictPort"

timeout /t 5 /nobreak > nul
start http://localhost:5174

exit
