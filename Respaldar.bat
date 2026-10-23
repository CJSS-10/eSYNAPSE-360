@echo off
chcp 65001 >nul
:: eSYNAPSE 360 - Respaldo de la base de datos y de los archivos del sistema
title eSYNAPSE 360 - Respaldo

echo ============================================================
echo   eSYNAPSE 360 - Respaldo
echo ============================================================
echo.
echo  Se copian: base de datos (db.sqlite3), archivos subidos (media)
echo  y certificados digitales (certificados).
echo.
echo  IMPORTANTE: cierra el sistema (ventana del backend) antes de
echo  respaldar, para que la base no este en uso.
echo.
pause

:: Carpeta con fecha y hora: backups\2026-10-10_1530
for /f "tokens=1-3 delims=/-. " %%a in ("%DATE%") do set FECHA=%%c-%%b-%%a
set HORA=%TIME:~0,2%%TIME:~3,2%
set HORA=%HORA: =0%
set DESTINO=%~dp0backups\%FECHA%_%HORA%

mkdir "%DESTINO%" 2>nul

echo [1/3] Base de datos...
copy /Y "%~dp0backend\db.sqlite3" "%DESTINO%\db.sqlite3" >nul && echo        OK || echo        NO SE ENCONTRO db.sqlite3

echo [2/3] Archivos subidos (media)...
robocopy "%~dp0backend\media" "%DESTINO%\media" /E /NFL /NDL /NJH /NJS /NP >nul
echo        OK

echo [3/3] Certificados digitales...
robocopy "%~dp0backend\certificados" "%DESTINO%\certificados" /E /NFL /NDL /NJH /NJS /NP >nul
echo        OK

:: Version del sistema respaldada (para saber con que version restaurar)
copy /Y "%~dp0backend\VERSION" "%DESTINO%\VERSION" >nul 2>nul

echo.
echo ============================================================
echo   Respaldo guardado en:
echo   %DESTINO%
echo.
echo   Copia esa carpeta a un disco externo o a la nube al menos
echo   una vez por semana. Para restaurar: reemplaza db.sqlite3,
echo   media y certificados por los de la carpeta de respaldo.
echo ============================================================
echo.
pause
