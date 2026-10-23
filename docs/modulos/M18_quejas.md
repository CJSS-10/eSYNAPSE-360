# M18 · Quejas

**App:** `quejas` (app propia, ADR-0004) · **Estado:** construido en 0.3.0; validado el 2026-10-22 (0.8.5), acta por firmar · **Pruebas:** `quejas/tests/test_quejas.py` (17)
**Procedimiento:** Gestión de Quejas (carpeta `PROCEDIMIENTOS SIG/`). **Formatos que replica:** Reporte de Quejas y Registro de Seguimiento de Quejas.

## 1. Propósito

Recibir, validar, evaluar e investigar, decidir, tratar y cerrar las quejas de clientes y otras partes interesadas, con comunicación documentada al reclamante en cada etapa y enlace con No Conformidades y Acciones Correctivas cuando la queja procede. Cubre NTP-ISO/IEC 17025 7.9 e ISO 9001 9.1.2 / 10.2.

## 2. Decisiones (César, 2026-10-20)

| Tema | Decisión |
|---|---|
| Encuestas de satisfacción | Se construyen después, con su formato. Por ahora el origen «Encuesta de satisfacción» se registra a mano. |
| Consulta del estado por el cliente con su código | Después, al publicar el sistema en un servidor. Por ahora se registra cada comunicación al cliente (fecha, medio, resumen, evidencia). |
| Queja procedente → NC | Botón «Registrar NC»: crea la No Conformidad en Hallazgos (procedencia Queja) y sigue el flujo de acción correctiva. Trabajo No Conforme queda como casilla hasta construir ese módulo. |

## 3. Etapas (etapa cerrada = solo lectura, ADR-0005)

| Etapa | Estado | Qué se registra | Quién |
|---|---|---|---|
| 1. Recepción y registro | Recibida | Código RQ-NNN-AAAA, fecha y hora de recepción, recibido por, reclamante (empresa, contacto, correo, teléfono, tipo de parte interesada), N° de OT, medio de recepción, origen (gestión comercial / técnica / logística) y motivo, descripción, documentos adjuntos | Área SIG (registra lo que comunica Comercial u otra área) |
| 2. Validación | Recibida → En evaluación | ¿Relacionada con las actividades de Metrindust? Fecha de validación. Si no lo está, se cierra comunicando los motivos | Gerente / Asistente SIG |
| 3. Evaluación e investigación | En evaluación | Responsables (Gerente Técnico para lo técnico, Gerente SIG para lo demás), personal involucrado, fecha de evaluación, evaluación, investigación y análisis de causas, ¿dentro del alcance acreditado?, ampliación del plazo con motivo | Gerente Técnico / Gerente SIG |
| 4. Decisión | En evaluación → En tratamiento / En cierre | Procedente o no procedente, con fundamento | Gerente Técnico / Gerente SIG (aprobar) |
| 5. Tratamiento | En tratamiento | Acciones a realizar, responsable designado, registrar NC (Hallazgos) y marcar trabajo no conforme, certificado reemplazado y nuevo (si cambia el certificado), seguimiento de las acciones | Responsable designado / Gerente SIG |
| 6. Cierre | En cierre → Cerrada | Comunicación al cliente del resultado (medio, texto, evidencia), conformidad del cliente, fecha de cierre, notificado por (no involucrado en el origen) | Área SIG o Comercial no involucrada |

Una queja cerrada se reabre solo con motivo (historial).

## 4. Comunicaciones y plazos

Cada comunicación al reclamante se registra: tipo (acuse de recibo, resultado de la validación, ampliación de plazo, avance, informe de resultados, motivos de no procedencia, resultado final), fecha, medio (correo, WhatsApp, mensaje, llamada, presencial, otro), resumen y evidencia adjunta.

| Plazo | Desde | Regla |
|---|---|---|
| Acuse de recibo con el código | Recepción | ≤ 24 horas |
| Resultado de la validación | Recepción | ≤ 2 días hábiles (salvo ampliación comunicada) |
| Informe de resultados (si el cliente lo solicita) | Validación | ≤ 7 días hábiles |

Días hábiles = lunes a viernes. La pantalla marca los plazos por vencer y vencidos.

## 5. Formatos

- **Reporte de Quejas:** una queja (N°, fechas de recepción y validación, quien registra, datos del cliente, medio, motivo, descripción, adjuntos, evaluación, investigación, acciones, comunicación y fecha de cierre).
- **Registro de Seguimiento de Quejas:** el listado (N°, fecha de recepción, N° OT, cliente, detalle, presentado por, recibido por, análisis de aceptación, ¿dentro del alcance acreditado?, estado abierto/cerrado, observaciones).

## 6. Criterios de aceptación

1. Registrar una queja asigna RQ-NNN-AAAA correlativo por año de recepción.
2. Sin validar no se evalúa; una queja no relacionada se cierra con la comunicación de motivos.
3. Decidir exige evaluación; no procedente pasa a cierre con motivos; procedente exige acciones y responsable.
4. «Registrar NC» crea la NC en Hallazgos (procedencia Queja) enlazada a la queja; no se duplica.
5. El cierre exige la comunicación al cliente y que la notifique alguien no involucrado.
6. Cada etapa cerrada queda de solo lectura; reabrir exige motivo.
7. Los plazos de 24 h, 2 y 7 días hábiles se calculan y se marcan.
8. Los dos PDF replican sus plantillas.

## 7. API (`/api/quejas/`)

| Acción | Operación | Regla |
|---|---|---|
| `POST` / `PATCH` | crear / editar | PATCH solo con campos de etapas abiertas (`Queja.ETAPAS`); el servidor nombra etapa y campo |
| `DELETE` | eliminar | Anula (baja lógica) solo antes de validar |
| `validar` | editar | Relacionada → en evaluación; no relacionada (con motivo) → en cierre |
| `decidir` | aprobar | Exige responsables, fecha, evaluación e investigación; procedente → tratamiento; no → cierre |
| `registrar_nc` | editar | Crea la NC en Hallazgos (fuente Queja), una sola vez |
| `pasar_a_cierre` | editar | Exige acciones, responsable, seguimiento y su fecha |
| `cerrar` | editar | Comunicación, medio, conformidad (si procede); notificador no involucrado; registra la comunicación final |
| `reabrir` | aprobar | Con motivo; vuelve a la etapa que corresponde al resultado |
| `comunicar` / `adjuntar` / `quitar_adjunto` | editar | Mientras no esté cerrada |
| `pdf` / `seguimiento_pdf` | leer | Reporte de Quejas / Registro de Seguimiento (con filtros) |

## 8. Pendientes

Ver `PENDIENTES.md` (encuestas, consulta web del cliente, enlace con trabajo no conforme, Mis tareas).
