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

## Fase actual: FASE 0 — Cimientos del sistema

**No avanzar a Fase 1 hasta completar y validar todos los items de Fase 0.**

### Checklist Fase 0:
- [ ] Proyecto Django creado (`sige`) con app `core`
- [ ] Modelo `Usuario` personalizado (extiende AbstractUser)
- [ ] Modelo `Rol` y `Permiso` con permisos granulares
- [ ] Middleware de auditoría automático
- [ ] API base con DRF + JWT
- [ ] Proyecto React creado con diseño del dashboard
- [ ] Sidebar colapsable con todos los módulos
- [ ] Login funcional conectado al backend
- [ ] CRUD de usuarios operativo
- [ ] Pruebas y validación

### Modelo de Usuario personalizado (campos adicionales):
```python
area = models.CharField(max_length=100)
laboratorio = models.CharField(max_length=100, blank=True)
cargo = models.CharField(max_length=100)
telefono = models.CharField(max_length=20, blank=True)
# is_active ya viene en AbstractUser
```

### Modelo de Rol y Permisos:
```python
# Módulos del sistema
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

**Bloque A — SGI Core:**
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

| Fase | Contenido | Tiempo |
|------|-----------|--------|
| 0 | Cimientos: auth, roles, permisos, dashboard | Mes 1 |
| 1 | SGI Core: M6, M8, M9, M10 | Mes 2-3 |
| 2 | Laboratorio 17025: M12-M16 | Mes 4-5 |
| 3 | Cadena operativa: M24, Logística, M25, M30 | Mes 6-8 |
| 4 | Complementarios: M3, M7, M11, M17, M18, M22, M23 | Mes 9-11 |
| 5 | Soporte y BI: M21, M26-M28, M34, M4, M5, IA | Mes 12-14 |

## Primer mensaje a enviar (Fase 0 - Paso 1)

> "Lee las instrucciones del proyecto. Estamos en la Fase 0. Crea el proyecto Django llamado 'sige' con una app 'core'. Necesito: modelo de Usuario personalizado extendiendo AbstractUser con los campos adicionales del AGENTS.md, modelo de Rol y Permiso con permisos granulares por módulo y operación, middleware de auditoría que registre automáticamente cada acción (usuario, acción, módulo, entidad, valor anterior, valor nuevo, timestamp, IP). Configura DRF con JWT. Al terminar, muéstrame los comandos de terminal que debo ejecutar."
