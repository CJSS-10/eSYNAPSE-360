# M16 Trabajo no conforme

**App:** `tnc` · **Permiso:** `trabajo_no_conforme` · **Versión:** 0.13.0 · **Procedimiento:** Control de Trabajos y Salidas No Conformes (versión 01) con su Registro de Trabajos y Salidas No Conformes (r01).

## Para qué

Identificar, controlar, evaluar, tratar y cerrar los trabajos no conformes (TNC) y las salidas no conformes (SNC) — NTP-ISO/IEC 17025 7.10 · ISO 9001 8.7.

## Requisitos y criterios de aceptación

### Registro (cualquier colaborador con permiso de crear)
- Código TSNC-NNN-AAAA (correlativo por año de detección).
- Tipo (TNC / SNC), naturaleza (técnica / administrativa), categoría del incidente (equipo, personal, condiciones ambientales, método, certificado o resultados, administrativo, otro), área o laboratorio (catálogo de Organización), reportado por (trabajador), fecha de detección y de reporte al Gerente SIG y Gerente Técnico, fuente de detección (lista del formato), OT / certificados / equipos involucrados (equipos del módulo Equipos), descripción.
- Fuente «Queja del cliente» exige la queja de origen (RQ); fuente «No conformidad» exige el hallazgo de origen (procedimiento 6.3.6 y 6.3.7).
- Nivel de riesgo (Alto / Medio / Bajo, Tabla N° 2) lo asigna el Gerente Técnico o el Gerente SIG (permiso de aprobar) al iniciar el tratamiento.

### Etapas (ADR-0005): Registro → Tratamiento → Autorización → Evaluación → Cierre → Cerrado
- **Tratamiento:** responsable del tratamiento; acciones ¿aplica? / ¿ejecutada? (detención, repetición, retención de documentos, notificación al cliente, análisis de impacto retroactivo, equipo fuera de servicio); corrección (realizada por, fecha); nota del cliente.
  - **Análisis de impacto retroactivo:** periodo revisado, última condición conforme, filas por OT y certificado (¿entregado?, ¿afectado?, acción: retener / anular y reemitir / ninguna), notificación al cliente (fecha y medio), certificado anulado y de reemplazo, conclusión.
  - **Reglas para pasar a autorización:** corrección registrada; cada acción con «aplica» decidido, y las que aplican, ejecutadas; nivel **Alto** exige detención y análisis retroactivo (y equipo fuera de servicio si la categoría es equipo y hay equipos vinculados); si el análisis aplica, exige periodo, conclusión y al menos una fila; si una fila está **entregada y afectada**, exige la notificación al cliente.
  - «Equipo fuera de servicio» ejecutado deja los equipos vinculados como **Inoperativo / Fuera de servicio** en Equipos.
- **Autorización de la reanudación:** ¿se acepta el TNC/SNC corregido como conforme?, sustento, asignado a; firma con la contraseña de quien autoriza. Naturaleza técnica: Gerente Técnico o Jefe de Laboratorio (puesto creado en 0.13.2; el Supervisor de Laboratorio ya no autoriza); administrativa: Gerente SIG (César, 2026-10-27; el Gerente Comercial solo gestiona la devolución del monto cancelado cuando se anula el servicio). Si no se acepta, vuelve al tratamiento (volver a ejecutar o notificar y anular).
- **Evaluación de la importancia (Área SIG):** ¿afecta la validez?, ¿incumple requisitos del SIG?, ¿compromete la competencia técnica?, nivel confirmado, análisis. El sistema cuenta los **eventos similares** (misma área y categoría, últimos 12 meses). ¿Amerita SAC?: obligatoria si el nivel confirmado es Alto o hay 3 o más eventos similares (6.3.3 y 6.3.5). Firma con contraseña (permiso de aprobar).
- **Cierre:** si amerita SAC, debe estar vinculada (se puede crear desde el registro); evidencias archivadas; firma con contraseña. La eficacia de la SAC sigue en Acciones correctivas (6.5.2).
- Anulación con motivo antes de la autorización.

### Integraciones
- Mis tareas: responsable del tratamiento; autorizaciones pendientes para quien puede autorizar; evaluaciones y cierres para el Área SIG.
- Revisión por la dirección, entrada p): TNC y SNC del periodo por nivel, tipo y estado.
- PDF con el formato del Registro (dos páginas).

### Consulta (0.13.1)
- Tablas N° 1 (responsabilidades y autoridades) y N° 2 (niveles de riesgo y acciones) del procedimiento en una ventana de consulta (`components/TablasTNC.jsx`): botón en el encabezado, en cada registro, junto al nivel de riesgo y en el tratamiento. Si el procedimiento cambia de versión, se actualiza ese archivo.
