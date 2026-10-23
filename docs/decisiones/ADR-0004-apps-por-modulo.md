# ADR-0004 · Módulos nuevos como apps Django propias; `esynapse_sig` se divide al migrar a PostgreSQL

**Fecha:** 2026-10-10 · **Estado:** vigente

## Contexto

Todos los módulos del SIG construidos hasta la fase 2 viven en una sola app, `esynapse_sig`: `views.py` supera las 2.700 líneas y `ficha_pdf.py` las 2.100. Funciona, pero cada cambio obliga a navegar archivos enormes y mezcla módulos sin relación. La cadena operativa (fase 3) añadirá al menos cuatro módulos grandes.

## Decisión

1. Desde la fase 3.0, **cada módulo nuevo es una app Django propia** con sus modelos, vistas, serializers, PDFs, migraciones y pruebas: `comercial`, `logistica`, `operaciones` (OT y certificados), `finanzas`. Los maestros compartidos (Cliente, Laboratorio, Series) van en `maestros` o en `core`.
2. `esynapse_sig` **no recibe módulos nuevos**. Se dividirá en apps por módulo (`documentos`, `hallazgos`, `acciones_correctivas`, `auditorias`, `competencia`, `equipos`) **junto con la migración a PostgreSQL**, cuando la base de desarrollo se reconstruye de todos modos y el movimiento de tablas entre apps se hace una sola vez.
3. Mientras tanto, cualquier cambio en `esynapse_sig` mantiene la estructura actual; no se mezclan las dos operaciones.

## Alternativas descartadas

- Dividir ahora sobre SQLite: implica renombrar tablas o migraciones de estado dos veces (ahora y al cambiar de motor), con riesgo y sin beneficio inmediato.
- Dejar todo en una app para siempre: insostenible con la fase 3.

## Consecuencias

- La estructura objetivo queda documentada en `02_arquitectura_y_convenciones.md`.
- La migración a PostgreSQL (fase 3.0) incluye la división y las pruebas existentes deben seguir en verde después de ella.
