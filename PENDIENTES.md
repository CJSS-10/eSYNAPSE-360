# eSYNAPSE 360 — Pendientes de revisión y desarrollo

> Actualizar este archivo al cerrar cada sesión de trabajo.

## Por revisar / validar (con el sistema en uso)

- [ ] **Documentos — archivo anotado**: descargar desde el botón ámbar "Descargar archivo anotado"
      y confirmar que trae los cambios del revisor (resaltados, tachados). El flujo ya quedó
      verificado por video el 05/06/2026; falta solo esta confirmación puntual.
- [ ] **Hallazgos (M8) — validación completa**: registrar un hallazgo real, recorrer el ciclo
      Registrado → En análisis → En tratamiento → Cerrado, probar reapertura, verificar
      correlativos (NC-2026-001, OBS-, ODM-) y la segregación del cierre.
- [ ] **Carga de documentos reales del SIG**: ya con la base limpia, registrar los SIG-PRO-xx
      reales con sus normas, retención y frecuencia correctas.
- [ ] Ajustes menores de filtros/columnas en Documentos que surjan del uso diario.
- [ ] **Certificado de Dennis**: cuando exista su usuario, colocar su .pfx en
      `backend/certificados/usuarios/<usuario>.pfx` + variable `CERT_PASS_<USUARIO>`.
- [ ] **Confianza en Adobe**: instalar `backend/certificados/ca_sige360_publico.cer` como
      certificado de confianza en las PCs de Metrindust (check verde en las firmas).

## Próximo desarrollo — Fase 1 (SGI Core)

- [ ] **M9 — Acciones Correctivas** ← SIGUIENTE
      - Análisis de causa raíz: 5 Porqués e Ishikawa (6M)
      - Plan de actividades: responsable + fecha límite por actividad
      - Alertas de vencimiento (3 días antes / vencida → escalonada)
      - Verificación de eficacia por persona distinta; si eficaz cierra el hallazgo
        vinculado, si no lo reabre (conexión directa con M8)
      - AC automática desde NC Mayor (el gancho `requiere_ac` ya existe en M8)
- [ ] **M10 — Auditorías** (cierra la Fase 1)
      - Programa anual, planificación con auditor líder, checklists por norma
      - Hallazgos de auditoría → se registran automáticamente en M8

## Fases siguientes (referencia rápida)

- Fase 2: Laboratorio 17025 (M12 Competencia, M13 Equipos, M14 Métodos, M15 Ensayos, M16 TNC)
- Fase 3: Cadena operativa (M24 CRM, Logística, M25 OT, M30 Cobranzas)
- Producción: migrar a PostgreSQL, servidor, respaldos automáticos, LibreOffice para
  conversión Word→PDF automática
