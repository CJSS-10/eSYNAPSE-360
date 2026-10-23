# Decisiones de arquitectura (ADR)

Cada decisión que condiciona cómo se construye el sistema se registra aquí el mismo día que se toma, con su contexto, la decisión y lo que se descartó. Formato: `ADR-nnnn-titulo.md`. Una decisión no se edita: si cambia, se escribe una nueva que la reemplaza y se anota en la anterior.

| ADR | Decisión | Fecha | Estado |
|---|---|---|---|
| 0001 | Monolito modular en Django; el sistema operativo anterior (FastAPI) se traslada como diseño, no como código | 2026-10-10 | Vigente |
| 0002 | PostgreSQL desde la fase 3.0 y firma PAdES desde el primer certificado | 2026-10-10 | Vigente |
| 0003 | Orden de trabajo general con líneas por equipo y laboratorio; certificado por línea; series por tipo de servicio | 2026-10-10 | Vigente |
| 0004 | Módulos nuevos como apps Django propias; `esynapse_sig` se divide al migrar a PostgreSQL | 2026-10-10 | Vigente |
| 0005 | Una etapa cerrada es de solo lectura | 2026-10-13 | Vigente |
| 0006 | Organización y personal (áreas, puestos, trabajadores) como datos maestros únicos del núcleo | 2026-10-22 | Vigente |
| 0007 | Interfaz: alineación de tablas por tipo de dato (reemplaza la regla de tablas centradas), escala de severidad única y módulo estándar | 2026-10-23 | Vigente |

Las decisiones de negocio de la cadena operativa (D-01 a D-17) están en `../../PLAN_CADENA_OPERATIVA.md`.
