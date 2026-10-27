# M21 (parte) · Capacitación e inducción

**App:** `capacitacion` (app propia, ADR-0004) · **Permisos:** módulo `capacitacion` · **Estado:** 0.9.1 construido, en validación · **Pruebas:** `capacitacion/tests/test_capacitacion.py`
**Procedimiento:** Gestión del Personal Ver. 01 (carpeta `PROCEDIMIENTOS SIG/`). **Formatos que replica:** Inducción al personal (tres partes), Lista de asistencia y Programa anual de capacitación.

## 1. Propósito
Planificar y evidenciar la inducción y la capacitación del personal: el programa anual aprobado por el Comité de SST, cada sesión con su lista de asistencia firmada, las notas y certificados, la evaluación de la eficacia y la inducción de cada trabajador. Cubre el registro obligatorio de inducción, capacitación, entrenamiento y simulacros de emergencia de la ley de SST (DS 005-2012-TR, art. 33) y las capacitaciones de SST que exige la ley (mínimo cuatro al año). Lo usan SST (indicadores en su Inicio), Competencia técnica y el resto del sistema.

## 2. Alcance (César, 2026-10-23)
| Incluido | Fuera (módulo de Recursos Humanos, después) |
|---|---|
| Programa anual de capacitación, aprobación del Comité, reprogramación y cancelación | Selección y entrevista del personal |
| Listas de asistencia (inducción, capacitación, entrenamiento, simulacro, charla, difusión, etc.) | Legajo, declaraciones juradas, planilla y T-Registro |
| Notas, certificados de aprobación o participación, constancias externas, material | Vacaciones |
| Evaluación de la eficacia a los 6 meses | Evaluación del simulacro (escenario, tiempos): pendiente del plan de emergencias |
| Inducción organizacional, del SIG y específica del cargo, con su contenido editable | |
| Situación por trabajador | |

## 3. Decisiones
| Tema | Decisión |
|---|---|
| Aprobación del programa | La realiza y aprueba el Comité de SST (pie del formato), igual que la matriz IPERC: firma de la mitad más uno de los titulares (contraseña de su usuario o PIN) o el acta en papel adjunta. Agregar, corregir o cancelar capacitaciones deja el programa pendiente de una nueva aprobación; reprogramar una fecha (RP) y ejecutar (R) no. |
| Firma de los asistentes | Regla del sistema: con usuario, su contraseña; sin usuario, su PIN (el mismo de EPP). Respaldo: la lista firmada en papel adjunta (marca a todos los asistentes sin firma). |
| Realizado | Una capacitación del programa queda realizada al cerrarse una lista de asistencia vinculada a ella (fecha realizada y V°B° de quien registra). |
| Certificados | Nota ≥ 14 → certificado de aprobación; si no o sin evaluación, de participación. Las externas llevan la constancia de la entidad. El diseño del certificado impreso queda pendiente (no hay formato). |
| Eficacia | Se evalúa una vez por sesión, con evidencia y firma; vence a los 6 meses (alerta 30 días antes). |
| Inducción | Tres partes; cada una se aprueba con 14 (nota sobre 20: las calificaciones se llevan a 20 según el total de puntos; la del SIG es la nota de la evaluación en línea). Desaprobada, se repite solo esa parte (nuevo intento). Completa con las tres aprobadas. Una inducción en proceso a la vez por trabajador. |
| Personal a capacitar | Todo el personal, áreas (incluye sus dependencias), puestos u otro grupo (texto; no se calcula por trabajador). «Metrología» = los laboratorios. |
| Contenido de la inducción (César, 2026-10-23) | Es configuración controlada, no código: temas (lista de verificación), documentos y preguntas se agregan, corrigen, quitan y reordenan; temas y documentos admiten enlace; los documentos pueden vincularse a la lista maestra (nombre, código y versión vigente). Cada cambio exige motivo, sube la versión y queda en el historial. Las inducciones registradas conservan su copia. |
| Duración de la sesión (César, 2026-10-23) | Se calcula con «Desde» y «Hasta» (servidor y pantalla); sin horas se indica a mano. |
| Carga inicial | Programa 2026 del Excel (36 capacitaciones; aprobado por el Comité el 2026-05-11, secretaria Erika Vega Rondo) con las correcciones revisadas con César; programa 2025 como histórico (solo consulta); contenido de las tres partes de la inducción. |

## 4. Registros y reglas
- **Programa anual:** año único; capacitaciones con tema, tipo (Metrología, SST, SIG, Calidad, Ambiental, RR. HH.), responsable, externa, personal a capacitar, fecha programada, horas; reprogramaciones (de, a, motivo); cancelación con motivo; fecha realizada y V°B°. Indicadores: programadas, realizadas, avance del año y a la fecha, atrasadas, SST realizadas, horas.
- **Lista de asistencia (CAP-NNN-AAAA):** en registro → cerrada (firma de quien registra) / anulada. Datos del formato: capacitador (o entidad), fecha, desde/hasta, duración, tipo, temas, material, tema tratado, asistentes con DNI y cargo, observaciones. No se cierra sin asistentes firmados, sin las notas (si tiene evaluación) ni sin duración. Cerrada: datos de solo lectura; se adjuntan constancias y material y se evalúa la eficacia.
- **Inducción (IND-NNN-AAAA):** partes con responsable, fecha, horas, temas incluidos, documentos entregados, evaluación, evaluador, observaciones; firma del responsable (contraseña) y del colaborador (usuario o PIN). Firmada no cambia.

## 5. API
| Ruta | Permiso | Qué hace |
|---|---|---|
| `/api/cap-programas/` + `anio/` · `catalogos/` · `item/` · `reprogramar/` · `cancelar/` · `firmantes/` · `aprobar/` (aprobar) · `pdf/` · `resumen/` · `situacion/` | leer · crear · editar · aprobar | Programa anual, indicadores y situación por trabajador |
| `/api/cap-sesiones/` + `asistentes/` · `quitar_asistente/` · `firmar_asistente/` · `nota/` · `lista_papel/` · `archivo/` · `cerrar/` · `eficacia/` (aprobar) · `anular/` (eliminar) · `pdf/` | leer · crear · editar · aprobar · eliminar | Listas de asistencia |
| `/api/cap-inducciones/` + `guardar_parte/` · `firmar_parte/` · `repetir_parte/` · `anular/` · `pdf/` | leer · crear · editar · eliminar | Inducción |
| `/api/cap-plantillas/` | leer · editar | Contenido de las partes de la inducción |

## 6. Criterios de aceptación
1. El programa 2026 cargado muestra 36 capacitaciones (27 realizadas) aprobado por el Comité; su PDF replica el formato con la grilla P/R/RP y el pie del Comité.
2. Agregar o corregir una capacitación deja el programa pendiente de aprobación; reprogramar no. El programa histórico no se modifica.
3. Una lista de asistencia no se cierra sin firmas (usuario, PIN o papel), sin notas si hay evaluación ni sin la contraseña de quien registra; al cerrarse, la capacitación del programa queda realizada; nota ≥ 14 da certificado de aprobación.
4. La eficacia se evalúa una vez, con evidencia; vence a los 6 meses.
5. La inducción se completa con las tres partes aprobadas (≥ 14); una parte desaprobada se repite sola.
6. La situación por trabajador muestra lo que le corresponde según el personal a capacitar y si asistió.
7. La duración de la lista de asistencia sale de «Desde» y «Hasta»; «Hasta» anterior se rechaza.
8. Cambiar el contenido de la inducción exige motivo, sube la versión y queda en el historial; los enlaces son http(s); los documentos vinculados toman los datos vigentes de la lista maestra; las inducciones ya creadas no cambian.
