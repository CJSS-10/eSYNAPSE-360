# Formatos del SIG implementados en el sistema

Registro de las plantillas del sistema de gestión que eSYNAPSE 360 reproduce como PDF.

## De dónde salen código, versión, fecha y siglas (caja de control)

Desde la versión 0.2.5 la fuente única es la **lista maestra (M6)**. En **Configuración → Formatos impresos** cada PDF del sistema se vincula con su documento de la lista maestra; la cabecera del PDF imprime entonces el código del documento, el número de su **versión vigente**, su fecha de vigencia (o aprobación) y las **siglas de cargo** de quien elaboró, revisó y aprobó esa versión (campo "sigla del cargo" de cada usuario). Al aprobar una nueva versión del formato en Documentos, todos los PDF la imprimen sin tocar nada más.

Orden de resolución (`control_formato` en `backend/esynapse_sig/ficha_pdf.py`):

1. Documento vinculado con versión vigente → lista maestra (origen "Lista maestra").
2. Sin vínculo → tabla de respaldo `CONTROL_FORMATOS` con los valores leídos de las plantillas (origen "Respaldo"); es lo que muestran las tablas de abajo.
3. Sin entrada en la tabla → valores globales y siglas de respaldo de Configuración (origen "Por defecto").

**Cuando una plantilla cambie de versión**: (1) registrar la nueva versión en Documentos (M6) y aprobarla; si el formato ya está vinculado, no hay que hacer más para la caja de control. (2) Reemplazar el archivo en `PROCEDIMIENTOS SIG/`. (3) Revisar si cambió la **estructura** (campos, columnas) y ajustar el generador. (4) Actualizar la fila de abajo y `CONTROL_FORMATOS`, y registrar en `CHANGELOG.md`. Si el cambio afecta registros del laboratorio, exige nueva acta de validación (`docs/validacion/`).

## Auditorías internas — procedimiento SIG-PRO-16

| Código | Formato | Versión | Fecha | Elaborado / Revisado / Aprobado | Generador | Origen de datos |
|---|---|---|---|---|---|---|
| SIG-PRO-16-r01 | Programa anual de auditorías | 02 | 2026-01-12 | ASIG / GSIG/GT / GG | `generar_programa_anual_pdf` | Programa + auditorías (clase, requisitos por norma, meses, observaciones) |
| SIG-PRO-16-r02 | Plan de auditoría interna | 01 | 2026-01-12 | ASIG / GSIG/GT / GG | `generar_plan_auditoria_pdf` | Auditoría (datos del laboratorio desde Configuración, cronograma de entrevistas) |
| SIG-PRO-16-r03 | Acta de reunión de apertura | 00 | 2025-01-10 | ASIG / **GSIG** / GG | `generar_acta_pdf` | Acta tipo apertura |
| SIG-PRO-16-r04 | Informe de auditoría interna | 00 | 2025-01-10 | ASIG / **GSIG** / GG | `generar_informe_auditoria_pdf` | Auditoría + hallazgos (M8) + participantes de actas |
| SIG-PRO-16-r05 | Acta de reunión de cierre | 00 | 2025-01-10 | ASIG / **GSIG** / GG | `generar_acta_pdf` | Acta tipo cierre |
| SIG-PRO-16-r06 | Lista de verificación NTP ISO/IEC 17025 | 00 | 2026-01-12 | ASIG / GSIG/GT / GG | `generar_lista_verificacion_pdf` | Lista con norma 17025 |
| SIG-PRO-16-r07 | Lista de verificación ISO 9001, 14001, 45001 | 00 | 2026-01-12 | ASIG / GSIG/GT / GG | `generar_lista_verificacion_pdf` | Lista integrada (contenido de autoría propia: la plantilla viene en blanco) |

## Competencia técnica — procedimiento MET-PRO-12

| Código | Formato | Versión | Fecha | Elaborado / Revisado / Aprobado | Generador |
|---|---|---|---|---|---|
| MET-PRO-12-r01 | Entrenamiento y supervisión de actividades | 00 | 2026-02-11 | ASIG / GSIG/GT / GG | `generar_entrenamiento_pdf` |
| MET-PRO-12-r02 | Autorización del personal | 00 | 2026-02-11 | ASIG / GSIG/GT / GG | `generar_autorizacion_pdf` |
| MET-PRO-12-r03 | Entrevista de seguimiento al personal | 00 | 2026-02-11 | ASIG / GSIG/GT / GG | `generar_seguimiento_pdf` |

## Control del equipamiento — procedimiento MET-PRO-04

Todos en versión **00** del **2026-02-11**, siglas ASIG / GSIG/GT / GG (valores globales `VERSION_FORMATO`, `FECHA_FORMATO`, `FIRMAS` y siglas de Configuración).

| Código | Formato | Generador |
|---|---|---|
| MET-PRO-04-r01 | Hoja de vida | `generar_ficha_pdf` |
| MET-PRO-04-r02 | Inventario de equipos | `generar_inventario_pdf` |
| MET-PRO-04-r03 | Programa de mantenimiento, calibración, comprobaciones y caracterización | `generar_programa_pdf` |
| MET-PRO-04-r04 | Cartas de trazabilidad | `generar_carta_trazabilidad_pdf` |
| MET-PRO-04-r05 / r06 / r07 | Informes de mantenimiento, comprobación intermedia y caracterización | bitácoras e informes (`generar_bitacora_pdf`) |
| MET-PRO-04-r08 | Intervalo de calibración | `generar_intervalo_pdf` |
| MET-PRO-04-r09 | Control de salida y entrada del equipamiento | movimientos (`generar_bitacora_pdf`) |

## Pendientes de implementar (plantillas disponibles, sin generador)

| Código | Formato | Módulo previsto |
|---|---|---|
| MET-PRO-02-r01 a r06 | Condiciones ambientales, visitas, orden y limpieza, estabilidad eléctrica, luminosidad, mapeo térmico | Instalaciones (fase 2, pendiente de planificar) |

## Observaciones sobre las plantillas

- Las actas y el informe (r03, r04, r05) llevan revisado **GSIG** (sin GT), distinto del resto del procedimiento. Se respeta tal cual.
- En el formato r02 (plan), la tercera columna de requisitos del cronograma de entrevistas dice "ISO 14001:2015" repetido; el sistema imprime **ISO 45001:2018**, que es lo que corresponde. Corregir en la plantilla.
- La plantilla r07 no trae contenido; las 83 filas de la lista integrada son autoría propia (migración `0037`) y conviene que Calidad las revise y las incorpore a la plantilla oficial.
