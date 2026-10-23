# Arquitectura y convenciones

## 1. Stack

| Capa | Tecnología | Notas |
|---|---|---|
| Backend | Python 3.10+ · Django 5 · Django REST Framework · SimpleJWT | Proyecto `esynapse`, apps `core` y `esynapse_sig` |
| Base de datos | SQLite (desarrollo actual) → **PostgreSQL** (decidido, fase 3.0) | ADR-0002 |
| PDF | ReportLab (formatos) · endesive (firma PAdES) · pypdf / pdfplumber | `esynapse_sig/ficha_pdf.py`, `firma_digital.py` |
| Frontend | React 18 · Vite · Tailwind CSS · Lucide · Recharts · Framer Motion · react-router (HashRouter) | Tema oscuro por defecto |
| Autenticación | JWT (access + refresh con lista negra) | `/api/auth/login/`, `/api/auth/refresh/` |

## 2. Estructura del repositorio

```
eSYNAPSE 360/                 ← taller (desarrollo, pruebas, respaldos)
├── backend/
│   ├── esynapse/             configuración Django (settings, urls)
│   ├── core/                 núcleo: usuarios, roles, permisos, auditoría, configuración
│   │   └── tests/            pruebas del núcleo
│   ├── esynapse_sig/         módulos del SIG construidos hasta la fase 2 (M6, M8, M9, M10, M12, M13)
│   │   ├── models.py · views.py · serializers.py · urls.py
│   │   ├── ficha_pdf.py      todos los generadores PDF
│   │   ├── firma_digital.py  firma PAdES
│   │   ├── migrations/
│   │   └── tests/            pruebas de reglas de negocio
│   ├── VERSION               versión instalada
│   ├── media/                archivos subidos (no se versiona)
│   └── certificados/         certificados digitales (.pfx) (no se versiona)
├── frontend/src/
│   ├── pages/                una página por módulo
│   ├── lib/api.js            cliente HTTP: un objeto por recurso
│   ├── lib/modulos.js        menú lateral y rutas por módulo/fase
│   └── components/, context/
├── docs/                     esta documentación
├── PROCEDIMIENTOS SIG/       formatos reales (xlsx/docx) que los PDF replican
├── eSYNAPSE 360 GitHub/      copia limpia para publicar (la genera Sincronizar carpeta limpia.bat)
└── *.bat                     Iniciar · Aplicar actualizacion · Probar · Respaldar · Sincronizar
```

**A partir de la fase 3 cada módulo nuevo es una app Django propia** (`comercial`, `logistica`, `operaciones`, `finanzas`) con sus modelos, vistas, serializers, PDFs y pruebas dentro. `esynapse_sig` no crece más; se dividirá en apps cuando se migre a PostgreSQL (ADR-0004).

## 3. Patrones obligatorios

| Patrón | Regla |
|---|---|
| **Auditoría** | Todo modelo de negocio hereda `AuditableModel` (`created_by`, `updated_by`, `created_at`, `updated_at`). El middleware registra cada acción en `LogAuditoria` (usuario, acción, módulo, entidad, valor anterior/nuevo, IP). |
| **Sin borrado físico** | `destroy` pone `is_active=False` (o el `estado` terminal). Las listas filtran `is_active=True` salvo `?incluir_inactivos=1`. |
| **Permisos** | Cada ViewSet declara `modulo = '...'`. `PermisoModular` resuelve la operación (`leer/crear/editar/aprobar/eliminar`) por la acción; las `@action` declaran la suya con `nombre.operacion = 'aprobar'`. Un ViewSet sin `modulo` solo lo usa el superusuario. |
| **Licenciamiento** | Un módulo deshabilitado en `ModuloHabilitado` queda bloqueado para todos, incluso el superusuario. |
| **Candado de aprobación** | En módulos con control de cambios (Equipos, Competencia; Auditorías pendiente), quien no tiene `aprobar` no modifica: su cambio queda como `SolicitudCambioEquipo` pendiente (HTTP 202) y un aprobador lo aprueba, devuelve o rechaza. |
| **Segundo factor** | Editar fichas de documentos y firmar exige la contraseña del propio usuario en la petición (`password`). |
| **Estados** | Los cambios de estado se hacen solo por acciones explícitas (`planificar`, `cerrar`, `aprobar`…) que validan precondiciones y devuelven 400 con mensaje de negocio; nunca por PATCH del campo `estado` (es `read_only` en los serializers). |
| **Códigos** | Correlativos por tipo y año (`AI-01-2026`, `NC-2026-001`) generados en `save()`; en PostgreSQL pasarán a secuencias. |
| **Colores** | Normas: ISO 9001 azul · 14001 verde · 45001/Ley 29783 rojo · 17025 ámbar. Estados: gris inicial · ámbar revisión · azul en proceso · violeta verificación · verde cerrado/vigente · rojo rechazado/vencido. En la UI y en los PDF. |
| **Códigos del SIG** | Solo en el encabezado de los PDF (`COD_*` en `ficha_pdf.py`) y en esta documentación. Nunca en la interfaz ni en comentarios del código. |
| **Configuración** | Datos de la empresa (nombre, logo, dirección, responsable del SIG, siglas de firma) viven en `ConfiguracionSistema` y los leen todos los PDF. |

## 4. Convenciones de código

- **Idioma**: estructura técnica en inglés (`get_queryset`, `serializer`), variables de negocio y textos de UI en español sin tildes en identificadores (`fecha_compromiso`, `areas_procesos`).
- **Backend**: `snake_case`; una acción de negocio = un `@action` con docstring de una línea en lenguaje natural; errores de negocio con `{'detail': '...'}` y HTTP 400.
- **Frontend**: componentes `PascalCase`, funciones `camelCase`; cada página usa `api.<recurso>.<accion>()` de `lib/api.js`, nunca `fetch` directo; permisos con `tienePermiso(modulo, operacion)`.
- **PDF**: un generador `generar_<formato>_pdf(objeto) -> bytes` por formato; cabecera de control común (`_cabecera_met12`), helpers `_fila_dato`, `_banda`, `_campo`; los datos se leen con `getattr` para poder probarlos con objetos simulados.
- **Migraciones**: una por entrega, con nombre descriptivo (`0039_campos_plan_informe`), docstring que explica el porqué. Las de datos (`RunPython`) incluyen la función inversa.
- **Pruebas**: `APITestCase` sobre `core.tests.base.CasoBase`; nombres en español que describen la regla (`test_no_se_cierra_sin_conclusiones`). Cada ViewSet nuevo trae al menos: permiso denegado, flujo feliz, y cada regla de negocio.

## 5. Lo que cambia al pasar a PostgreSQL (fase 3.0)

- `DATABASES` por variables de entorno (`.env`), `SECRET_KEY` fuera del código, `DEBUG=False` configurable.
- Correlativos por secuencia de base de datos (sin riesgo de duplicado bajo concurrencia).
- Restricciones de integridad y transacciones reales (`select_for_update`, `atomic`) en candado, OT y certificados.
- División de `esynapse_sig` en apps por módulo aprovechando que la base se reconstruye.
- Respaldo con `pg_dump` en lugar de copiar `db.sqlite3`.
