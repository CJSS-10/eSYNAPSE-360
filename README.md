# eSYNAPSE 360 — Sistema Integrado de Gestión Empresarial

Plataforma web que unifica los procesos de **Metrindust S.A.C.** (laboratorio de calibración multimagnitud, Lima, Perú): calidad, laboratorio, operaciones, comercial y soporte.

**Acreditación:** ISO/IEC 17025:2017 (INACAL) · **Certificaciones:** ISO 9001, ISO 14001, ISO 45001 (Bureau Veritas)

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Django 5 · Django REST Framework · SimpleJWT |
| Frontend | React 18 · Vite · Tailwind CSS · Lucide Icons |
| Base de datos | SQLite (desarrollo) → PostgreSQL (producción) |
| Autenticación | JWT con refresh y blacklist de tokens |

## Principios de diseño

- **Auditoría total**: todo modelo registra `created_by`, `updated_by`, `created_at`, `updated_at`. Log de auditoría inmutable con usuario, acción, valores anterior/nuevo, IP y dispositivo.
- **Soft delete**: ningún registro se elimina físicamente — solo se desactiva.
- **Permisos granulares**: 36 módulos × 5 operaciones (leer/crear/editar/aprobar/eliminar) por rol. Un usuario con varios roles obtiene la unión de permisos.
- **Firma controlada**: nadie firma con credenciales de otro; cada firma queda registrada con usuario, timestamp y dispositivo.

## Instalación (desarrollo)

### Requisitos
- Python 3.10+
- Node.js 18+
- Git

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver     # http://127.0.0.1:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

En Windows, los scripts de la raíz hacen todo con doble clic:

| Script | Para qué |
|---|---|
| `Iniciar eSYNAPSE 360.bat` | Aplica actualizaciones pendientes y arranca backend + frontend |
| `Aplicar actualizacion.bat` | Aplica migraciones (con el sistema cerrado) |
| `Probar.bat` | Ejecuta las pruebas automáticas (base temporal, no toca datos) |
| `Respaldar.bat` | Respaldo con fecha de base, archivos y certificados |
| `Sincronizar carpeta limpia.bat` | Genera la copia publicable en `eSYNAPSE 360 GitHub/` |

Procedimientos detallados: `docs/03_operacion_en_pc.md`.

### Pruebas

```bash
cd backend
python manage.py test core esynapse_sig quejas procesos cambios riesgos legal sst organizacion
```

## Endpoints principales

| Ruta | Descripción |
|------|-------------|
| `POST /api/auth/login/` | Login JWT (access + refresh) |
| `GET /api/auth/me/` | Usuario autenticado + permisos efectivos |
| `/api/usuarios/` | CRUD de usuarios (DELETE = soft delete + invalida sesiones) |
| `/api/roles/` | CRUD de roles con matriz de permisos anidada |
| `/api/auditoria/` | Log de auditoría (solo lectura, solo administradores) |
| `GET /api/configuracion/catalogo/` | Catálogo de módulos y operaciones |
| `/admin/` | Admin de Django |

## Roadmap

| Fase | Contenido | Estado |
|------|-----------|--------|
| 0 | Cimientos: auth JWT, roles y permisos granulares, log de auditoría, dashboard React | ✅ Completada |
| 1 | SIG Core: Documentos (M6), Hallazgos (M8), Acciones Correctivas (M9), Auditorías (M10) | ✅ Construida · en validación |
| 2 | Laboratorio 17025: Competencia (M12), Equipos (M13) construidos; Métodos, Ensayos de Aptitud, TNC pendientes | ⏳ Parcial |
| 3 | Cadena operativa: CRM, Logística, Órdenes de Trabajo y certificados, Cobranzas (`PLAN_CADENA_OPERATIVA.md`) | ⏳ Próxima |
| 4 | Complementarios: Riesgos, Procesos, Cumplimiento, Cambios, Quejas, MA, SST | Pendiente |
| 5 | Soporte y BI: RRHH, Compras, Inventarios, Mantenimiento, Indicadores, IA | Pendiente |

Versión instalada: `backend/VERSION` · Historial: `CHANGELOG.md` · Backlog: `PENDIENTES.md`.

## Documentación del proyecto

- `docs/README.md` — índice de toda la documentación (método de trabajo, arquitectura, operación, fichas de módulos, decisiones, validación)
- `CLAUDE.md` — instrucciones de desarrollo, reglas de negocio, estado de fases y método de trabajo
- `PLAN_CADENA_OPERATIVA.md` — diseño y fases de la cadena comercial → logística → laboratorio → cobranza
- `SIGE_Flujos_Detallados.md` — flujos funcionales originales por módulo

---

*Proyecto privado de Metrindust S.A.C. — Todos los derechos reservados.*
