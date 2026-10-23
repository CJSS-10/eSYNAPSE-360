@echo off
chcp 65001 >nul
:: eSYNAPSE 360 - Aplica las actualizaciones de la base de datos (migraciones)
title eSYNAPSE 360 - Aplicar actualizacion

cd /d "%~dp0backend"
call venv\Scripts\activate
set /p VERSION=<VERSION

echo ============================================================
echo   eSYNAPSE 360 - Aplicar actualizacion   (version %VERSION%)
echo ============================================================
echo.
echo  IMPORTANTE: cierra la ventana del backend (servidor) antes de
echo  continuar. Aplicar actualizaciones con el servidor encendido
echo  puede danar la base de datos.
echo.
pause

python manage.py migrate

echo.
echo ------------------------------------------------------------
echo  Si arriba ves lineas con "OK" (o "No migrations to apply"),
echo  la actualizacion se aplico correctamente.
echo  Abre el sistema con "Iniciar eSYNAPSE 360.bat".
echo ------------------------------------------------------------
echo.
pause
