@echo off
chcp 65001 >nul
:: eSYNAPSE 360 - Ejecuta las pruebas automaticas del backend
title eSYNAPSE 360 - Pruebas automaticas

echo ============================================================
echo   eSYNAPSE 360 - Pruebas automaticas
echo   (usan una base de datos temporal; no tocan tus datos)
echo ============================================================
echo.

cd /d "%~dp0backend"
call venv\Scripts\activate
python manage.py test core esynapse_sig quejas procesos cambios riesgos legal sst organizacion
set RESULTADO=%ERRORLEVEL%

echo.
echo ------------------------------------------------------------
if "%RESULTADO%"=="0" (
  echo  TODAS LAS PRUEBAS PASARON. El sistema esta consistente.
) else (
  echo  HAY PRUEBAS FALLIDAS. Revisa arriba el detalle (FAIL / ERROR)
  echo  y reportalo antes de seguir trabajando sobre el sistema.
)
echo ------------------------------------------------------------
echo.
pause
