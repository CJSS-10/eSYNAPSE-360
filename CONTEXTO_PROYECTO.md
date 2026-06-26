# eSYNAPSE 360° — Contexto del proyecto (handoff)

> Documento vivo para continuar el desarrollo en cualquier chat o con cualquier IA.
> **Mantener actualizado en cada cambio.** Última actualización: 2026-06-25.

---

## 1. Qué es

**eSYNAPSE 360°** es un Sistema Integrado de Gestión Empresarial (SGI) construido a la
medida de **Metrindust S.A.C.** (laboratorio de calibración multimagnitud acreditado
ISO/IEC 17025:2017 ante INACAL, Lima–Perú) con el objetivo doble de:

1. Usarlo internamente para unificar calidad, laboratorio, operaciones y comercial.
2. **Comercializarlo como SaaS** (white-label + licenciamiento por módulos) a otros
   laboratorios y empresas.

> Nota de marca: el producto se llama **eSYNAPSE 360°** en todo lo visible al usuario.
> Paquetes Python: proyecto Django `esynapse` y app de negocio `esynapse_sig` (renombrados
> desde `sige`/`sig` el 2026-06-25; la app `core` conserva su nombre). El nombre/sigla/logo/color se editan en runtime
> desde Configuración (singleton `ConfiguracionSistema`).

### Empresa (datos de referencia)
- Acreditación: ISO/IEC 17025:2017 (INACAL). Certificaciones ISO 9001/14001/45001 (Bureau Veritas).
- ~35 personas · ~534 OTs/mes · ~2,126 equipos calibrados/mes · 100+ clientes · 2 sedes.
- ERP actual: Odoo (sólo integración API para facturación; fuera del alcance del build).

---

## 2. Stack y estructura

```
Backend:   Django 5.2 · DRF · SimpleJWT · SQLite (dev) → PostgreSQL (prod)
Frontend:  React 18 · Vite · Tailwind · lucide-react · (Recharts/Framer previstos)
Auth:      JWT (access/refresh) · firma PAdES con CA interna + endesive
```

```
D:\eSYNAPSE 360\
├─ CLAUDE.md                  # instrucciones maestras del proyecto (reglas obligatorias)
├─ CONTEXTO_PROYECTO.md       # este archivo (handoff)
├─ backend\
│  ├─ manage.py
│  ├─ esynapse\                   # settings, urls raíz
│  ├─ core\                   # usuarios, roles/permisos, auditoría, configuración/licencias
│  │  ├─ models.py            # Usuario, Rol, Permiso, RolUsuario, LogAuditoria,
│  │  │                       # ConfiguracionSistema, ModuloHabilitado
│  │  ├─ permissions.py       # PermisoModular, SoloAdministradores, SoloPropietario
│  │  ├─ configuracion.py     # endpoints config pública/edición + toggle de módulos
│  │  ├─ signals.py           # auditoría automática (pre/post_save, pre_delete, login)
│  │  ├─ middleware.py        # request/usuario actual por hilo
│  │  └─ migrations\          # 0001..0007 (config 0003/0004, roles 0005, admin sistema 0006/0007)
│  └─ esynapse_sig\                    # módulos del negocio (M6..M13, etc.)
│     ├─ models.py            # ~1086 líneas (ver §5)
│     ├─ serializers.py
│     ├─ views.py             # ViewSets DRF
│     ├─ panel.py             # MisTareasView (buzón) + CalendarioView (agregadores)
│     ├─ urls.py              # router DRF
│     └─ migrations\          # 0001..0018 (M13 reconstruido en 0018)
└─ frontend\
   └─ src\
      ├─ App.jsx, main.jsx
      ├─ context\  AuthContext.jsx · ConfigContext.jsx
      ├─ components\  Layout.jsx (buzón/campana) · Sidebar.jsx (marca+filtro módulos) · Modal.jsx
      ├─ lib\  api.js · modulos.js
      └─ pages\  Documentos · Hallazgos · AccionesCorrectivas · Auditorias · Equipos
                 · Roles · Usuarios · Configuracion · MisTareas · Calendario · Login

```

---

## 3. Reglas obligatorias (de CLAUDE.md, resumidas)

1. Trabajar **módulo por módulo**, respetando las fases.
2. Auditoría en todo modelo: `created_by/updated_by/created_at/updated_at`.
3. **Nunca borrar** — soft delete (`is_active` o `estado`).
4. Log de auditoría automático en cada acción (vía signals).
5. Permisos granulares por módulo y operación (leer/crear/editar/aprobar/eliminar).
6. Frontend: tema oscuro por defecto con toggle claro.
7. Código en inglés (estructura) / español (negocio y UI).
8. Git desde el día 1 con commits descriptivos.
9. **Colores de normas (SIEMPRE):** ISO 9001 azul · ISO 14001 verde · ISO 45001/Ley 29783 rojo · NTP ISO/IEC 17025 ámbar.
10. **Colores de estado (SIEMPRE):** gris inicial/registro · ámbar análisis/revisión · azul ejecución/en proceso · violeta verificación/reabierto · verde cerrado/vigente/completado · rojo rechazado/vencido.

Además (acordado en sesión):
- **No mostrar al usuario los códigos de procedimiento de Metrindust** (MET-PRO, SIG-PRO, etc.).
  Pueden quedar en comentarios internos del código, nunca en la UI.
- Correlativos en formato **PREFIJO-NNN-AAAA** (NC/OBS/ODM/SAC, informes, etc.).
- Modelo comercial de **dos niveles de administración** (ver §6).

---

## 4. Estado por módulo (lo construido)

| Módulo | Estado | Notas |
|--------|--------|-------|
| Capa 0 — Usuarios/Roles/Permisos/Auditoría | ✅ | Usuario custom, Rol+Permiso granular, LogAuditoria por signals. |
| Capa 0 — Configuración white-label + Licenciamiento | ✅ | `ConfiguracionSistema` (marca) + `ModuloHabilitado` (licencias con dependencias). |
| M6 Documentos | ✅ | Versionado, flujo elaboración→revisión→aprobación, **firma electrónica PAdES** (CA interna + endesive), **bitácora de archivos** (ArchivoVersion), **candado** (requiere_recarga), historial de observaciones con adjuntos, versión vigente + etiqueta de versión en proceso. |
| M8 Hallazgos | ✅ | Código NC/OBS/ODM-NNN-AAAA. **Triaje**: NC (Mayor/Menor) → botón **Generar SAC** (deriva a M9). Las etapas de tratamiento de NC NO viven aquí (van en M9). |
| M9 Acciones Correctivas (SAC) | ✅ | `SolicitudAC` (SAC-NNN-AAAA) + `AccionSAC`; causa raíz, plan, verificación de eficacia; conectado a Hallazgos. |
| M10 Auditorías | ✅ | Programa anual, plan/equipo, ejecución, listas de verificación, catálogo `RequisitoNorma` (4 normas), hallazgos que alimentan M8/M9, informe. |
| M13 Equipos e Instrumentos | ✅ (reconstruido) | Inventario + **Hoja de Vida con pestañas** (ver §5.13). Código **asignado por el usuario**. |
| Buzón (Mis Tareas) + Calendario | ✅ | Agregadores transversales con filtro por persona; alertas de calibración. |
| Roles recomendados (plantillas) | ✅ | 9 roles sembrados y editables. |

**Fase actual del roadmap:** Fase 2 (Laboratorio 17025). Hecho M13; pendientes M12 Competencia,
M14 Métodos, M15 Ensayos de aptitud, M16 Trabajo No Conforme, y MET-PRO-02 Condiciones Ambientales.

---

## 5. Modelo de datos clave (app `esynapse_sig`)

### M6 Documentos
`Documento`, `VersionDocumento` (estado borrador/revision/aprobacion/vigente/obsoleto,
`requiere_recarga` = candado, `fecha_proxima_revision`), `ObservacionVersion` (`resuelta`),
`ArchivoVersion` (bitácora append-only de cada archivo subido por etapa),
`FirmaVersion` (PAdES), `VerificacionExterna`.

### M8/M9
`Hallazgo` (codigo PREFIJO-NNN-AAAA, tipo NC/OBS/ODM, severidad, `responsable`, `estado`,
FK `auditoria`), `SolicitudAC` (SAC-NNN-AAAA, `responsable`, `verificador`, `estado`),
`AccionSAC` (tipo, `responsable`, `fecha_propuesta`, `estado`).

### M10
`Auditoria` (AI-NN-AAAA), `ProgramaAuditoria`, `EquipoAuditoria`, `ActaAuditoria`,
`ListaVerificacion`, `ItemVerificacion`, `RequisitoNorma` (catálogo de las 4 normas).

### M13 Equipos (reconstruido — calca el Excel de la Hoja de Vida)
- **`Equipo`** = ficha técnica. Campos: `codigo` (**lo asigna el usuario**, único, ya NO autogenerado),
  `magnitud`, `clasificacion` (patrón referencia/verificación/trabajo / equipamiento), `nombre`,
  `marca`, `modelo`, `serie`, `procedencia`, `intervalo_indicacion`, `division_escala`,
  `clase_exactitud`, `resolucion`, `cantidad` (alcance/cantidad), `material`, `tipo_indicacion`,
  `laboratorio`, `instructivo`, `manual`, `criterio_aceptacion`, `exactitud_asignada`,
  `inicio_servicio`, `estado` (operativo/calibrado/inoperativo/baja), `requiere_calibracion`,
  `n_certificado`, `fecha_ultima_calibracion`, `fecha_proxima_calibracion`, `periodicidad_meses`.
  - `actualizar_calibracion()` recalcula última/próxima/n_certificado a partir del **último
    registro de calibración** (regla "patrón vigente").
- **`RegistroEquipo`** = bitácora unificada de las 6 pestañas de la Hoja de Vida.
  `tipo` ∈ {calibracion, mantenimiento, verificacion, comprobacion_intermedia, caracterizacion, suceso}.
  Campos: `frecuencia`, `numero_documento` (N° cert/informe), `descripcion` (en 'suceso' = Sucesos),
  `fecha`, `fecha_proxima` (en 'suceso' = fecha de solución), `observaciones`, `vb` (V°B°), `archivo`.
- **`ActividadPrograma`** = programa anual (r03): tipo, año, frecuencia, meses[].
- **`MovimientoEquipo`** = control de salida/entrada (r09).
- **`InformeEquipo`** = informes técnicos con archivo (r05/r06/r07) — se mantiene en backend;
  en la UI nueva el adjunto del propio registro de bitácora cubre el caso común.
- **`CartaTrazabilidad`** = trazabilidad metrológica por magnitud (r04).

Prefijos de magnitud (para informes, NO para el código del equipo que ahora es manual):
masa=M, temperatura=TH, electricidad=ET, presión=FP, longitud=LA, grandes_volumenes=GV, analisis_quimico=AQ.

---

## 6. Modelo comercial (dos niveles de administración)

- **Propietario del sistema (superusuario / dueño SaaS)** — permiso `SoloPropietario` (is_superuser):
  controla **identidad del producto** (nombre/sigla/logo/color) y **licenciamiento de módulos**
  (`ModuloHabilitado`, con dependencias y activación en cascada). Puede editar todo, incluidos los
  roles marcados como admin de sistema.
- **Administrador de Sistema (del cliente)** — permiso `SoloAdministradores` (superuser OR `es_admin_sistema`):
  gestiona **usuarios, roles y el nombre de la empresa** (`subtitulo`), nada de licencias ni marca del producto.

Enforcement de licencias: `PermisoModular` consulta `ModuloHabilitado.claves_habilitadas()`
(incluye núcleo `usuarios` y `configuracion`); un módulo deshabilitado → **403 para todos**.

Endpoints (core/configuracion.py):
`GET /api/configuracion/publica/` (AllowAny, marca+módulos; lo usa el frontend al arrancar y en login),
`GET/PATCH /api/configuracion/sistema/` (marca: producto sólo propietario, subtítulo admins),
`GET /api/configuracion/modulos/` y `POST /api/configuracion/modulos/<clave>/` (toggle, sólo propietario).

---

## 7. Convenciones de frontend

- `ConfigContext` carga `/configuracion/publica/` al inicio → marca + `modulos_habilitados`.
- `Sidebar` filtra ítems por `config.modulos_habilitados` (más núcleo `libre`).
- `Layout` tiene la **campana/buzón** (Mis Tareas); estado leído/no leído en `localStorage`
  con clave `t.modulo|t.codigo|t.estado|t.fecha`; al hacer clic la notificación se marca leída.
- Clases utilitarias del tema: `card-sige`, `input-sige`, `btn-primary`, `btn-ghost`, color `sige-*`.
- `Modal` no se cierra al hacer clic fuera (evita perder formularios).
- Colores de estado/normas: aplicar SIEMPRE según reglas 9 y 10.

---

## 8. Reglas de negocio críticas (laboratorio)

1. No OT sin ingreso validado.
2. No retiro sin calibración (estado Calibrado/Completado; no exige certificado aprobado).
3. Entrega ≠ Certificado (eventos independientes; alertar si certificado no enviado tras entrega).
4. Facturación flexible (heredada de la cotización).
5. **Técnico autorizado** — bloquear asignación sin autorización vigente para método/magnitud.
6. **Patrón vigente** — bloquear equipo patrón con calibración vencida (alimentado por `actualizar_calibracion`).
7. **Firma controlada** — metrólogo elabora → encargado revisa → firmante autorizado firma con su credencial.

---

## 9. Lecciones técnicas / hazards (LEER antes de editar)

- **Desincronización file-tool ↔ shell.** Al editar archivos grandes con la herramienta de edición,
  la copia que ve el shell/Python a veces queda **truncada** (se cortan las últimas clases/funciones),
  aunque la vista del editor parezca completa. Ha ocurrido en `models.py`, `serializers.py`,
  `views.py`, `core/signals.py` y `pages/Equipos.jsx`.
  - **Síntomas:** `ImportError: cannot import name X`, `SyntaxError: unterminated string/expected except`,
    `Unexpected end of file` en esbuild.
  - **Regla:** después de CADA edición de backend, verificar en shell con
    `python -c "import ast; ast.parse(open('archivo').read())"` y revisar `tail`. Para frontend,
    transpilar con `npx esbuild --loader:.jsx=jsx <archivo>` **desde /tmp** (no desde frontend/,
    porque el node_modules montado es de Windows y falla en Linux).
  - **Reparación:** `head -n <línea_buena> archivo > /tmp/fix && cat >> /tmp/fix <<'EOF' …cola completa… EOF && cp /tmp/fix archivo`.
  - Limpiar bytecode obsoleto antes de migrar/probar: `find . -name __pycache__ -type d -exec rm -rf {} +`.
- **Pruebas backend** correr sobre copia limpia: `rm -rf /tmp/esynapsebk && cp -r esynapse_sig core esynapse manage.py /tmp/esynapsebk/`
  y ejecutar el script de pruebas **dentro** de /tmp/esynapsebk (cwd importa: el dir del script va al sys.path).
  Las baterías deben incluir el endpoint **LIST**.
- **Caché de prefetch DRF** queda obsoleta tras crear objetos relacionados → re-consultar por pk
  (patrón `_data()` en los ViewSets).

---

## 10. Pendientes / próximos pasos

- [ ] Commit del trabajo reciente (M13 reconstruido, limpieza de códigos de procedimiento, buzón mark-read, este contexto).
- [ ] Fase 2 restante: M12 Competencia técnica, M14 Métodos, M15 Ensayos de aptitud (Z-score), M16 Trabajo No Conforme.
- [ ] MET-PRO-02 Condiciones Ambientales (módulo nuevo).
- [ ] M3 Riesgos (necesario para cerrar el flujo de Observación/OdM de Hallazgos).
- [ ] Fase 3: M24 CRM, Logística, M25 OT, M30 Cobranzas.

---

## 11. Bitácora de cambios de este documento

- 2026-06-24 — Creación. Reconstrucción de M13 Equipos: código manual, modelo `RegistroEquipo`
  (6 bitácoras de la Hoja de Vida), inventario con todas las columnas, Hoja de Vida con pestañas.
  Documentado el hazard de truncación file-tool ↔ shell.
- 2026-06-24 — Alta de equipo alineada al inventario: el formulario de registro muestra
  código, descripción, clasificación, marca, modelo, n° serie, alcance/cantidad, clase,
  resolución, n° de certificado, periodicidad y fecha de última calibración (+ magnitud y
  laboratorio). Al crear con datos de calibración, se siembra el primer registro en la
  pestaña Calibraciones y se calcula la próxima calibración.
- 2026-06-24 — Periodicidad de calibración pasa de meses a **días** (campo `periodicidad_dias`,
  migración sig/0019); la próxima calibración se calcula como última + días. Etiquetas del
  alta afinadas: 'Clase / Exactitud', sin '(lo asignas tú)' ni el formato de fecha entre paréntesis.
- 2026-06-24 — Equipo: nuevos campos 'Proveedor de calibración' y 'Observaciones'
  (migración sig/0020). Visibles en el alta y en la pestaña Ficha Técnica; proveedor también en el inventario.
- 2026-06-24 — Ficha Técnica del equipo reorganizada en secciones (Datos Generales / Especificaciones Técnicas); inicio de servicio captura solo el año (se guarda AAAA-01-01); código editable como campo; el modal muestra solo el nombre en el título; nuevo campo **imagen del equipo** (FileField, migración sig/0021, subida por PATCH multipart).
- 2026-06-24 — ⚠️ La base de datos de desarrollo (db.sqlite3) se corrompió por accesos concurrentes (servidor del usuario + migraciones del asistente sobre el mismo SQLite). Se reconstruyó desde cero (migraciones + semillas). NO correr migraciones contra la base activa con el runserver encendido. Superusuario recreado: usuario 'cesar' (contraseña temporal).
- 2026-06-24 — PDF Hoja de Vida (Ficha Técnica): generador en sig/ficha_pdf.py (reportlab) que
  replica el formato del laboratorio (cabecera con logo de empresa, código/versión/fecha + firmas,
  franjas azul marino #1E3A5C con texto blanco, foto del equipo). Botón 'Generar PDF' en la ficha
  (endpoint equipos/<id>/ficha_pdf). Logo del cliente: campo ConfiguracionSistema.logo_empresa.
  El encabezado (código, versión, fecha de aprobación, siglas Elaborado/Revisado/Aprobado) se VINCULA
  con M6 Documentos: en Configuración se elige el documento de la lista maestra (formato_hv_codigo) y
  el PDF jala su versión vigente y fecha; siglas configurables (formato_hv_elaborado/revisado/aprobado).
  Si no hay documento configurado, usa constantes por defecto. Migración core/0009. Distinción: la
  ESTRUCTURA del formato (campos/diseño) se cambia por código + subir versión; los METADATOS del
  encabezado se gestionan desde el sistema sin código.
- 2026-06-24 — M6 Documentos: jerarquía documental con campo Documento.padre (self-FK, migración
  sig/0022). En 'Nuevo documento', si el tipo es formato/registro/PETS/instructivo aparece el
  selector 'Documento padre' para colgarlo de su procedimiento/manual. Lista y ficha muestran
  padre_codigo/padre_titulo. El icono 'ojo' abre una ficha de solo lectura del documento.
  Retención admite 'Sujeto a Nueva Versión' (centinela anos_retencion=0).
- 2026-06-25 — M6 Documentos: la ficha (modal del 'ojo') ahora se puede **editar previa
  autorización con la contraseña del usuario**. Botón 'Editar' (gated por permiso documentos.editar,
  solo si el documento está activo) → formulario con nombre, tipo, proceso/entidad emisora, soporte,
  retención, normas, documento padre y (externos) verificación + fecha de aprobación. Endpoint
  `POST /documentos/<id>/editar_ficha/` (acción editar_ficha): exige request.user.check_password;
  aplica los cambios vía DocumentoSerializer parcial; en externos la fecha de aprobación va a la
  versión vigente. Auditoría automática: las señales fijan updated_by/updated_at y el log registra
  una entrada EDITAR por cada campo modificado; la ficha muestra 'Última actualización: <fecha y
  hora> por <usuario>'. SIN migración (fecha_aprobacion es write-only del serializer). Commits
  48b3bb1 (backend+frontend) y d9cd14d (api). Entorno: el mount de shell se congeló a media edición
  (snapshots truncados que NO sincronizaban); se verificó con la capa de archivos real + esbuild/ast
  y se reconstruyeron copias completas en el árbol antes de commitear.
- 2026-06-25 — **Renombrado interno de paquetes** a eSYNAPSE: proyecto Django `sige` → `esynapse`
  (settings/urls/wsgi/asgi/manage.py) y app de negocio `sig` → `esynapse_sig` (app_label, INSTALLED_APPS,
  urls, imports, FK string `Hallazgo.auditoria`, las 22 migraciones, `signals._es_auditable`). Strings de
  firma a eSYNAPSE (logger `esynapse.firmas`, cert `ca_esynapse360.pfx`, sufijo `.esynapse.pfx`, salt
  `esynapse-ca-`). `core` y los nombres de tabla derivados (`esynapse_sig_*`) se recrean al re-migrar.
  Validado: `manage.py check` 0 issues, `makemigrations --check` sin cambios, migración limpia crea 22
  tablas + seeds (9 roles, 34 módulos, 129 requisitos) y superusuario. Commits b8816cd, 5cb9f52, 932cbdc.
  Pendiente opcional (NO hecho, gran cambio en frontend sin efecto visible): el token de color CSS
  `sige-*` del tema (tailwind.config.js + cientos de className). El script `renombrar_sgi_a_sig.py` es
  histórico/obsoleto (puede borrarse).
- 2026-06-26 — Creada la **carpeta canónica limpia `eSYNAPSE 360 GitHub/`** (snapshot de fuente
  solo con lo necesario, 110 archivos): backend (esynapse/core/esynapse_sig + manage.py +
  requirements), frontend (src + configs, sin node_modules/dist), docs y assets buenos. Excluida
  toda basura/generado/pruebas. Validada: migración limpia 61 migraciones + seeds. Regla
  permanente (ver CLAUDE.md): replicar cada cambio válido a esa carpeta; el git del taller la
  ignora. Renombrado el doc de flujos a `eSYNAPSE_Flujos_Detallados.md` en la copia.
