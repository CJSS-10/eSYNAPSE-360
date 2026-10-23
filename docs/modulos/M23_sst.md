# M23 · Seguridad y Salud en el Trabajo

**App:** `sst` (app propia, ADR-0004) · **Estado:** 0.8.0 (IPERC, ATS), 0.8.1 (ATS en campo), 0.8.3 (alineación con Organización), 0.8.4 (incidentes, accidentes, enfermedades y estadísticas) y 0.8.6 (inspecciones y monitoreos) construidos, en validación · **Pruebas:** `sst/tests/test_sst.py`, `test_eventos.py`, `test_inspecciones.py`
**Procedimiento:** Identificación de Peligros, Evaluación de Riesgos y Controles Ver. 02 (carpeta `PROCEDIMIENTOS SIG/`). **Formatos que replica:** Matriz IPERC y Análisis de Trabajo Seguro.

## 1. Propósito

Identificar los peligros de cada actividad y puesto, evaluar sus riesgos y definir controles por jerarquía (ISO 45001 6.1.2 y 8.1.2, Ley 29783 art. 57), y analizar antes de iniciar los trabajos no rutinarios o de riesgo (ATS).

## 2. Plan de entregas (César, 2026-10-22)

| Versión | Contenido |
|---|---|
| **0.8.0** | Catálogo de puestos de trabajo · Matriz IPERC (carga del Excel) · ATS · PDF de ambos |
| **0.8.1** | ATS en campo: formato de Metrindust o del cliente, ATS tipo por servicio, envío a campo, recepción con el ATS firmado adjunto y revisión de SST (decisión de César del 2026-10-22) |
| 0.8.2 | Organización y personal en el núcleo (ADR-0006): los puestos de SST pasan al catálogo único |
| 0.8.3 | SST alineado con Organización: ejecutantes del ATS desde Trabajadores, responsables de controles como puestos, filtro por área, riesgos del trabajador |
| 0.8.4 | Incidentes, accidentes y enfermedades ocupacionales (investigación → hallazgo / acción correctiva) |
| 0.8.6 | Inspecciones y monitoreos de agentes (0.8.5 fue la entrega de saneamiento: modo pruebas) |
| 0.8.7 | EPP (catálogo, matriz por puesto, entrega firmada por el trabajador con PIN, reposición, devolución) y vigilancia médica (exámenes médicos ocupacionales, aptitud, próximos exámenes) |
| 0.8.8 | Comité SST (resultado de la elección, miembros, reuniones con actas firmadas adjuntas, acuerdos) y Programa anual SSOMA |
| después | Registro de inducción, capacitación, entrenamiento y simulacros (formato diseñado en `PROCEDIMIENTOS SIG/Formatos SST (propuesta)/`) |
| 0.9.0 | Medio ambiente (M22) |

## 3. Decisiones

| Tema | Decisión |
|---|---|
| Fórmula IPERC | La del formato: probabilidad = A + B + C + D (índices 1–3), nivel = probabilidad × severidad (1–3). Trivial ≤ 4 · Tolerable 5–8 · Moderado 9–16 · Importante 17–24 · Intolerable ≥ 25. Aceptable hasta Moderado. |
| Nivel recalculado | El sistema siempre calcula el nivel. En 26 filas del Excel la probabilidad estaba escrita a mano (no era la suma) y el nivel salía menor; se cargaron recalculadas y cada una deja la observación en su historial. |
| Escala del ATS | La del formato ATS: severidad 1–4 × probabilidad 1–4 (Tolerable ≤ 2 · Poco significativo 3–6 · Significativo 8–9 · Intolerable ≥ 12). No se mezcla con la del IPERC. |
| Puestos | Desde 0.8.2 vienen de Organización y personal (núcleo, ADR-0006); SST solo los referencia. El texto original de la columna «puestos» del Excel se conserva en cada fila. Cada fila IPERC tiene además el área del organigrama (la hoja de la matriz se conserva: es la estructura del formato). |
| Áreas | Una por hoja del Excel (16). La hoja «SIG (2)» no se cargó: es una copia de trabajo (confirmado por César, 2026-10-22). |
| Firmas del ATS | El supervisor o prevencionista de SST valida con su contraseña. Los ejecutantes y el cliente firman en el formato impreso (la firma con PIN del trabajador llega en 0.8.3). |
| ATS en campo (2026-10-22) | En campo el ATS se llena y firma en papel: en el formato de Metrindust (impreso prellenado desde un ATS tipo) o en el del cliente cuando lo exige. Al volver se adjunta firmado y SST lo revisa con firma. El ATS en las instalaciones de Metrindust mantiene la validación previa. |
| Modo sin conexión (2026-10-22) | Llenar el ATS en el celular sin señal, con firmas en pantalla, se construye junto con la OT en campo (fase 3.3), cuando el sistema esté publicado en un servidor; no antes, para no construirlo dos veces. |
| Proceso = área (2026-10-22) | En SST el campo «proceso» admite solo procesos principales del mapa (no subprocesos). La carga de Logística pasó de «Recepción de Equipos y/o Instrumentos» a Metrología. |
| Inspecciones (César, 2026-10-22) | **Motor de plantillas** en tres familias: por elemento (extintores, luces, detectores, escaleras, botiquines, kit antiderrame, herramientas), por preguntas (SSTMA, movilidad, moto) y por trabajador (EPP). Los 11 formatos del procedimiento de seguimiento y medición se cargan como plantillas; el SIG crea nuevas sin programar. El PDF replica la cabecera común y la tabla de su familia. |
| Inventario de seguridad (César, 2026-10-22) | Extintores, luces de emergencia, detectores, escaleras, botiquines, kits y vehículos se registran con código, ubicación, piso y vencimientos (recarga, prueba hidrostática, SOAT, revisión técnica); la inspección los trae solos y hay alertas antes de vencer. |
| No conformes (César, 2026-10-22) | Cada ítem «No conforme» lleva acción inmediata, responsable y plazo, con seguimiento en la misma inspección. Un botón registra hallazgo → solicitud de acción correctiva solo para los relevantes. |
| Alcance 0.8.6 (César, 2026-10-22) | Inspecciones con su programa y frecuencias, y monitoreos (programa anual, registro con límites máximos permisibles, seguimiento de recomendaciones), todo junto. |
| Entregas 0.8.7 y 0.8.8 (César, 2026-10-22) | 0.8.7: EPP y vigilancia médica (lo que toca a cada trabajador). 0.8.8: Comité SST y Programa anual SSOMA. El registro de inducción, capacitación, entrenamiento y simulacros queda para después. |
| Firma de la entrega de EPP (César, 2026-10-22) | El trabajador firma con un **PIN personal** de 4 a 6 dígitos que crea en su primera entrega, delante del Área SIG; se guarda cifrado; 5 intentos fallidos lo bloquean y SIG lo restablece. Si no puede firmar en pantalla, se adjunta el cargo firmado en papel. El responsable de la entrega firma con su contraseña. |
| Stock de EPP (César, 2026-10-22) | No se lleva en SST: catálogo de EPP con vida útil, matriz por puesto, entregas, reposiciones, devoluciones y alertas de renovación. El stock lo lleva Logística y se integra con Inventarios (M28). |
| Vigilancia médica | Solo la aptitud (apto, apto con restricciones, no apto, observado) y las restricciones o recomendaciones sin diagnóstico; los resultados clínicos los custodia el médico ocupacional. Próximo examen: anual para el personal operativo y cada dos años para el administrativo (procedimiento de seguimiento y medición), editable. |
| Aprobación de la matriz IPERC (0.8.11, César) | La matriz la **realiza y aprueba el Comité de SST**, como en el pie del formato. Se aprueban una o varias hojas a la vez; firma cada titular (mitad más uno como mínimo): con la contraseña de su usuario si lo tiene, con su PIN si no; o se adjunta el acta firmada en papel. Si una fila cambia después, la hoja queda **pendiente de aprobación** hasta que el Comité la apruebe de nuevo. Reemplaza la «revisión del área» de una sola persona. Cargada la aprobación del 15/12/2025 (todas las hojas). La carga inicial había tomado como filas el pie de cada hoja (32 filas con razón social, RUC y domicilio): se retiraron; la matriz vigente tiene 353 filas. |
| Firma de personas (0.8.11, César) | Regla para todo el sistema: con usuario → contraseña de su usuario; sin usuario → PIN personal. Aplica a la entrega de EPP, al cargo de resultados médicos y a la aprobación del IPERC. |
| Comité SST (0.8.8) | El proceso electoral (convocatoria, candidaturas, votación) sigue en papel; el sistema registra el **resultado**: comité por periodo con sus miembros (empleador / trabajadores, titular / suplente, presidente y secretario), actas de elección e instalación y el registro en el T-Registro como adjuntos. Reuniones (instalación, ordinarias mensuales, extraordinarias) con asistentes, quórum (mitad más uno de los titulares), agenda, desarrollo y acuerdos; el sistema imprime el acta en borrador para firmar y la reunión se cierra con el **acta firmada adjunta**. Acuerdos con responsable, plazo y seguimiento mensual. El Comité de intervención frente al hostigamiento sexual queda fuera (información reservada). |
| Programa anual SSOMA (0.8.8) | Objetivos (con indicador y meta) y actividades con responsable (puesto), meses programados y ejecutados, evidencia y avance. Aprobado con firma: lo programado queda de solo lectura; un cambio se hace como reprogramación con motivo (nueva versión). Cargado el programa 2026 del Excel. |
| Vigilancia médica (0.8.8) | Cargo de entrega de resultados: el trabajador lo firma con su PIN (o cargo en papel). Recordatorio anual del Anexo 4 (informe técnico de vigilancia, hasta marzo), con su registro de presentación. |
| Caja de control | IPERC: versión 01 · 2025-10-01 · GSIG / GSIG / GG. ATS: versión 00 · 2026-03-20 · ASIG / GSIG/GG / GG (las de las plantillas). La lista maestra manda cuando el formato esté vinculado. |

## 4. Registros y reglas

- **Puesto:** nombre (único), tipo (propio / tercero), proceso, funciones. Se desactiva, no se borra.
- **Fila IPERC (IPR-000):** área, proceso del catálogo, subproceso, puestos expuestos (o «todos los puestos»), actividad, peligro (con la tabla de peligros del anexo como ayuda), riesgo, consecuencia, situación (rutinaria / no rutinaria / emergencia, al menos una), controles existentes, requisito legal; evaluación inicial; controles por jerarquía (eliminación, sustitución, ingeniería, administrativo, EPP) y responsable; evaluación residual.
- **Situación de control:** sin evaluar · controlado (aceptable, o residual aceptable) · **requiere control** (no aceptable sin controles o sin residual) · **trabajo detenido** (residual todavía no aceptable).
- Cada cambio queda en el **historial** de la fila (campos, nivel anterior y nuevo). Las filas no se eliminan: se **retiran con motivo**.
- **Revisión del área** con firma: fija la «fecha de actualización» del formato.
- **ATS (ATS-000-AAAA):** datos generales del formato, tipo de trabajo, hasta 9 ejecutantes, hasta 6 equipos, filas IPERC relacionadas, etapas con peligros, riesgos, S×P, medidas y S×P con medidas. **Validación con firma** del supervisor: exige zona, tarea, personal, etapas evaluadas con medidas; las etapas significativas o intolerables requieren la evaluación con medidas; si queda intolerable, no se valida («no se permite realizar el trabajo»). Validado o anulado = solo lectura; se anula con motivo.
- **ATS en campo:** dónde se realiza (instalaciones / campo), formato (Metrindust / cliente) y cliente. Estados: en preparación → **en campo** (la preparación queda cerrada; solo se transcribe lo que cambió: personal, equipos, horario, firmantes del cliente, comentarios, filas IPERC; y las etapas si el formato es el de Metrindust) → **recibido** (adjunto obligatorio del ATS firmado, fecha de ejecución, observaciones de campo) → **revisado** por SST con firma. SST puede devolverlo con observación (vuelve a «en campo»). En el formato de Metrindust la revisión exige las etapas transcritas y, si quedó un riesgo intolerable, una observación. Un ATS revisado no se anula. Indicador: trabajos en campo sin ATS recibido (fecha pasada) y ATS por revisar.
- **ATS tipo:** servicio, descripción, tipo de trabajo, proceso, filas IPERC y etapas con su evaluación típica. Al preparar un ATS se copia y se ajusta; también se puede guardar un ATS como tipo.

- **Incidente / accidente (AT, IP, IN, EM):** reportado → en investigación → en revisión → en acciones → cerrado (anulado solo antes de concluir). Reporte después de 24 h marcado. Personas afectadas con los datos del registro oficial; descanso médico actualizable hasta el cierre. Concluir (firma, elaborado) exige gravedad y grado (accidentes), porqués (método 5 porqués), causas inmediatas y básicas y conclusiones. Revisar (firma, aprobar) registra hallazgo (NC mayor si incapacitante, mortal o incidente peligroso) y solicitud de acción correctiva. Cierre (firma) exige la solicitud cerrada, la notificación al Ministerio (mortal o incidente peligroso) y, si se pidió, confirmar la actualización del IPERC.
- **Enfermedad ocupacional:** registro agregado por área (sin datos personales de salud); al firmarse registra hallazgo y solicitud.
- **Elementos de seguridad (inventario):** extintores, luces de emergencia, detectores de humo, escaleras, botiquines, kits antiderrame, vehículos y motos; código único por tipo; vencimientos (recarga, prueba hidrostática, SOAT, revisión técnica, productos del botiquín) con aviso 30 días antes; baja con motivo, no se elimina.
- **Plantillas de inspección:** las 11 del procedimiento de seguimiento y medición cargadas (botiquines, extintores, luces, SSTMA, detectores, EPP, kit antiderrame, escaleras, movilidad, moto lineal, herramientas portátiles). Tipo de lista (en el código, «familia»): lista de equipos, contenido de un equipo, lista de preguntas, lista de trabajadores. Escalas: C/NC/NA, Sí/No/NA, Óptimo/Mal/NA, ✔/X; criterio «invertido» (Requiere cambio). Frecuencia y caja de control de respaldo por plantilla. El SIG crea o cambia plantillas sin programar; cada inspección guarda la estructura con la que se hizo.
- **Inspección (INS-000-AAAA):** en registro → firma del responsable del registro → con acciones pendientes → cerrada (anulada solo antes de firmar). Filas según la familia (inventario del tipo y del área, contenido del elemento, preguntas, trabajadores del área). No se firma con respuestas vacías ni con un «no conforme» sin acción inmediata, responsable y plazo. Firmada: respuestas y datos de solo lectura. Completar las acciones cierra la inspección. El hallazgo (→ solicitud de acción correctiva) se registra solo para los ítems elegidos, una vez.
- **Programa de inspecciones:** por plantilla y mes según su frecuencia: realizada, en plazo, programada, atrasada.
- **Monitoreos:** programa anual por agente (meses programados; reprogramación en el historial); registro (MON-000-AAAA) con resultados frente al LMP, causas de las desviaciones, conclusiones e informe adjunto, firmado; seguimiento de recomendaciones por agente con fecha o frecuencia, responsable y estado. Cargados: programas 2025 y 2026, monitoreo de diciembre de 2025 y sus 20 recomendaciones.
- **EPP:** catálogo (29 EPP del formato de entrega, con las marcas de la matriz; vida útil por definir), matriz por puesto (14 perfiles: administrativos, logística, metrología por laboratorio y servicio en campo; x obligatorio, x* según la tarea), entrega (EPP-000-AAAA) con dotación, reposición (con motivo; reemplaza el EPP anterior del mismo tipo), cambio de puesto o campo. Firma: responsable con contraseña y trabajador con PIN (lo crea en su primera entrega; cifrado; 5 errores lo bloquean; SIG lo restablece) o cargo en papel adjunto. Firmada no se modifica; anulación solo antes de firmar. Devolución (reutilizable / descartado). Situación por trabajador frente a la matriz: falta, vigente, por renovar, vencido. Alertas: obligatorios sin entregar, renovaciones, cesados con EPP sin devolver, PIN bloqueados.
- **Vigilancia médica:** evaluación (EMO-000-AAAA: tipo de examen, centro médico, médico y CMP, medidas correctivas) con la aptitud de cada trabajador, sus restricciones o recomendaciones sin diagnóstico, el próximo examen (12 meses operativo, 24 administrativo, editable) y el certificado de aptitud adjunto; no se registra sin aptitud, restricciones cuando corresponden, próximo examen ni centro médico. Vista por trabajador: último examen, aptitud y próximo (sin examen, vencido, por vencer).
- **Cargo de entrega de resultados médicos y Anexo 4 (0.8.8):** con la evaluación registrada, cada trabajador firma la recepción de su resultado con su PIN (el mismo de los EPP) o se adjunta el cargo en papel; quien registra firma con su contraseña; una sola vez por resultado. Informe anual de vigilancia médica (Anexo 4): pendiente del año anterior con plazo al 31 de marzo (por vencer / vencido) hasta registrar su presentación con el archivo; corregirla es reemplazarla con motivo (queda la constancia en observaciones).
- **Comité de SST (0.8.8):** por periodo (fechas de elección, instalación y fin del mandato; T-Registro; actas de elección e instalación y constancia adjuntas). Miembros de Organización y personal: representación, titular / suplente, cargo; un solo presidente y un solo secretario, ambos titulares; baja con motivo (queda el historial). Alertas: no paritario, falta presidente o secretario, sin T-Registro, mandato por vencer (60 días), sin reunión ordinaria del mes, acuerdos vencidos. Cargado el comité 2025-2027 (sus miembros se registran cuando estén en Organización y personal).
- **Reunión del comité (NNN-AAAA-CSST):** programada → realizada (exige agenda, quórum —mitad más uno de los titulares— y el acta firmada adjunta) / cancelada con motivo. El sistema imprime el acta para firmar. Cerrada, no cambia.
- **Acuerdos:** responsable (trabajador) y plazo; seguimiento con estado (pendiente, en proceso, cumplido, no cumplido) y comentario obligatorio; vencido si pasa el plazo sin cumplirse.
- **Programa anual SSOMA:** objetivos y actividades con responsable (puesto), indicador, meta y meses. En elaboración se edita; aprobado (firma con contraseña, permiso aprobar) lo programado no cambia y se registra la ejecución por mes con evidencia (no meses futuros); reprogramar abre una nueva versión con motivo y guarda lo anterior en el historial. Avance por actividad y por objetivo a la fecha. Cargado el programa 2026 del Excel (3 objetivos, 9 actividades, ejecutado de enero y febrero).
- **Estadísticas:** por mes; horas-hombre = trabajadores propios activos en el mes × días laborables × 8 (editables); IF = incapacitantes × 10⁶ / HH; IG = días perdidos × 10⁶ / HH; IA = IF × IG / 1000; tasa de incidencia = enfermedades × 10⁶ / expuestos.

## 5. API

| Ruta | Permiso | Qué hace |
|---|---|---|
| `/api/org-puestos/` (núcleo, desde 0.8.2) | Organización | Catálogo de puestos; SST solo lo lee |
| `/api/sst-iperc/` | leer · crear · editar | Filas (filtros `area`, `proceso`, `puesto` —incluye «todos los puestos»—, `clasificacion`, `situacion`, `buscar`, `retirados`) |
| `POST .../{id}/retirar/` | editar | Retiro con motivo |
| `GET .../catalogos/` · `resumen/` · `matriz_pdf/?area=` | leer | Áreas, niveles, tabla de peligros; resumen por área; PDF (A3, una hoja por área) |
| `GET .../aprobaciones/` · `POST .../aprobar_comite/` (aprobar; JSON con firmas o multipart con acta) | leer · aprobar | Aprobación del Comité por hojas; estado aprobada / pendiente / sin aprobar |
| `/api/sst-ats/` + `agregar_paso/` · `editar_paso/` · `quitar_paso/` · `validar/` · `enviar_a_campo/` · `recibir/` (multipart) · `observar/` · `revisar/` · `anular/` · `guardar_como_tipo/` · `pdf/` · `resumen/` | leer · crear · editar | ATS |
| `/api/sst-ats-tipo/` | leer · crear · editar · eliminar | ATS tipo (DELETE desactiva) |
| `/api/sst-eventos/` + `afectado/` · `quitar_afectado/` · `actualizar_descanso/` · `archivo/` · `notificar_mtpe/` · `iniciar_investigacion/` · `concluir/` · `devolver/` · `aprobar_informe/` · `cerrar/` · `anular/` · `registro_pdf/` · `informe_pdf/` · `catalogos/` | leer · crear · editar · aprobar · eliminar | Incidentes y accidentes |
| `/api/sst-enfermedades/` + `registrar_acciones/` · `cerrar/` · `anular/` · `pdf/` | leer · crear · editar · aprobar · eliminar | Enfermedades ocupacionales |
| `/api/sst-estadisticas/anio/` · `datos_mes/` · `informe/` · `registro_pdf/` · `datos_pdf/` | leer · editar | Estadísticas |
| `/api/sst-elementos/` + `dar_baja/` · `catalogos/` | leer · crear · editar · eliminar | Inventario de elementos de seguridad |
| `/api/sst-plantillas/` | leer · crear · editar · eliminar | Plantillas de inspección (DELETE desactiva) |
| `/api/sst-inspecciones/` + `agregar_fila/` · `quitar_fila/` · `responder/` · `firmar/` · `completar_accion/` · `registrar_hallazgo/` · `anular/` · `pdf/` · `programa/` · `resumen/` | leer · crear · editar · eliminar | Inspecciones |
| `/api/sst-programa-monitoreos/` + `anio/` · `item/` · `quitar_item/` · `pdf/` | leer · crear · editar | Programa anual de monitoreos |
| `/api/sst-monitoreos/` + `informe/` · `firmar/` · `anular/` · `pdf/` | leer · crear · editar · eliminar | Registro de monitoreos |
| `/api/sst-recomendaciones/` + `programa_pdf/` | leer · crear · editar · eliminar | Seguimiento de recomendaciones |
| `/api/sst-epp-catalogo/` + `catalogos/` | leer · crear · editar · eliminar | Catálogo de EPP (DELETE desactiva) |
| `/api/sst-epp-matriz/` + `requisitos/` · `matriz_pdf/` | leer · crear · editar · eliminar | Matriz de EPP por puesto |
| `/api/sst-epp-entregas/` + `firmar/` · `firmar_papel/` · `restablecer_pin/` (aprobar) · `devolver/` · `anular/` · `estado/` · `sugerir/` · `resumen/` · `pdf/` · `tarjeta_pdf/` | leer · crear · editar · aprobar · eliminar | Entregas de EPP |
| `/api/sst-emo/` + `agregar/` · `resultado/` · `quitar/` · `certificado/` · `firmar/` · `anular/` · `pdf/` · `vigilancia/` · `entregar_resultados/` · `entregar_resultados_papel/` · `anexo4/` · `registrar_anexo4/` | leer · crear · editar · eliminar | Vigilancia médica |
| `/api/sst-comite/` + `vigente/` · `catalogos/` · `adjuntar/` · `miembro/` · `baja_miembro/` | leer · crear · editar | Comité de SST |
| `/api/sst-comite-reuniones/` + `acuerdo/` · `quitar_acuerdo/` · `cerrar/` (multipart) · `cancelar/` (eliminar) · `pdf/` | leer · crear · editar · eliminar | Reuniones y actas |
| `/api/sst-comite-acuerdos/` + `seguimiento/` | leer · editar | Acuerdos de reuniones realizadas |
| `/api/sst-programa-ssoma/` + `anio/` · `objetivo/` · `actividad/` · `quitar_actividad/` · `ejecutar/` · `aprobar/` (aprobar) · `reprogramar/` · `pdf/` | leer · crear · editar · aprobar | Programa anual SSOMA |

## 6. Criterios de aceptación

1. La matriz cargada muestra las 353 filas vigentes de las 16 hojas con su nivel inicial y residual; el PDF de un área replica las columnas del Excel con los colores de nivel.
2. Una fila con nivel Importante o Intolerable aparece como «requiere control» hasta registrar controles y la evaluación residual; si el residual sigue no aceptable, «trabajo detenido».
3. Una fila no se elimina; retirada queda como registro con su historial.
4. Un ATS no se valida sin etapas evaluadas y medidas, ni con riesgo intolerable; validado no se modifica; el PDF replica el formato.
5. Un ATS en campo no se recibe sin el archivo firmado; recibido ya no se modifica; el revisado queda con la firma de SST. El formato del cliente no exige etapas ni tiene PDF propio.
6. Un ATS preparado desde un ATS tipo trae sus etapas, tipo de trabajo, proceso y filas IPERC.
7. Un accidente no se concluye sin causas ni porqués; al revisarse registra hallazgo y solicitud de acción correctiva; no se cierra con la solicitud abierta ni, si es mortal o peligroso, sin la notificación al Ministerio.
8. Las estadísticas del mes calculan IF, IG e IA con las fórmulas de la R.M. 050-2013-TR sobre las horas-hombre propuestas o editadas.
9. Una inspección de extintores trae los extintores activos del inventario; no se firma con respuestas vacías ni con un «no conforme» sin acción; firmada no cambia; se cierra al completar sus acciones; el PDF replica la cabecera y la tabla del formato.
10. Cambiar una plantilla no altera las inspecciones ya hechas.
12. Una entrega de EPP no se firma sin la contraseña del responsable y el PIN del trabajador (o el cargo en papel); el PIN se guarda cifrado y se bloquea al quinto error; la reposición reemplaza el EPP anterior.
13. Un examen médico registra solo aptitud y restricciones, y no se registra sin ellas ni sin el próximo examen.
14. El comité no admite dos presidentes o secretarios ni un suplente en esos cargos, y alerta si no es paritario o no está en el T-Registro.
15. Una reunión no se cierra sin agenda, quórum ni acta firmada adjunta; cerrada no cambia; sus acuerdos se siguen con comentario y se marcan vencidos.
16. El programa SSOMA aprobado no cambia lo programado; la ejecución exige evidencia y no admite meses futuros; reprogramar abre una nueva versión que se vuelve a aprobar; el PDF replica el formato.
17. El cargo de resultados médicos solo se firma con la evaluación registrada, con el PIN del trabajador (o papel) y una sola vez; el Anexo 4 del año anterior queda pendiente hasta registrarse.
18. La matriz de un área solo queda aprobada con la firma de la mitad más uno de los titulares del Comité (contraseña o PIN según tengan usuario) o con el acta en papel; si una fila cambia, el área queda pendiente; el PDF imprime el pie del formato con los firmantes y la fecha, o las casillas en blanco y el aviso de pendiente.
11. Un monitoreo no se registra sin resultados frente al LMP, causas de las desviaciones, conclusiones e informe; registrado marca como ejecutado su monitoreo del programa.
