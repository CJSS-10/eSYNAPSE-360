"""
eSYNAPSE 360 — Constantes del sistema.
Módulos y operaciones para el esquema de permisos granulares (CLAUDE.md).
"""

# Módulos del sistema (37 módulos + logística + administración)
MODULOS = [
    # Nivel 1 — Estratégicos
    ('planeamiento', 'Planeamiento Estratégico'),
    ('legal', 'Gestión Legal y Cumplimiento'),
    ('riesgos', 'Riesgos y Oportunidades'),
    ('indicadores', 'Indicadores y Dashboards BI'),
    ('revision_direccion', 'Revisión por la Dirección'),
    # Nivel 2 — Bloque A: SGI Core
    ('documentos', 'Gestión Documental'),
    ('procesos', 'Gestión de Procesos'),
    ('hallazgos', 'Hallazgos'),
    ('acciones_correctivas', 'Acciones Correctivas'),
    ('auditorias', 'Auditorías'),
    ('cumplimiento', 'Cumplimiento Normativo'),
    ('cambios', 'Gestión de Cambios'),
    ('quejas', 'Quejas, Reclamos y Satisfacción'),
    ('conocimiento', 'Gestión del Conocimiento'),
    ('innovacion', 'Innovación I+D+i'),
    # Nivel 2 — Bloque B: Laboratorio 17025
    ('competencia_tecnica', 'Competencia Técnica'),
    ('equipos', 'Equipos e Instrumentos'),
    ('metodos', 'Métodos y Mediciones'),
    ('ensayos_aptitud', 'Ensayos de Aptitud'),
    ('trabajo_no_conforme', 'Trabajo No Conforme'),
    # Nivel 2 — Bloque C: SST y Medio Ambiente
    ('medio_ambiente', 'Medio Ambiente'),
    ('sst', 'Seguridad y Salud en el Trabajo'),
    # Nivel 2 — Bloque D: Operaciones
    ('compras', 'Compras'),
    ('proveedores', 'Proveedores'),
    ('inventarios', 'Inventarios'),
    ('mantenimiento', 'Mantenimiento'),
    # Nivel 2 — Bloque E: Cadena Comercial
    ('crm', 'Comercial y CRM'),
    ('logistica', 'Logística'),
    ('ordenes_trabajo', 'Órdenes de Trabajo'),
    # Nivel 3 — Soporte
    ('rrhh', 'Recursos Humanos'),
    ('administracion', 'Administración'),
    ('activos', 'Activos'),
    ('marketing', 'Marketing'),
    ('ti', 'Tecnologías de la Información'),
    # Capa 0 — Administración del sistema
    ('usuarios', 'Gestión de Usuarios'),
    ('configuracion', 'Configuración del Sistema'),
]

# Operaciones por módulo
OPERACIONES = [
    ('leer', 'Leer'),
    ('crear', 'Crear'),
    ('editar', 'Editar'),
    ('aprobar', 'Aprobar'),
    ('eliminar', 'Eliminar'),  # soft delete
]

# Acciones registradas en el log de auditoría
ACCIONES_AUDITORIA = [
    ('LOGIN', 'Inicio de sesión'),
    ('LOGOUT', 'Cierre de sesión'),
    ('LOGIN_FALLIDO', 'Intento de inicio de sesión fallido'),
    ('CREAR', 'Creación de registro'),
    ('EDITAR', 'Edición de registro'),
    ('ELIMINAR', 'Desactivación de registro (soft delete)'),
    ('APROBAR', 'Aprobación'),
    ('RECHAZAR', 'Rechazo'),
    ('FIRMAR', 'Firma digital'),
    ('EXPORTAR', 'Exportación de datos'),
    ('ACCESO_BLOQUEADO', 'Intento de acceso sin permiso'),
    ('API_EXTERNA', 'Llamada a API externa'),
    ('VER', 'Consulta de registro'),
]


# Dependencias entre módulos (para el licenciamiento por cliente):
# clave -> módulos que deben estar habilitados para que esta funcione.
DEPENDENCIAS_MODULOS = {
    'acciones_correctivas': ['hallazgos'],
    'auditorias': ['hallazgos'],
}

# Módulos núcleo: siempre habilitados, no se venden por separado.
MODULOS_NUCLEO = ['usuarios', 'configuracion']
