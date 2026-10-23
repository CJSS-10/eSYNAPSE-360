# ADR-0002 · PostgreSQL desde la fase 3.0 y firma PAdES desde el primer certificado

**Fecha:** 2026-10-10 · **Estado:** vigente

## Contexto

El desarrollo usa SQLite. Al construir órdenes de trabajo, certificados y facturas se necesitan transacciones reales, secuencias atómicas para correlativos y restricciones de integridad; SQLite ya se corrompió una vez por accesos concurrentes. Para los certificados, eSYNAPSE ya cuenta con firma PAdES (endesive) construida en M6.

## Decisión

1. **PostgreSQL** es la base de datos del sistema a partir de la fase 3.0 (antes de construir la OT). En el PC de desarrollo se instala PostgreSQL local; el flujo de trabajo (iniciar, actualizar, probar, respaldar) se mantiene, cambiando `db.sqlite3` por `pg_dump`.
2. Los certificados de calibración se firman con **PAdES** (firma digital con certificado personal del firmante) desde el primer certificado emitido por el sistema. No se arranca con firma visual + hash.

## Alternativas descartadas

- Seguir en SQLite hasta producción: riesgo de rehacer lógica de correlativos y transacciones.
- Firma visual + hash primero: ya existe PAdES y un certificado de calibración se verifica ante terceros sin acceso al sistema.

## Consecuencias

- Cada firmante autorizado necesita su certificado digital (`.pfx`) y su contraseña de firma en el servidor.
- `settings.py` pasa a leer la base de datos y los secretos de variables de entorno.
- El respaldo del PC cambia a `pg_dump` (se actualizará `Respaldar.bat`).
