# Operación del sistema en el PC de desarrollo

Mientras el sistema no esté en un servidor, todo (desarrollo, pruebas y datos) vive en el PC de César, en `D:\eSYNAPSE 360`. Estos son los procedimientos. Todos se ejecutan con doble clic en los `.bat` de la carpeta raíz.

## Iniciar

`Iniciar eSYNAPSE 360.bat`

1. Muestra la versión instalada.
2. Verifica si hay actualizaciones de base de datos pendientes; si las hay, **las aplica antes de arrancar** (el servidor aún no corre, es seguro).
3. Abre dos ventanas: backend (Django, puerto 8000) y frontend (React, puerto 5173), y el navegador en `http://localhost:5173`.

Para cerrar el sistema: cerrar las dos ventanas negras (o Ctrl+C en cada una).

## Actualizar (después de una entrega)

`Aplicar actualizacion.bat`

1. **Cerrar primero el sistema.** Aplicar migraciones con el servidor encendido puede dañar la base (ocurrió el 24-06-2026).
2. Ejecutar el `.bat`; debe mostrar `OK` por cada migración o `No migrations to apply`.
3. Iniciar normalmente.

Si al abrir el sistema no deja entrar con una contraseña correcta, casi siempre es una migración pendiente: cerrar, aplicar, iniciar.

## Probar

`Probar.bat` ejecuta las pruebas automáticas (reglas de negocio, permisos, PDF). Usa una base de datos temporal: **no toca tus datos**. Debe terminar en `OK`. Si aparece `FAIL` o `ERROR`, reportarlo antes de seguir usando el sistema. Conviene correrlo después de cada actualización.

## Respaldar

`Respaldar.bat` copia a `backups\AAAA-MM-DD_HHMM\`:

- `db.sqlite3` (toda la información del sistema),
- `media\` (archivos subidos: documentos, certificados de equipos, evidencias),
- `certificados\` (certificados digitales `.pfx` para firmar),
- `VERSION` (para saber con qué versión restaurar).

**Cerrar el sistema antes de respaldar.** Recomendación: respaldo **diario** al terminar de trabajar y copia **semanal** de la carpeta `backups` a un disco externo o a la nube. Un respaldo en el mismo disco no protege contra una falla del disco.

**Restaurar**: cerrar el sistema; reemplazar `backend\db.sqlite3`, `backend\media` y `backend\certificados` por los de la carpeta de respaldo; iniciar. Si la versión del respaldo es anterior a la instalada, el lanzador aplicará las migraciones faltantes.

## Publicar (carpeta limpia y Git)

`Sincronizar carpeta limpia.bat` copia a `eSYNAPSE 360 GitHub\` el backend, el frontend, `docs\` y los archivos de raíz, excluyendo todo lo que no debe publicarse (bases de datos, media, certificados, respaldos, `venv`, `node_modules`, scripts de diagnóstico, `Guia.txt`). Después, en esa carpeta: revisar cambios y hacer commit.

## Restablecer la contraseña de un usuario

En una consola, dentro de `D:\eSYNAPSE 360\backend` (nota el `/d`, necesario para cambiar de disco):

```
cd /d "D:\eSYNAPSE 360\backend"
venv\Scripts\activate
python manage.py changepassword NOMBRE_DE_USUARIO
```

## Qué no hacer

- No ejecutar dos veces el lanzador (dos servidores sobre la misma base).
- No editar `db.sqlite3` con herramientas externas mientras el sistema corre.
- No borrar `backend\migrations\*`: son el historial de la base de datos.
- No subir a GitHub `Guia.txt`, `.pfx`, `db.sqlite3` ni `media`.

## Cuando pase a servidor (futuro)

Se añadirán: PostgreSQL con `pg_dump` automático, ambientes separados (pruebas y producción), HTTPS, variables de entorno para secretos y respaldo fuera de sede. Está planificado en `PLAN_CADENA_OPERATIVA.md`, fase 3.0.
