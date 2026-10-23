# M8 · Hallazgos

**App:** `esynapse_sig` · **Estado:** ajustado al procedimiento de no conformidades y acciones correctivas (0.2.9), pendiente de validación en pantalla · **Pruebas:** `tests/test_hallazgos.py` (9) + registro desde auditoría en `test_auditorias*.py`
**Procedimiento:** Gestión de No Conformidades y Acciones Correctivas (carpeta `PROCEDIMIENTOS SIG/`). El procedimiento no tiene un formato propio de hallazgo: la NC se describe en la Solicitud de Acción Correctiva; sus dos formatos (Solicitud y Seguimiento) se imprimen desde M9.

## 1. Propósito

Registro único de no conformidades, observaciones y oportunidades de mejora, vengan de donde vengan (auditoría interna o externa, inspección, queja, seguimiento, indicador, riesgo), y su derivación: las NC a una solicitud de acción correctiva (M9), las observaciones y oportunidades de mejora a Riesgos y Oportunidades (M3).

## 2. Modelo

`Hallazgo`: `codigo`, `tipo` (NC mayor, NC menor, observación, oportunidad de mejora), `fuente`, `proceso`, `descripcion`, `requisito`, `lugar`, `fecha_deteccion`, `evidencia`, `responsable` (solo registros anteriores: desde 0.8.20 el responsable del tratamiento se designa al evaluar la solicitud de acción correctiva o en Riesgos y oportunidades / mejora continua, y el hallazgo lo muestra desde ahí; «Por designar» mientras tanto), `requiere_ac`, `tratamiento` (`accion_correctiva` / `riesgos_oportunidades`), `auditoria` (si nació en M10), `sac` (solicitud que la trata), `reclasificaciones` (historial con motivo), `cerrado_por`, `fecha_cierre`, `comentarios_cierre`, `is_active`.

- **Código:** `NC-NNN-AAAA`, `OBS-NNN-AAAA`, `ODM-NNN-AAAA`, correlativo por prefijo y año. El año es el del programa de auditoría si nació en una auditoría; si no, el de la fecha de detección.
- **Estados:** NC: `registrado → en_tratamiento` (al generar o sumarse a una solicitud) `→ cerrado` (cuando la solicitud se cierra). Observación / oportunidad de mejora: `derivado` (a Riesgos y Oportunidades). `en_analisis` y `reabierto` quedan solo para registros anteriores.

## 3. API (`/api/hallazgos/`)

| Acción | Operación | Regla |
|---|---|---|
| `PATCH` | editar | Solo con la etapa de registro abierta; el tipo no se edita aquí |
| `reclasificar` | editar | Tipo nuevo + motivo obligatorio; nuevo código si cambia el prefijo; queda en el historial. No aplica a hallazgos de auditoría |
| `generar_sac` | crear | NC sin solicitud; crea la solicitud precargada (procedencia, normas, descripción, requisito) |
| `sac_abiertas` | leer | Solicitudes abiertas, primero las del mismo requisito o proceso (posible duplicado) |
| `vincular_sac` | editar | Suma la NC como nueva ocurrencia a una solicitud abierta |
| `resumen` | leer | Tablero |
| `DELETE` | eliminar | Baja lógica |

## 4. Reglas (procedimiento de no conformidades)

- **Toda NC** se registra en una solicitud de acción correctiva (`requiere_ac`); en la solicitud se evalúa si basta una corrección.
- **No se duplican solicitudes:** una NC del mismo problema se suma a la solicitud abierta.
- **Observaciones y oportunidades de mejora** no se tratan aquí: quedan derivadas a Riesgos y Oportunidades.
- **Etapa cerrada = solo lectura (ADR-0005):** el registro se corrige mientras la NC no se haya derivado (o, en observaciones y oportunidades de mejora, mientras Riesgos no las reciba). Los hallazgos de auditoría se corrigen desde la auditoría, en su etapa. El servidor rechaza el cambio nombrando el campo y el motivo.
- **NC de auditoría:** se deriva después de la reunión de cierre (antes aún se reclasifican o descartan en la auditoría).
- **Cierre:** al cerrarse la solicitud (eficaz, o solo corrección) se cierran todas sus NC con la referencia a la solicitud.
- **Mis tareas:** el responsable ve las NC registradas que aún no se derivan.

## 5. Criterios de aceptación

1. Registrar una NC menor manual; corregir su lugar; generar la SAC; intentar corregir la descripción → rechazado nombrando el campo y la SAC.
2. Registrar otra NC del mismo requisito; «Sumar a SAC abierta» la sugiere como posible mismo problema; sumarla; la SAC muestra ambas NC.
3. Registrar una observación: queda «Derivado a riesgos y oportunidades» y no ofrece SAC.
4. Reclasificar una NC menor a observación con motivo: cambia de código y queda el historial.
5. Cerrar la SAC como eficaz: ambas NC quedan cerradas con la referencia a la SAC.

## 6. Pendientes

- Conectar las observaciones y oportunidades de mejora con M3 Riesgos cuando se construya.
- Al construir M18 (Quejas) y M16 (Trabajo no conforme) alimentarán este módulo con sus fuentes.
- Validación en pantalla y acta.
