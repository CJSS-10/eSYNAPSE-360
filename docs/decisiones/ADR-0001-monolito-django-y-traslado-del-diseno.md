# ADR-0001 · Monolito modular en Django; el sistema operativo anterior se traslada como diseño

**Fecha:** 2026-10-10 · **Estado:** vigente

## Contexto

Existían dos proyectos: eSYNAPSE 360 (Django + DRF + React, módulos del SIG construidos: núcleo, M6, M8, M9, M10, M12, M13) y `Sistema Metrindust` (FastAPI + SQLAlchemy + PostgreSQL + Mantine, fases 0 y 1 del flujo comercial, con un diseño de procesos P01–P11 de alta calidad). César decidió unificar todo en eSYNAPSE.

## Decisión

1. eSYNAPSE 360 es el único sistema. Un solo repositorio, una sola base de datos, organizado por módulos (apps Django).
2. Del proyecto anterior se adoptan el **modelo de procesos y puertas (DD-01)**, las máquinas de estado explícitas, los eventos de dominio, el versionado de maestros por vigencia y la práctica "cada puerta tiene una prueba". **No se reutiliza su código.**
3. Las puertas que exigen "técnico autorizado" y "patrón vigente" se resuelven consultando M12 y M13 directamente.

## Alternativas descartadas

- Mantener los dos sistemas e integrarlos por API: duplica usuarios, laboratorios, autorizaciones y equipos, y rompe la trazabilidad SIG ↔ operación.
- Migrar eSYNAPSE a FastAPI: tirar siete módulos funcionando por una preferencia de framework.

## Consecuencias

- La cadena operativa se construye en Django siguiendo `PLAN_CADENA_OPERATIVA.md`.
- Hay que incorporar a eSYNAPSE patrones que no tenía: estados con transiciones validadas, eventos append-only, maestros versionados (ver `02_arquitectura_y_convenciones.md`).
