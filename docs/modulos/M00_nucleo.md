# M00 · Núcleo (Capa 0 — Administración)

**App:** `core` · **Estado:** construido, en uso · **Pruebas:** `core/tests/`

## 1. Propósito

Autenticación, usuarios, roles con permisos granulares, log de auditoría inmutable, configuración del sistema (marca y datos de la empresa), licenciamiento por módulos y catálogos de opciones. Todo módulo de negocio se apoya en esto.

## 2. Modelos

| Modelo | Para qué | Campos clave |
|---|---|---|
| `Usuario` (AbstractUser) | Persona que usa el sistema | `area`, `laboratorio`, `cargo`, `sigla_cargo` (ASIG, GSIG, GT, GG: se imprime en la caja de control de los formatos), `telefono`, `foto`, `is_active` (soft delete) |
| `Rol` | Agrupa permisos | `nombre`, `es_admin_sistema` |
| `Permiso` | Una celda de la matriz módulo × operación | `rol`, `modulo` (36 claves), `operacion` (leer/crear/editar/aprobar/eliminar), `permitido` |
| `RolUsuario` | Asignación usuario–rol | un usuario puede tener varios roles: tiene la **unión** de permisos |
| `LogAuditoria` | Registro inmutable de cada acción | usuario, acción, módulo, entidad, valor anterior/nuevo, IP, dispositivo, timestamp |
| `ConfiguracionSistema` | Singleton de marca y empresa | `nombre_sistema`, `subtitulo` (empresa), `direccion`, `responsable_sig`, logos, `color_primario`, siglas de firma de formatos |
| `ModuloHabilitado` | Licenciamiento | `clave`, `habilitado`, `dependencias` |
| `OpcionCatalogo` | Lista anterior de áreas y laboratorios (sin uso desde 0.8.2: se trasladó a Organización y personal) | `tipo`, `nombre`, `orden` |
| `organizacion.Area` · `Puesto` · `Trabajador` | **Organización y personal** (ADR-0006): organigrama (gerencias, áreas, laboratorios), puestos con sigla de firma, línea de reporte y perfil versionado, trabajadores con usuario opcional. El usuario vinculado toma cargo, sigla y área de su puesto | ver `organizacion/models.py` |

## 3. API

| Ruta | Uso |
|---|---|
| `POST /api/auth/login/` · `refresh/` · `verify/` | JWT |
| `GET /api/auth/me/` · `POST /api/auth/cambiar-password/` | Sesión propia |
| `/api/usuarios/`, `/api/roles/`, `/api/permisos/`, `/api/roles-usuarios/` | CRUD (eliminar = desactivar) |
| `/api/auditoria/` | Log (solo administradores) |
| `/api/org-areas/` · `/api/org-puestos/` · `/api/org-trabajadores/` (+ `cesar/`, `reingresar/`, `reactivar/`) | Organización y personal: lectura para todo usuario activo; cambios con el permiso «organización» |
| `GET /api/configuracion/publica/` | Sin login: marca, **versión**, módulos habilitados (la usa la pantalla de login) |
| `GET/PATCH /api/configuracion/sistema/` | Administradores: marca + datos de empresa + siglas de formatos |
| `/api/configuracion/modulos/` · `.../<clave>/toggle/` | Propietario: habilitar/deshabilitar módulos |
| `/api/configuracion/catalogo/`, `/api/opciones-catalogo/` | Catálogos |

## 4. Reglas

- Superusuario pasa todos los permisos **excepto** un módulo deshabilitado.
- Sin `modulo` declarado en un ViewSet, solo el superusuario accede (seguro por defecto).
- Un usuario eliminado queda `is_active=False`; conserva su historial.
- Las acciones 401/403 también se registran en el log (intentos de acceso sin permiso).
- La identidad del producto (nombre del sistema, logo, color) la edita solo el propietario; la de la empresa (nombre, dirección, responsable, logo de empresa) el administrador del cliente.

## 5. Pantallas

`Login`, `Usuarios`, `Roles y permisos` (matriz), `Log de auditoría`, `Configuración`, `Dashboard`, `Mis tareas`, `Calendario`.

## 6. Pendientes

- Multi-tenant: diseñado (configuración y licenciamiento por instalación), no activado.
- Política de contraseñas y bloqueo por intentos (previsto para producción).
- `SECRET_KEY` y `DEBUG` a variables de entorno al pasar a servidor.
