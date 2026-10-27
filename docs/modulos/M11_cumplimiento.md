# M11 Cumplimiento

**App:** `cumplimiento` · **Permiso:** `cumplimiento` · **Versión:** 0.14.0 · **Diseño:** acordado con César el 2026-10-26 (`PENDIENTES.md`).

## Para qué

Responder, norma por norma, «¿cumplimos este requisito, cómo y dónde está la evidencia?» para ISO 9001, ISO 14001, ISO 45001 y NTP ISO/IEC 17025, y mostrar el grado de cumplimiento del SIG como insumo de la Revisión por la dirección.

## Fuera del alcance

- Leyes, decretos y la Ley 29783: siguen en M2 Requisitos legales; aquí solo se ve su resultado como evidencia de la cláusula correspondiente.
- Auditorías: siguen en M10; aquí solo se ve su resultado como evidencia.

## Requisitos y criterios de aceptación

### Catálogo (no se cargan las normas otra vez)
- Base: el catálogo de requisitos de normas de Auditorías.
  - ISO 9001, 14001 y 45001 se evalúan por **cláusula** (4.1 … 10.3).
  - NTP ISO/IEC 17025 se evalúa por **numeral** (4.1.1 … 8.9.3).
  - Se suman los ítems de seguimiento del organismo de acreditación del catálogo (cambios a comunicar, uso del símbolo, etc.).
- **Otros requisitos** (organismo de acreditación, entidad certificadora, clientes u otros) que el Área SIG registra: fuente, documento de referencia, código, texto y norma relacionada. Se evalúan igual que los de norma. Se dan de baja con motivo, nunca se borran.

### Evaluación por requisito
- Estado:
  - cumple / parcial / no cumple;
  - **no aplica** con justificación obligatoria;
  - sin evaluar.
- Campos de la evaluación:
  - proceso responsable (catálogo de Procesos, solo procesos principales);
  - cómo se cumple (texto);
  - documentos de la lista maestra que lo sustentan;
  - evidencia (texto);
  - fecha y autor de la última evaluación.
- Cada cambio queda en el historial del requisito (quién, cuándo, estado anterior y nuevo).
- **Correspondencia entre normas**: las cláusulas comunes de la estructura de alto nivel de ISO 9001, 14001 y 45001 se evalúan una vez y se reflejan en las otras dos.
  - Son 4.1 a 4.4, 5.1 a 5.3, 6.1, 6.2, 7.1 a 7.5, 8.1, 9.1 a 9.3 y 10.1 a 10.3.
  - La 8.2 solo se comparte entre 14001 y 45001.
  - El reflejo es opcional en cada evaluación (marcado por defecto) y queda anotado en el historial de cada norma.

### Evidencia automática desde los módulos
Cada requisito vinculado muestra la evidencia viva del sistema con nivel **conforme**, **alerta** o **informativo**. Solo hay alerta ante hechos objetivos: algo vencido, no aprobado o inexistente.

| Evidencia | Alerta cuando | Requisitos |
|---|---|---|
| Programa de auditorías del año | no está aprobado | 9.2 · 17025 8.8 |
| Revisión por la dirección | ninguna cerrada en los últimos 12 meses | 9.3 · 17025 8.9 |
| Matriz de riesgos y oportunidades | sin riesgos vigentes o sin revisión en 12 meses | 6.1 · 17025 8.5 |
| Riesgos a la imparcialidad | ninguno identificado | 17025 4.1.4–4.1.5 |
| Evaluación del cumplimiento legal | ninguna cerrada en 12 meses | 14001 y 45001 6.1 y 9.1 |
| Matriz IPERC | sin aprobación del Comité en 12 meses | 45001 6.1 |
| Matriz de aspectos ambientales | sin aprobación en 12 meses | 14001 6.1 |
| Comité de SST | no vigente o sin reunión realizada en 2 meses | 45001 5.4 |
| Programa SSOMA del año | no aprobado | 14001 y 45001 6.2 |
| Programa de capacitación del año | no aprobado | 7.2 · 7.3 |
| Autorizaciones del personal técnico | seguimiento vencido | 17025 6.2.5–6.2.6 · 9001 7.2 |
| Equipos con calibración | calibración vencida en uso | 17025 6.4.7 · 6.4.13 · 6.5.1 · 9001 7.1 |
| Lista maestra | documentos vigentes con revisión vencida | 7.5 · 17025 8.3 |
| Fichas de proceso | proceso principal sin ficha vigente | 4.4 · 17025 8.2 |
| Acciones correctivas, quejas, trabajo no conforme, cambios, monitoreos, consumos | solo informativo (conteos) | 10.2 · 17025 8.7 · 7.9 · 7.10 · 9001 8.7 · 6.3 · 45001 8.1 · 9.1 |

- Un requisito evaluado como cumple o parcial pasa a **en riesgo** si su evidencia automática está en alerta o si la evaluación tiene más de 12 meses.

### Brecha → hallazgo → acción correctiva
- Un requisito en parcial o no cumple se registra como **hallazgo** con un clic. Al registrarlo se elige el tipo: NC mayor, NC menor u observación.
- El hallazgo lleva fuente «Seguimiento», requisito «Norma cláusula», el proceso y la descripción.
- Queda vinculado al requisito, y solo puede haber un hallazgo abierto por requisito. El tratamiento sigue en Hallazgos y Acciones correctivas.

### Tablero
- % de cumplimiento por norma: cumple = 100, parcial = 50, no cumple = 0; no aplica se excluye.
- Cobertura: % de requisitos evaluados.
- Requisitos en riesgo y % por proceso.
- **Cortes**: el Área SIG guarda un corte (fecha y resultado por norma) para ver la evolución. La Revisión por la dirección muestra el estado actual en la entrada de desempeño del SIG.

### Permisos
- Leer: ver.
- Editar: evaluar.
- Crear: registrar otros requisitos y hallazgos.
- Aprobar: guardar cortes.
- Eliminar: dar de baja otros requisitos.

### Por sede y PDF (0.14.1, decisiones de César del 2026-10-27)
- Evaluación individual del SIG completo y de cada sede (`EvaluacionSede`): cada una con su propia calificación, sin combinarse ni heredarse; una sede sin evaluar queda «sin evaluar». Cada estado de sede exige indicar cómo se cumple o la evidencia en la sede. El hallazgo de una brecha de sede exige que esa sede esté en parcial o no cumple.
- Tablero con cumplimiento por sede; matriz con vista por sede; hallazgo con la sede como lugar de detección.
- PDF «Matriz de evaluación del cumplimiento de requisitos» (A4 horizontal): cabecera con caja de control, alcance, resumen por norma y sede, evidencia en alerta y matriz por norma con estados coloreados, sin pie de página. Formato nuevo: código «POR ASIGNAR» hasta vincularlo con su documento en la lista maestra.

## Decisiones abiertas (para César)
- ~~P-M11-1 Sede~~ y ~~P-M11-2 Formato impreso~~: resueltas en 0.14.1.
- **P-M11-3 Requisitos del organismo de acreditación:** el catálogo de «otros requisitos» parte vacío. El Área SIG carga las directrices y políticas del INACAL que apliquen (trazabilidad, incertidumbre, ensayos de aptitud, uso del símbolo).
