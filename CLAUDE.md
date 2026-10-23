# eSYNAPSE 360 — Instrucciones del Proyecto

## Quién eres y qué estás construyendo

Eres el asistente de desarrollo del **eSYNAPSE 360** (Sistema Integrado de Gestión Empresarial) para **Metrindust S.A.C.** (Metrología e Instrumentación Industrial S.A.C.), laboratorio de calibración multimagnitud en Lima, Perú.

El objetivo es construir una plataforma web que unifique todos los procesos de la empresa: calidad, laboratorio, operaciones, comercial y soporte. La visión a futuro es comercializarlo como SaaS para otros laboratorios.

## La empresa

| Dato | Valor |
|------|-------|
| Acreditación | ISO/IEC 17025:2017 — INACAL |
| Certificaciones | ISO 9001 · ISO 14001 · ISO 45001 — Bureau Veritas |
| Personal | ~35 personas |
| Volumen | ~534 OTs/mes · ~2,126 equipos calibrados/mes |
| Clientes | 100+ activos |
| Sedes | 2 (operativa 3 pisos + administrativa) |
| ERP actual | Odoo (se integra vía API para facturación) |

## Stack tecnológico

```
Backend:    Django 5+ · Django REST Framework · SimpleJWT
Frontend:   React 18+ · Tailwind CSS · Shadcn/ui · Framer Motion · Recharts · Lucide Icons
Base datos: SQLite (desarrollo) → PostgreSQL (producción)
Auth:       JWT tokens
```

## Reglas de desarrollo (obligatorias)

1. Trabaja **módulo por módulo**, no saltes de fase
2. Todo modelo tiene auditoría: `created_by`, `updated_by`, `created_at`, `updated_at`
3. Nunca eliminar registros — siempre soft-delete con campo `is_active` o `estado`
4. Log de auditoría automático en cada acción del sistema
5. Permisos granulares por módulo y operación (leer/crear/editar/aprobar/eliminar)
6. Frontend: tema oscuro por defecto con toggle a light mode
7. Código: inglés para estructura técnica, español para variables de negocio y textos de UI
8. Git desde el primer día con commits descriptivos
9. Etiquetas de normas SIEMPRE con estos colores en toda la UI: ISO 9001 azul · ISO 14001 verde · ISO 45001/Ley 29783 rojo · NTP ISO/IEC 17025 ámbar/amarillo
10. Etiquetas de estados SIEMPRE con colores semánticos: gris registro/inicial · ámbar análisis/revisión · azul ejecución/en proceso · violeta verificación/reabierto · verde cerrado/vigente/completado · rojo rechazado/vencido
12. **Etapa cerrada = solo lectura (ADR-0005)**: en toda secuencia de etapas, al avanzar a la siguiente, los datos de las etapas previas no se modifican, y los de etapas futuras no se capturan por adelantado. Cada modelo con flujo declara `ETAPAS` (nombre, estados en que sigue abierta, campos) y expone `etapas_abiertas`; el servidor rechaza el cambio nombrando etapa y campo, la pantalla deshabilita. Corregir algo cerrado = mecanismo controlado (reabrir con motivo y revisión, nueva versión), nunca "editar".
13. **Tablas alineadas por tipo de dato (ADR-0007, reemplaza «tablas centradas»)**: texto, códigos y nombres a la izquierda; estados, clasificaciones y sí/no al centro (`text-center`); fechas, plazos y cantidades a la derecha (`text-right`); códigos y etiquetas sin partirse. Se aplica con la clase `tabla-sig`; las tablas sin ella conservan el centrado anterior hasta adaptar su módulo. Niveles de riesgo: siempre con la escala única de `frontend/src/lib/severidad.js`. Pantalla principal de módulo: `EncabezadoModulo` + filtros + `Vistas` + tabla `tabla-sig` (+ `EtapaMini` si hay etapas); piloto en Acciones correctivas.
11. **Códigos del SIG solo en el PDF** — NUNCA colocar códigos internos del sistema de gestión (p. ej. MET-PRO-04-r03, SIG-PRO-11, rNN) en textos de la UI ni en comentarios/docstrings del código. Esos códigos se usan EXCLUSIVAMENTE impresos dentro del formato PDF (encabezados). En el código usa descripciones en lenguaje natural (comentarios necesarios, sin códigos).
14. **Terminología: SIG** — el sistema de gestión de Metrindust se llama **SIG** (Sistema Integrado de Gestión). No usar "SGC" ni "SGI" en pantallas, PDF, código ni documentación.
15. **Firma de personas (César, 2026-10-22)**: toda firma de una persona con usuario del sistema es con la **contraseña de su usuario**; quien no tiene usuario (personal sin acceso, terceros) firma con su **PIN personal** (cifrado, se crea en su primera firma, 5 errores lo bloquean). Respaldo: documento firmado en papel adjunto. Helper: `sst.epp_api.firma_persona`.

## Estado actual (octubre 2026) — versión en `backend/VERSION`

| Fase | Estado | Detalle |
|------|--------|---------|
| 0 Cimientos | **Completa** | Proyecto `esynapse`, apps `core` + `esynapse_sig`, usuario personalizado, roles/permisos, auditoría, JWT, dashboard, configuración, licenciamiento; **Organización y personal** (app `organizacion`, 0.8.2, ADR-0006): áreas, puestos y trabajadores únicos para todo el sistema |
| 1 SIG Core | **Construida** | M6 Documentos (en uso), M8 Hallazgos, M9 Acciones correctivas (**cerrado** en 0.2.15; acta por firmar), M10 Auditorías (**cerrado** en 0.2.8; acta por firmar) |
| 2 Laboratorio | **Parcial** | M12 Competencia técnica y M13 Equipos construidos. Faltan M14 Métodos, M15 Ensayos de aptitud, M16 Trabajo no conforme |
| 4 Complementarios | **Iniciada** | M18 Quejas construido (0.3.0, app `quejas`); M7 Procesos (**cerrado** en 0.4.1, app `procesos`; acta por firmar); M17 Cambios construido (0.5.0, app `cambios`); M3 Riesgos construido (0.6.0, app `riesgos`); M2 Requisitos legales construido (0.7.0, app `legal`); M23 SST (0.8.0 a 0.8.8: IPERC, ATS, incidentes, inspecciones, monitoreos, EPP, vigilancia médica, Comité y Programa SSOMA; app `sst`); encuestas de satisfacción después |
| 3 Cadena operativa | **Siguiente** | Diseño aprobado en `PLAN_CADENA_OPERATIVA.md` (DD-03). Arranca por la fase 3.0: PostgreSQL + maestros |

Fichas de cada módulo construido: `docs/modulos/`. Backlog: `PENDIENTES.md`. Historial: `CHANGELOG.md`.

## Método de trabajo (obligatorio) — detalle en `docs/01_metodo_de_trabajo.md`

1. **Ciclo por módulo**: requisitos y criterios de aceptación (ficha en `docs/modulos/`) → diseño (ADR si es decisión de arquitectura) → construcción **con pruebas automáticas** → validación por César (checklist + acta en `docs/validacion/`) → entrega.
2. **Definición de hecho**: pruebas en verde (`Probar.bat`), migración creada y `makemigrations --check` limpio, ficha del módulo actualizada, entrada en `CHANGELOG.md` con la versión, validado en pantalla, sincronizado a la carpeta limpia y en Git.
3. **Toda entrega termina con el bloque**: Versión · Cambios · Migración sí/no · Pasos (cerrar, `Aplicar actualizacion.bat`, `Iniciar`) · Qué probar. Y actualiza `backend/VERSION`, `CHANGELOG.md` y `PENDIENTES.md`.
4. **Pruebas**: cada regla de negocio nueva tiene una prueba que la hace fallar si se rompe. Base: `core/tests/base.py` (`CasoBase`). Se ejecutan con `python manage.py test core esynapse_sig quejas procesos cambios riesgos legal sst organizacion` (en el sandbox se pueden correr instalando `requirements.txt`).
5. **Catálogos únicos**: todo campo «proceso» usa el catálogo oficial (`procesos.Proceso`, solo procesos principales cuando el campo representa un área); todo campo de área, laboratorio, puesto o persona usa Organización y personal (`organizacion.Area`, `Puesto`, `Trabajador`, ADR-0006). Nunca texto libre ni catálogos propios por módulo.
6. **Módulos nuevos (fase 3 en adelante) = app Django propia** (`comercial`, `logistica`, `operaciones`, `finanzas`, `maestros`). `esynapse_sig` no crece; se divide en apps al migrar a PostgreSQL (ADR-0004).
7. **Formatos**: todo PDF replica 1:1 el formato real en `PROCEDIMIENTOS SIG/`; si no está, se pide antes de construir. Verificar que cada dato del PDF tenga captura en pantalla.
8. **Nunca** correr migraciones con el servidor encendido; nunca borrar físicamente; nunca entregar sin pruebas en verde.
9. Decisiones de diseño se escriben el mismo día en `docs/decisiones/` o en el plan correspondiente; preguntas abiertas numeradas (P-nn) en `PENDIENTES.md`.

### Referencia: módulos y operaciones de permisos
```python
MODULOS = [
    'planeamiento', 'legal', 'riesgos', 'indicadores', 'revision_direccion',
    'documentos', 'procesos', 'hallazgos', 'acciones_correctivas', 'auditorias',
    'cumplimiento', 'cambios', 'quejas', 'conocimiento', 'innovacion',
    'competencia_tecnica', 'equipos', 'metodos', 'ensayos_aptitud', 'trabajo_no_conforme',
    'medio_ambiente', 'sst',
    'compras', 'proveedores', 'inventarios', 'mantenimiento',
    'crm', 'logistica', 'ordenes_trabajo',
    'rrhh', 'administracion', 'activos', 'marketing', 'ti',
    'usuarios', 'configuracion',
]

# Operaciones por módulo
OPERACIONES = ['leer', 'crear', 'editar', 'aprobar', 'eliminar']
```

## Arquitectura modular (37 módulos + Logística)

### CAPA 0 — Administración
Usuarios · Roles · Permisos · Log de auditoría · Firma digital · Configuración · Multi-tenant (diseñar ahora, activar al comercializar)

### NIVEL 1 — Estratégicos
| Módulo | Para qué |
|--------|----------|
| M1 Planeamiento | Misión, FODA, objetivos, BSC, KPIs |
| M2 Legal | Matriz legal, obligaciones, alertas |
| M3 Riesgos | Identificación, evaluación P×I, controles |
| M4 Indicadores BI | Dashboards en tiempo real |
| M5 Revisión Dirección | Consolidación de datos + decisiones |

### NIVEL 2 — Operativos

**Bloque A — SIG Core:**
| Módulo | Para qué |
|--------|----------|
| M6 Documentos | Control de versiones, aprobación, firma digital |
| M7 Procesos | Mapa de procesos, caracterizaciones |
| M8 Hallazgos | NC, observaciones, OdM, fuentes múltiples |
| M9 Acciones Correctivas | Causa raíz, plan, verificación de eficacia |
| M10 Auditorías | Programa anual, checklists, informes |
| M11 Cumplimiento | Matriz ISO 9001/14001/45001/17025/Ley 29783 |
| M17 Cambios | Solicitud, impacto, implementación |
| M18 Quejas, Reclamos y Satisfacción | Quejas y reclamos de clientes, encuestas de satisfacción |
| M19 Conocimiento | Lecciones aprendidas, casos técnicos, FAQ |
| M20 Innovación | Proyectos I+D+i, ideas, resultados |

**Bloque B — Laboratorio 17025:**
| Módulo | Para qué |
|--------|----------|
| M12 Competencia | Autorizaciones por método/magnitud, alertas de vencimiento |
| M13 Equipos | Hojas de vida, calibración, verificación, trazabilidad metrológica |
| M14 Métodos | Validación, incertidumbre, control de cambios |
| M15 Ensayos Aptitud | Intercomparaciones, Z Score |
| M16 Trabajo No Conforme | Impacto retroactivo, notificación al cliente |

**Bloque C — SST y MA:**
| Módulo | Para qué |
|--------|----------|
| M22 Medio Ambiente | Aspectos, impactos, residuos, consumos |
| M23 SST | IPERC, inspecciones, incidentes, EPP, vigilancia médica |

**Bloque D — Operaciones:**
| Módulo | Para qué |
|--------|----------|
| M26 Compras | Solicitudes, OC, recepción |
| M27 Proveedores | Registro, evaluación, homologación |
| M28 Inventarios | Almacenes, stock, trazabilidad |
| M34 Mantenimiento | Preventivo, correctivo, MTBF/MTTR |

**Bloque E — Cadena Comercial (OPERATIVO, no soporte):**
| Módulo | Para qué |
|--------|----------|
| M24 CRM | Clientes, cotizaciones, pipeline |
| Logística | Recojo → Ingreso → Distribución → Retiro → Almacén → Devolución |
| M25 OT | Ejecución, resultados, certificados |

El servicio termina cuando el cliente recibe su equipo y su certificado. Facturación y cobranzas son procesos de soporte financiero, no parte del servicio de calibración.

### NIVEL 3 — Soporte
M21 RRHH · M29 Facturación (**FUERA del desarrollo** — solo integración API con Odoo) · M30 Cobranzas · M31 Administración · M32 Contabilidad (**INACTIVO**) · M33 Activos · M35 Marketing · M36 TI · M37 Otros

## Cadena operativa del laboratorio

```
CRM → Cotización → Logística (Recojo) → Recepción e Ingreso
→ OT (se genera SOLO después del ingreso) → Distribución interna
→ Ejecución técnica → Certificado (firma controlada)
→ Logística (Retiro de lab → Almacén tránsito → Devolución al cliente)
→ Factura (API Odoo) → Cobranza
```

## Reglas de negocio críticas

| Regla | Descripción |
|-------|-------------|
| 1 | **No OT sin ingreso** — Sistema bloquea OT si equipo no tiene recepción validada |
| 2 | **No retiro sin calibración** — Logística retira cuando estado = "Calibrado/Completado". No requiere certificado aprobado |
| 3 | **Entrega ≠ Certificado** — Son eventos independientes. Alerta si certificado no enviado post-entrega |
| 4 | **Facturación flexible** — Esquema heredado de cotización: adelantada/parcial/contra entrega/crédito |
| 5 | **Técnico autorizado** — Bloquea asignación si no tiene autorización vigente para método/magnitud |
| 6 | **Patrón vigente** — Bloquea asignación de equipo patrón con calibración vencida |
| 7 | **Firma controlada** — Metrólogo elabora → Encargado revisa → Firmante autorizado firma con su credencial |

## Firma de certificados

| Firmante | Alcance |
|----------|---------|
| Gerente Técnico | Todos los laboratorios |
| Encargado de lab (4-5 personas) | Solo su laboratorio asignado |

Nadie firma con credenciales de otro. Cada firma queda registrada con usuario, timestamp y dispositivo.

## Laboratorios (sede operativa)

| Piso | Laboratorios |
|------|-------------|
| 1° | Recepción/Logística · Longitud (2 ambientes) · Grandes Volúmenes |
| 2° | Análisis Químico · Gases · Topografía y Geodesia · Fuerza y Presión · Temperatura |
| 3° | Masa y Volumen · Electricidad · Tiempo/Frecuencia · Fotometría · Telecomunicaciones · Mantenimiento |

## Roadmap de fases

| Fase | Contenido | Estado |
|------|-----------|--------|
| 0 | Cimientos: auth, roles, permisos, dashboard | Completa |
| 1 | SIG Core: M6, M8, M9, M10 | Construida; M10 cerrado (0.2.8), M9 cerrado (0.2.15), M6/M8 en validación |
| 2 | Laboratorio 17025: M12-M16 | M12 y M13 construidos; M14, M15, M16 pendientes (M14 se adelanta en la fase 3 si la OT lo exige) |
| 3 | Cadena operativa: M24 CRM, Logística, M25 OT y certificados, M30 Cobranzas — subfases 3.0 a 3.7 en `PLAN_CADENA_OPERATIVA.md` | Siguiente |
| 4 | Complementarios: M3, M7, M11, M17, M18, M22, M23 | M18 Quejas (0.3.0) construido; M7 Procesos cerrado (0.4.1); M17 Cambios (0.5.0), M3 Riesgos (0.6.0) y M2 Legal (0.7.0) construidos; M23 SST en curso (0.8.0 IPERC y ATS; 0.8.1 ATS en campo; 0.8.2 Organización y personal; 0.8.3 alineación con Organización; 0.8.4 incidentes, accidentes, enfermedades y estadísticas; 0.8.5 saneamiento y modo pruebas; 0.8.6 inspecciones y monitoreos; 0.8.7 EPP y vigilancia médica; 0.8.8 Comité y Programa SSOMA; M22 en 0.9.0) |
| 5 | Soporte y BI: M21, M26-M28, M34, M4, M5, IA | — |

Decisiones ya tomadas para la fase 3 (no reabrir sin ADR nuevo): PostgreSQL y firma PAdES (ADR-0002); OT general con líneas por equipo y laboratorio, certificado por línea, series por tipo de servicio con reinicio anual (ADR-0003); apps por módulo (ADR-0004).

## Carpeta canónica limpia — "eSYNAPSE 360 GitHub/"

Dentro de la carpeta de trabajo existe `eSYNAPSE 360 GitHub/`: el sistema SOLO con los
archivos necesarios y **siempre actualizado**, listo para instalar/publicar (GitHub).

Reglas permanentes:
- La carpeta de trabajo (`eSYNAPSE 360`) es el **taller**: pruebas, scripts temporales,
  diagnósticos, copias de respaldo, etc.
- **La replicación la hace `Sincronizar carpeta limpia.bat`** (César lo ejecuta en su PC al
  aceptar una entrega): copia `backend/`, `frontend/`, `docs/` y los archivos de raíz
  (README, CLAUDE, CHANGELOG, planes, backlog, scripts). El asistente **no** copia archivos a
  mano a la carpeta limpia (la copia desde el sandbox escribía sobre una vista desactualizada).
- En la carpeta limpia **NUNCA** va basura: nada de `__pycache__`, `venv`, `node_modules`,
  `dist`, `db.sqlite3`/`*.sqlite3`, `media/`, `certificados/`, `backups/`, `*.log`, `*.bak`,
  `_renametest3/`, scripts de prueba/diagnóstico (`diagnostico_firma.py`,
  `limpiar_documentos_prueba.py`, `renombrar_sgi_a_sig.py`), `Guia.txt` (credenciales), ni temporales.
- El git del taller **ignora** `eSYNAPSE 360 GitHub/` (no la versiona; es un snapshot de fuente
  limpia, no un sub-repo).

## Nota para el asistente sobre el entorno

- Los archivos reales se leen y escriben con las herramientas de archivo (Read/Edit/Write/Grep).
  La vista del sandbox (`/sessions/.../mnt/`) sirve para ejecutar comandos (pruebas, compilación,
  scripts) y normalmente está al día, pero ante una discrepancia manda la herramienta de archivo.
- Para correr la suite en el sandbox: `pip install -r backend/requirements.txt --break-system-packages`
  y `python3 manage.py test core esynapse_sig quejas procesos cambios riesgos legal sst organizacion` desde `backend/`. Para el frontend, validar sintaxis
  con esbuild (`transformSync`, loader jsx).
