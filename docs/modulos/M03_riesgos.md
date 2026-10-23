# M3 · Riesgos y oportunidades

**App:** `riesgos` (app propia, ADR-0004) · **Estado:** construido en 0.6.0 (en validación) · **Pruebas:** `riesgos/tests/test_riesgos.py`
**Procedimiento:** Gestión de Riesgos y Oportunidades Ver. 00 (carpeta `PROCEDIMIENTOS SIG/`). **Formatos que replica:** Matriz de Riesgos y Oportunidades y Matriz de Oportunidades de Mejora.

## 1. Propósito

Identificar, analizar, valorar, tratar y hacer seguimiento a los riesgos y oportunidades del SIG (ISO 9001 6.1, ISO 14001 6.1, ISO 45001 6.1, NTP-ISO/IEC 17025 8.5 y 4.1.4 imparcialidad), y registrar las oportunidades de mejora con su decisión y eficacia (ISO 9001 10.1/10.3). Los riesgos de SST y los aspectos ambientales tienen metodología propia; se trasladan aquí solo cuando afectan los objetivos del SIG, indicando su origen.

## 2. Decisiones (César, 2026-10-21)

| Tema | Decisión |
|---|---|
| Categorías | Las 13 del formato (técnico-metrológico, operativo, imparcialidad, confidencialidad, cumplimiento, estratégico, comercial, financiero, proveedores, personal, TI, ambiental, SST). El procedimiento (que define 7) se corrige en su próxima versión. |
| Procesos | Del catálogo M7. Equivalencias de la carga: Alta Dirección → Gestión Estratégica; SIG → Sistema Integrado de Gestión; TI → Sistemas; Créditos, Facturación y Cobranzas → Facturación y Cobranzas; Logística → **Recepción de Equipos y/o Instrumentos** (subproceso nuevo de Metrología); Marketing → **Marketing** (proceso de soporte nuevo); Administración → Recursos Humanos. |
| Acciones | Varias acciones por riesgo u oportunidad, cada una con responsable, fechas, recursos y estado. En el PDF se listan dentro de la celda. |
| Valoración | Escala 1–5 × 1–5. Nivel: 1–3 No significativo · 4–7 Tolerado · 8–14 Moderado · 15–19 Importante · 20–25 Crítico. ¿Requiere acción?: riesgo desde 8; oportunidad desde 15 (8–14 «en cartera»). |
| Caja de control de los PDF | Versión 00 · 2026-01-23 · Elaborado ASIG · Revisado GSIG/GT · Aprobado GG; la lista maestra manda cuando el formato esté vinculado. |

## 3. Registros y reglas

**Contexto (FODA y partes interesadas):** fortalezas F-n, debilidades D-n, oportunidades O-n, amenazas A-n y partes interesadas; cada riesgo u oportunidad enlaza los elementos de contexto que lo originan.

**Riesgo / oportunidad (R-000 / O-000, correlativo único):**

| Etapa | Qué se registra | Reglas |
|---|---|---|
| Identificación y valoración inicial (borrador) | Proceso, tipo, categoría, fuente, fecha, actividad, descripción, causa, efecto, controles existentes, P×I (V×B) | Se registra en la matriz con «Registrar en la matriz»; después solo cambia por **revaloración** con motivo (queda el historial). |
| Tratamiento | Estrategia (riesgo: reducir, aceptar, evitar, compartir, remover; oportunidad: incrementar) y acciones | Si requiere acción: estrategia y al menos una acción, salvo «aceptar» con decisión documentada. Aceptar un riesgo Importante o Crítico exige la **firma del Gerente General**. |
| Seguimiento | Estado de cada acción: pendiente, en proceso, ejecutado (fecha y evidencia) | Acción vencida sin ejecutar: alerta y registro del incumplimiento como hallazgo. |
| Verificación de la eficacia | Valoración residual, fecha de verificación, evidencia | Solo con todas las acciones ejecutadas; fecha ≥ ejecución + 3 meses. Eficacia calculada: riesgo eficaz si el residual baja, oportunidad si sube; igual = sin cambio. No eficaz o sin cambio → **nuevo tratamiento** (el ciclo anterior queda en el historial). |
| Materialización | Fecha y descripción | Registra un hallazgo (riesgo materializado) para su acción correctiva. |
| Retiro | Motivo | El riesgo deja de aplicar; no se borra. |

Oportunidades «en cartera» (8–14): la Alta Dirección decide abordarlas o descartarlas (con motivo).

**Oportunidad de mejora (OM-000):** proceso, fuente, detectado por, fecha, descripción, situación que la motiva → decisión (se implementa / en evaluación / no se implementa, con justificación) → acción, responsable, fecha máxima → estado → eficacia (lograda, parcial, no lograda). En evaluación más de un año: alerta. Las observaciones y oportunidades de mejora de Hallazgos que se derivan a este módulo aparecen como pendientes de registrar.

**Revisiones de la matriz:** actualización (Área SIG) y supervisión del correcto llenado (Gerente Técnico, control independiente), con firma; alimentan la cabecera del PDF.

**Indicadores:** los de las hojas «Indicadores» de ambas matrices, mapa de calor y distribución por nivel y por origen.

## 4. Conexión con otros módulos

- **Procesos:** proceso del catálogo.
- **Hallazgos / Acciones correctivas:** materialización e incumplimiento de plazo generan hallazgo; observaciones y OdM derivadas llegan aquí.
- **Cambios:** origen «Riesgos identificados»; un cambio puede exigir actualizar la matriz.
- **Revisión por la dirección:** indicadores y oportunidades en cartera.

## 5. Criterios de aceptación

1. Código correlativo R/O/OM; nivel, ¿requiere acción? y eficacia se calculan igual que el formato.
2. No se registra en la matriz sin los datos de identificación y valoración; luego solo se revalora con motivo.
3. Riesgo que requiere acción: no se registra sin estrategia y acción (o aceptación documentada; firma del GG si es Importante o Crítico).
4. Verificación solo con acciones ejecutadas y fecha ≥ ejecución + 3 meses.
5. OM: «se implementa» exige acción, responsable y fecha; «no se implementa», justificación; eficacia solo con la acción ejecutada.
6. Carga inicial de la matriz y del registro de OM existentes.
7. Los dos PDF replican sus formatos.

## 6. API

| Ruta | Permiso | Qué hace |
|---|---|---|
| `/api/riesgos/` (GET, POST, PATCH, DELETE) | leer · crear · editar · eliminar | Matriz; filtros `tipo`, `proceso`, `categoria`, `nivel`, `situacion`, `vencidas=1`, `buscar`; PATCH solo en etapas abiertas; DELETE anula un borrador |
| `POST /api/riesgos/{id}/registrar/` | editar | Pasa a la matriz (valida identificación, valoración y tratamiento) |
| `POST .../agregar_accion/` · `editar_accion/` · `quitar_accion/` · `seguimiento_accion/` (multipart) · `registrar_incumplimiento/` | editar | Acciones de tratamiento |
| `POST .../aceptar_riesgo/` · `decidir_cartera/` | aprobar | Firma del GG; decisión de cartera |
| `POST .../verificar/` · `nuevo_tratamiento/` · `revalorar/` · `materializar/` · `retirar/` | editar | Eficacia y ciclo de vida |
| `GET /api/riesgos/catalogos/` · `indicadores/` · `hallazgos_derivados/` · `matriz_pdf/` | leer | Listas, indicadores, derivados de Hallazgos, PDF |
| `/api/oportunidades-mejora/` + `decidir/` · `seguimiento/` · `evaluar_eficacia/` · `matriz_pdf/` | crear · editar · leer | Matriz de oportunidades de mejora |
| `/api/contexto-riesgos/` | leer · crear · editar · eliminar | FODA y partes interesadas (DELETE = deja de estar vigente) |
| `/api/revisiones-riesgos/` + `actualizacion/` (editar) · `supervision/` (aprobar) | — | Revisiones de la matriz, con firma |
