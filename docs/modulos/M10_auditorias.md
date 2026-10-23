# M10 · Auditorías Internas

**App:** `esynapse_sig` · **Estado:** cerrado (0.2.8), acta de validación pendiente de firma · **Pruebas:** `test_auditorias.py` (ciclo, hallazgos, listas, 6 PDF)
**Formatos que replica:** procedimiento SIG-PRO-16 — r01 Programa anual · r02 Plan · r03 Acta de apertura · r04 Informe · r05 Acta de cierre · r06 Lista de verificación 17025 · r07 Lista de verificación integrada 9001/14001/45001 (archivos en `PROCEDIMIENTOS SIG/SIG-PRO-16 Auditoría Interna/`).

## 1. Propósito

Programa anual, planificación, ejecución con listas de verificación, registro de hallazgos (en M8), informe y cierre de auditorías internas del sistema integrado, con los seis formatos impresos 1:1.

## 2. Modelos

| Modelo | Para qué |
|---|---|
| `ProgramaAuditoria` | Programa anual como **documento controlado**: `anio`, estado `borrador → aprobado (solo lectura) → en_modificacion → aprobado`, `revision` (sube en cada reaprobación), `aprobado_por` / `fecha_aprobacion`, `modificado_por` / `fecha_modificacion` / `motivo_modificacion`. Aprobado bloquea alta/baja de auditorías y los campos del programa (`CAMPOS_PROGRAMA`: proceso, tipo, clase, normas, cláusulas, mes programado, observaciones); el plan y la reprogramación siguen editables |
| `Auditoria` | `codigo` `AI-NN-AAAA`, programa, tipo (programada/extraordinaria), **clase** (interna / externa: INACAL, certificadora), normas (incluye `sig_integrado`), **requisitos por norma** (cláusulas a auditar, texto por norma, como las 4 columnas del programa), **observaciones del programa**, objetivo, alcance, criterios, documentos de referencia, áreas, **cronograma de entrevistas** (JSON: fecha, hora, área, requisitos por norma, modalidad, TIC, auditor, auditado), observaciones del plan, modalidad, auditor líder, **mes programado** (original, no se sobrescribe) y **mes reprogramado**, fecha programada, fechas inicio/fin, motivo de reprogramación, estado, **lugar**, **personas entrevistadas**, fortalezas, debilidades, conclusiones, fecha de informe |
| `EquipoAuditoria` | Integrantes: usuario interno o externo, rol (líder, auditor, experto, observador), cargo (se hereda del usuario) |
| `ActaAuditoria` | Apertura o cierre: participantes (nombre, condición equipo auditor/auditado, cargo), tres secciones de texto, archivo firmado |
| `ListaVerificacion` / `ItemVerificacion` | Checklist por norma generado del catálogo: cláusula, descripción, documento de referencia, evaluación (evidencia), resultado C/NC/OBS/NA |
| `RequisitoNorma` | Catálogo de cláusulas/preguntas por norma. La integrada 9001·14001·45001 tiene 201 filas (36 títulos de cláusula y 165 preguntas); cada pregunta empieza con la norma y el numeral exacto que la exige; su Nro. es un correlativo y los títulos de cláusula conservan su numeral (`ItemVerificacion.referencias_norma()` da la norma y numeral reales para hallazgos e informe) |

**Estados:** `programada → planificada → apertura → en_ejecucion → conclusiones → reunion_cierre → en_informe → cerrada`.

**Impresos (0.2.7):** los siete PDF se compararon hoja por hoja con sus plantillas y usan los anchos de columna reales del Excel. Actas e informe toman la fecha de la reunión o del informe, no la de impresión. Correcciones deliberadas respecto a la plantilla: "Representante" y "Observador(es)" sin la errata del original.

## 3. API

`/api/programas-auditoria/`: `aprobar` (editar; exige al menos una auditoría; **candado**: sin permiso de aprobar queda pendiente; desde "en modificación" sube la revisión), `abrir_modificacion` (editar; motivo obligatorio; solo desde aprobado), `programa_pdf` (leer; imprime la línea de revisión). `PATCH`/`DELETE` del programa y alta/baja/edición de campos del programa en sus auditorías responden 400 mientras esté aprobado.
`/api/solicitudes-auditoria/`: bandeja del candado (`aprobar`, `devolver`, `rechazar`, `reenviar`, `pendientes_count`, `mis_devueltas_count`).

`/api/auditorias/`:

| Acción | Operación | Precondición |
|---|---|---|
| `planificar` | editar | objetivo, alcance, un auditor líder en el equipo y al menos una entrevista; lo aprueba el líder o un aprobador |
| `iniciar` | editar | planificada |
| `reprogramar` | editar | motivo y nuevo mes obligatorios; conserva el mes programado original |
| `agregar_integrante` / `quitar_integrante` | editar | un solo integrante con rol líder (interno o externo; el segundo se rechaza); el campo `auditor_lider` lo refleja y no se edita directamente; **independencia**: si la persona pertenece al área o laboratorio auditado, la respuesta trae `aviso` (no bloquea; observadores exentos) |
| `registrar_acta` | editar | tipo apertura/cierre, participantes, secciones |
| `generar_lista` | editar | norma válida; no se duplica |
| `evaluar_item` | editar | resultado, documento de referencia, evidencia |
| `registrar_hallazgo` | crear | solo en ejecución/informe; crea Hallazgo (M8); NC mayor → requiere AC |
| `terminar_ejecucion` / `validar_hallazgos` | editar | ejecución → conclusiones → reunión de cierre (validar exige cero ítems pendientes y conclusiones) |
| `cerrar` | editar | conclusiones obligatorias; **candado**: sin permiso de aprobar queda como solicitud pendiente (aprobar / devolver / rechazar; el solicitante corrige conclusiones y reenvía) |
| `plan_pdf`, `acta_pdf?tipo=`, `lista_pdf?norma=`, `informe_pdf` | leer | |

## 4. Reglas de negocio

- Los hallazgos se registran en M8, nunca en una tabla propia.
- El auditor líder se define solo en el equipo auditor (rol líder, uno por auditoría). Plan, actas, informe y pantalla toman ese nombre (`Auditoria.nombre_lider()`). Pruebas: `tests/test_auditorias_lider.py`.
- Criterios de auditoría = normas seleccionadas + criterios adicionales (manual, procedimientos).
- Lista de verificación integrada (9001·14001·45001) separada de la de 17025, como en el procedimiento. Si se audita una sola de esas normas, su lista (catálogo con bloque `lista`) se deriva de la integrada: solo sus preguntas, su numeral y sus títulos; Sistema Integrado y normas sueltas no se combinan en una auditoría. Pruebas: `PruebasListasPorNorma`. La de 17025 es el formato completo: 175 filas con el texto íntegro de cada numeral y 8 ítems de seguimiento (bloque `seguimiento`), más NOTAS y Anexo 1 fijos en el PDF.
- Datos de empresa, dirección y responsable del SIG salen de Configuración.
- El código `AI-NN-AAAA` lleva el año del programa anual; sigue a la auditoría si se mueve de programa antes de ejecutarse. En ejecución o cerrada no cambia de programa.
- Programa anual aprobado = solo lectura; "Modificar programa" lo reabre con motivo y al reaprobar sube la revisión.

### Secuencia y etapas (procedimiento de auditoría interna + ADR-0005)

| Paso | Estado | Qué se hace | Cierra con | Luego queda |
|------|--------|-------------|------------|-------------|
| 1 Plan | Programada | Datos del programa (clase, normas, cláusulas, mes), objetivo, alcance, criterios, documentos, fecha de elaboración, cronograma, modalidad, equipo auditor | Aprobar y comunicar plan (líder o aprobador; exige cronograma) | Solo lectura |
| 2 Documentos de trabajo | Planificada | Preparar lista de verificación (opcional) y documento de referencia por ítem | Iniciar ejecución | Ítems fijos |
| 3 Reunión de apertura | Reunión de apertura | Acta de apertura (participantes y 3 secciones) | Registrar acta → En ejecución | Acta inmutable |
| 4 Ejecución | En ejecución | Evaluar ítems (evidencia, C/NC/OBS/NA), registrar hallazgos | Terminar ejecución | Evaluación fija |
| 5 Conclusiones | Conclusiones | Reclasificar, corregir o descartar hallazgos; conclusiones de la auditoría (obligatorias) | Validar hallazgos | Hallazgos y conclusiones fijos |
| 6 Reunión de cierre | Reunión de cierre | Acta de cierre | Registrar acta → En informe | Acta inmutable |
| 7 Informe | En informe | Lugar, entrevistados, fortalezas, debilidades | Entregar informe y cerrar (candado de aprobación) | — |
| Cerrada | Cerrada | Consulta y PDF | — | Todo solo lectura |

Trazabilidad: todo ítem evaluado No cumple u Observación queda "pendiente de clasificar" hasta que origina un hallazgo (nuevo o existente, vínculo `ItemVerificacion.hallazgo`) o se descarta con motivo (`motivo_descarte`); `validar_hallazgos` exige cero pendientes. Reprogramar (desviación con motivo) se permite en Programada y Planificada. Hallazgos: NC mayor y menor → acción correctiva; observación y oportunidad de mejora → riesgos y oportunidades (`tratamiento`). El servidor rechaza cualquier cambio fuera de su etapa nombrando la etapa y el campo; la API expone `etapas_abiertas` y la pantalla muestra una etapa a la vez. Pruebas: `tests/test_auditorias_etapas.py` (ayudante `tests/flujo_auditoria.py`).

## 5. Criterios de aceptación (para el acta de validación)

1. Crear programa 2026 y una auditoría con "Sistema Integrado"; planificar con equipo; iniciar.
2. Generar la lista integrada (201 filas; cada pregunta con su referencia ISO en negrita), evaluar 3 ítems con documento de referencia y evidencia; PDF r07 muestra las columnas del formato.
3. Registrar acta de apertura con participantes; PDF r03 marca condición con X y muestra las 4 secciones.
4. Registrar un hallazgo NC mayor; aparece en Hallazgos con "requiere AC".
5. Generar informe y cerrar; PDF r04 con todas las secciones; PDF r02 con cronograma de entrevistas completo.
7. Secuencia: recorrer los 7 pasos con una auditoría real; comprobar que cada paso muestra solo su contenido, que los pasos anteriores se consultan en solo lectura, que sin acta de apertura no se registran hallazgos, que en Conclusiones se reclasifica y descarta, y que tras el acta de cierre los hallazgos no cambian.
6. Programa anual (PDF r01): una auditoría interna reprogramada muestra marca azul en el mes original (fila Programado) y en el nuevo (fila Reprogramado); una externa muestra marca amarilla; las cuatro columnas de normas traen las cláusulas; observaciones a la derecha; cabecera con elaborado/aprobado y leyenda de colores.

## 6. Pendientes

- Firmar el acta de validación `docs/validacion/M10_acta_2026-10-16.md`.
- Mejoras registradas en `PENDIENTES.md` (no bloquean el uso): representante del área auditada desde las actas con respaldo en el cronograma; áreas/procesos y fecha programada editables después de crear; baja lógica al quitar un integrante; conexión de observaciones y oportunidades de mejora con M3 Riesgos.

**Estado:** módulo **cerrado** en 0.2.8 (2026-10-16). 54 pruebas automáticas propias (`test_auditorias.py`, `test_auditorias_etapas.py`, `test_auditorias_candado.py`, `test_auditorias_lider.py`).
