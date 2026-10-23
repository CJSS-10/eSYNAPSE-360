# M9 · Acciones Correctivas

**App:** `esynapse_sig` · **Estado:** **cerrado** en 0.2.15 (2026-10-20); acta de validación en `docs/validacion/M09_acta_2026-10-20.md`, por firmar · **Pruebas:** `tests/test_acciones_correctivas.py` (21) + cierre de NC en `tests/test_hallazgos.py`
**Procedimiento:** Gestión de No Conformidades y Acciones Correctivas (carpeta `PROCEDIMIENTOS SIG/`). **Formatos que replica:** Solicitud de Acción Correctiva y Seguimiento a Solicitudes de Acciones Correctivas y No Conformidades.

## 1. Propósito

Tratar las No Conformidades: evaluación de la necesidad de acción correctiva (6.4), análisis de causa con 5 porqués (6.5), aprobación del plan con verificador (6.6), implementación con evidencias (6.7), verificación de eficacia (6.8) y seguimiento (6.9). Cierra las NC del registro de hallazgos que trata.

## 2. Modelos

| Modelo | Para qué |
|---|---|
| `SolicitudAC` | La solicitud (`SAC-NN-AAAA`): NC de origen (`hallazgo`), procedencia, normas, personal/entidad auditora, auditor, auditado, requisito, descripción; significancia, extensión, ¿requiere AC?; 5 porqués y causa raíz; cambios al SIG y a la matriz de riesgos; responsable de la implementación, verificador; eficacia y cierre; `ciclo` y `ciclos_anteriores` (análisis no eficaces, no se sobrescriben) |
| `AccionSAC` | Corrección o acción correctiva: descripción, fecha propuesta, responsable, estado, verificación, evidencia, `ciclo`, `is_active` (baja lógica), `reaperturas` |

**Estados:** `registrada → en_analisis → en_implementacion → en_verificacion → cerrada_conforme` · `cerrada_sin_ac` (solo corrección) · no eficaz → vuelve a `en_analisis` con un ciclo nuevo.

## 3. API (`/api/sac/`)

| Acción | Operación | Regla |
|---|---|---|
| `POST` | crear | Toda SAC trata una NC: la elegida (sin otra SAC, de auditoría solo tras la reunión de cierre) o una nueva que se crea en Hallazgos con su clasificación y proceso |
| `PATCH` | editar | Solo en Registrada (procedencia, auditor, requisito, descripción, responsable); la NC de origen no cambia |
| `evaluar` | editar | Exige responsable de la implementación (6.3.3) |
| `registrar_analisis` | editar | En análisis |
| `agregar_accion` | editar | Acción correctiva solo en análisis; corrección en registro, análisis o implementación sin AC |
| `aprobar_plan` | aprobar | Causa raíz + al menos una AC del ciclo vigente + verificador |
| `editar_accion` / `quitar_accion` | editar | Acción pendiente del ciclo vigente con su etapa abierta |
| `completar_accion` | editar | En implementación; exige verificación; al completar todas pasa a verificación (o cierra si es solo corrección) |
| `reabrir_accion` | editar | Completada por error, con motivo, mientras la SAC está en implementación o en verificación |
| `verificar_eficacia` | editar | Lo hace el verificador designado o quien puede aprobar. Eficaz → cierra la SAC y sus NC; no eficaz → ciclo al historial y nuevo análisis |
| `pdf` | leer | Solicitud de Acción Correctiva |
| `seguimiento_pdf` | leer | Seguimiento (con los filtros del listado) |

## 4. Reglas

- La SAC muestra todas las NC que trata (la de origen y las ocurrencias sumadas desde Hallazgos).
- Etapa cerrada = solo lectura (ADR-0005) por etapas: registro, evaluación, análisis/acciones, implementación, verificación.
- Clasificación (columna del Seguimiento): tipo de la NC de origen + «AC» o «Solo corrección».
- La pantalla principal es la tabla de Seguimiento (mismas columnas del formato).
- (0.2.12) Verificación no eficaz: el nuevo ciclo empieza con el análisis en blanco (botón para partir del anterior); si se confirma el mismo análisis, pantalla y PDF dicen «se revisó y se confirma» en lugar de repetirlo.
- (0.2.13) Formato de 11 secciones (decisión de César): la causa raíz es la sección 7, aparte del análisis de causa (6); acciones correctivas 8, eficacia 9, actualizaciones 10, conformidad 11. La plantilla Excel oficial (Ver. 01) aún tiene 10: actualizarla con una nueva versión en la lista maestra.
- (0.2.13) La ficha muestra todas las secciones del formato en consulta. `fecha_registro` (editable en el registro; por defecto hoy; la NC creada la toma como fecha de detección). `verificado_por` = quien verificó la eficacia; es el responsable de la evaluación de la eficacia y de la conformidad en el PDF.
- (0.2.14) Correcciones y acciones correctivas se agregan en su sección (5 y 8) y se corrigen o quitan (`editar_accion`, `quitar_accion`; baja lógica `AccionSAC.is_active`) mientras están pendientes, son del ciclo vigente y su etapa sigue abierta (`AccionSAC.editable()`). «SIG integrado» heredado de una auditoría se guarda como ISO 9001 + 14001 + 45001 (`normas_de_sac`).
- (0.2.15) `completar_accion` exige verificación. `reabrir_accion` (motivo obligatorio) mientras la SAC está en implementación o en verificación (vuelve a implementación); historial en `AccionSAC.reaperturas`; `AccionSAC.reabrible()`. Seguimiento: fecha de actualización = última modificación real; tabla en Arial 11, hoja horizontal.

## 5. Criterios de aceptación

1. «Nueva SAC» sin elegir NC: pide clasificación y proceso; la NC aparece en Hallazgos en tratamiento.
2. Corregir el registro en Registrada; tras evaluar, el registro queda de solo lectura.
3. Evaluar sin responsable → bloqueado.
4. Verificación no eficaz: el análisis anterior queda en «Ciclos anteriores» y se pide una acción nueva para aprobar el plan.
5. Cerrar como eficaz: la SAC queda Cerrada conforme y sus NC cerradas.
6. PDF de la solicitud y PDF del seguimiento iguales a sus formatos.

## 6. Pendientes

- Firmar el acta de validación (`docs/validacion/M09_acta_2026-10-20.md`).
- Emitir la nueva versión de la plantilla de la solicitud (11 secciones) y reflejar la hoja horizontal del seguimiento; vincularlas en Configuración → Formatos impresos.
- Decidir si la justificación de la evaluación es obligatoria cuando la NC se trata solo con corrección (recomendado).
