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

En Windows, el script `Iniciar eSYNAPSE 360.bat` (raíz del proyecto) arranca ambos servidores y abre el navegador.

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
| 1 | SGI Core: Documentos (M6), Hallazgos (M8), Acciones Correctivas (M9), Auditorías (M10) | ⏳ Próxima |
| 2 | Laboratorio 17025: Competencia, Equipos, Métodos, Ensayos de Aptitud, TNC (M12–M16) | Pendiente |
| 3 | Cadena operativa: CRM, Logística, Órdenes de Trabajo, Cobranzas | Pendiente |
| 4 | Complementarios: Riesgos, Procesos, Cumplimiento, Cambios, Quejas, MA, SST | Pendiente |
| 5 | Soporte y BI: RRHH, Compras, Inventarios, Mantenimiento, Indicadores, IA | Pendiente |

## Documentación del proyecto

- `CLAUDE.md` — instrucciones de desarrollo, arquitectura modular y reglas de negocio
- `SIGE_Flujos_Detallados.md` — flujos paso a paso de cada módulo

---

*Proyecto privado de Metrindust S.A.C. — Todos los derechos reservados.*
