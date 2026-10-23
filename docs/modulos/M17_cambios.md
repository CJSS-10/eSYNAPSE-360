# M17 · Cambios

**App:** `cambios` (app propia, ADR-0004) · **Estado:** construido en 0.5.0; cambio temporal en vigor en 0.5.1; validado el 2026-10-22 (0.8.5), acta por firmar · **Pruebas:** `cambios/tests/test_cambios.py`
**Procedimiento:** Control de Cambios Ver. 00 (carpeta `PROCEDIMIENTOS SIG/`). **Formatos que replica:** Solicitud de Cambios, Planificación de Cambios y Seguimiento de Cambios.

## 1. Propósito

Gestionar de forma planificada y controlada todo cambio temporal o permanente que pueda afectar al SIG: identificarlo, evaluar su viabilidad e impactos (calidad, ambiente, SST, parte técnica de la NTP-ISO/IEC 17025, imparcialidad, requisitos legales y de acreditación), aprobarlo, planificarlo, implementarlo, comunicarlo, verificar su eficacia, revertirlo si corresponde y cerrarlo (ISO 9001 6.3, ISO 14001 8.1, ISO 45001 8.1.3, NTP-ISO/IEC 17025 8.5 y 6.x según el cambio).

## 2. Decisiones (César, 2026-10-21)

| Tema | Decisión |
|---|---|
| Quién aprueba | **Todo cambio lo aprueba el Gerente General**, sea mayor o menor. |
| Clasificación | *Aceptado:* el sistema registra la prioridad del formato (alta / media / baja) y la clasificación del procedimiento (mayor / menor). La clasificación decide si la planificación detallada es obligatoria. |
| Plan de ejecución | *Aceptado:* cambio menor → basta el plan de la Solicitud; cambio mayor o técnico → Planificación de Cambios obligatoria (el procedimiento la exige para los cambios técnicos). |
| Cambio temporal (2026-10-21) | Al confirmar la eficacia pasa a **«Temporal en vigor»** y se cierra al registrar su fin (fecha, qué se restituyó, evidencia). Prórroga con motivo, firmada por el Gerente General. Volverlo permanente = nueva solicitud que lo referencia. La reversión de la verificación es solo por ineficacia. |
| Caja de control de los PDF | Versión y fecha de cada formato (versión **00**); la lista maestra manda cuando el formato esté vinculado. |

## 3. Etapas (etapa cerrada = solo lectura, ADR-0005)

| Etapa | Estado | Qué se registra | Quién |
|---|---|---|---|
| 1. Solicitud | Solicitado | Código, solicitante, proceso solicitante (catálogo), fecha, prioridad, descripción, justificación, origen interno / externo con su fuente | Responsable de área o cualquier usuario |
| 2. Evaluación | En evaluación | Factibilidad técnica, aspectos operativos y financieros; procesos afectados (catálogo); beneficios; riesgos e impactos (calidad, ambiente, SST, técnico 17025, imparcialidad, acreditación); controles; consecuencias de no realizarlo; clasificación mayor / menor; ¿técnico?; ¿afecta clientes o alcance acreditado?; responsable y equipo evaluador | Gerente SIG y áreas involucradas |
| 3. Resolución | En aprobación → Aprobado / Rechazado | Aprobado o rechazado con firma (contraseña) y fecha. Rechazado: reevaluación (vuelve a evaluación con motivo) o archivo | **Gerente General** |
| 4. Planificación | En planificación | Tipo (previsto / no previsto; temporal con fecha de reversión / permanente); fuente u origen; responsable y equipo de implementación; plazo; actividades con responsable, recursos y plazo | Responsable de área |
| 5. Implementación | En implementación | Avance y evidencia de cada actividad; fotos antes, durante y después; documentos actualizados (vínculo a la versión en Documentos) | Equipo de implementación |
| 6. Comunicación | (dentro de 5) | A quién (personal, clientes, proveedores, contratistas, otras partes), fecha, medio, resumen, evidencia. Si afecta clientes o actividades acreditadas, antes de implementar | Responsable de área |
| 7. Eficacia | En verificación | ¿Se implementó? ¿Fue eficaz? Verificación de resultado, calidad, validez de resultados, riesgos, conformidad legal y de acreditación. No eficaz → reversión parcial o total y/o acción correctiva | Gerente SIG |
| 8. Cierre | Cerrado | Cerrado por y fecha; solo con actividades completas, eficacia evidenciada, documentos y matrices actualizados y acciones derivadas cerradas | Gerente SIG |

## 4. Conexión con otros módulos

- **Procesos:** proceso solicitante y procesos afectados del catálogo; al aprobar el cambio, cada proceso afectado recibe el aviso «ficha por revisar».
- **Documentos:** los documentos actualizados se enlazan a su versión; el cierre exige que estén vigentes (la versión anterior rige hasta la aprobación de la nueva).
- **Acciones correctivas:** un cambio puede originarse en una solicitud de acción correctiva; un cambio no eficaz puede generar una.
- **Competencia y Equipos:** si el cambio es técnico (personal, patrones, software, métodos, condiciones ambientales), la planificación detallada es obligatoria.

## 5. Criterios de aceptación

1. Código correlativo por año; proceso solicitante del catálogo.
2. No se evalúa sin solicitud completa; no se resuelve sin evaluación completa (riesgos, controles, procesos afectados, clasificación).
3. Solo el Gerente General aprueba o rechaza, con contraseña; rechazo con motivo; reevaluación vuelve a evaluación.
4. Cambio mayor o técnico no pasa a implementación sin Planificación completa; temporal exige fecha de reversión.
5. Si afecta clientes o el alcance acreditado, no se implementa sin comunicación registrada.
6. No se cierra sin actividades completas, eficacia verificada, documentos vigentes y acciones derivadas cerradas.
7. Aprobar crea los avisos «ficha por revisar» de los procesos afectados.
8. Cada etapa cerrada queda de solo lectura; reabrir con motivo.
9. Los tres PDF replican sus plantillas.

## 6. API (`/api/cambios/`)

| Ruta | Permiso | Qué hace |
|---|---|---|
| `GET /` · `POST /` · `PATCH /{id}/` | leer · crear · editar | Lista (filtros `estado`, `abiertos=1`, `anio`, `buscar`), alta y edición; el servidor rechaza campos de etapas cerradas o futuras |
| `DELETE /{id}/` | eliminar | Anula (solo en «solicitado»; borrado lógico) |
| `GET catalogos/` | leer | Listas del formulario (prioridades, orígenes y motivos, impactos, fuentes, criterios, etc.) |
| `POST {id}/enviar_evaluacion/` · `enviar_aprobacion/` | editar | Avance de etapa con validación de lo obligatorio |
| `POST {id}/resolver/` | aprobar | `{aprobado, comentarios, password}`; aprobar genera los avisos a los procesos afectados |
| `POST {id}/reevaluar/` · `archivar/` | editar | Tras un rechazo, con motivo |
| `POST {id}/agregar_actividad/` · `editar_actividad/` · `quitar_actividad/` | editar | Plan de ejecución (en evaluación o planificación) |
| `POST {id}/iniciar_implementacion/` · `completar_actividad/` · `pasar_a_verificacion/` · `cerrar/` | editar | Implementación y cierre |
| `POST {id}/comunicar/` · `agregar_foto/` · `quitar_foto/` | editar | Comunicación y registro fotográfico (multipart) |
| `POST {id}/prorrogar/` | aprobar | Cambio temporal: `{fecha_nueva, motivo, password}` |
| `POST {id}/registrar_fin_temporal/` | editar | Multipart `{fecha, detalle, evidencia}`; cierra el cambio temporal en vigor |
| `POST {id}/nuevo_cambio_permanente/` | crear | Nueva solicitud que vuelve permanente un cambio temporal en vigor |
| `POST {id}/reabrir/` | aprobar | Con motivo (vuelve a verificación; el fin temporal registrado queda en el historial de reaperturas) |
| `GET {id}/pdf/` · `{id}/planificacion_pdf/` · `seguimiento_pdf/` | leer | Los tres formatos |

## 7. Pantalla

Menú SIG Core → **Cambios**: tabla con las columnas del Seguimiento, filtros y «Imprimir seguimiento»; «Nueva solicitud». El detalle muestra el avance por etapas y, en cada estado, solo el formulario de la etapa abierta; las cerradas se leen. La barra inferior ofrece la acción que cierra la etapa (aprobar y rechazar se firman con contraseña).
