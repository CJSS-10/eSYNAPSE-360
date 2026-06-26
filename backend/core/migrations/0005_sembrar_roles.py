from django.db import migrations

T = ['leer', 'crear', 'editar', 'aprobar', 'eliminar']
CRUD = ['leer', 'crear', 'editar', 'eliminar']
RCEA = ['leer', 'crear', 'editar', 'aprobar']
RCE = ['leer', 'crear', 'editar']
RA = ['leer', 'aprobar']
RE = ['leer', 'editar']
RC = ['leer', 'crear']
R = ['leer']

ROLES = [
    ('Administrador de Sistema', 'Gestiona usuarios, roles y la marca de la empresa.', True, {
        'usuarios': CRUD, 'configuracion': ['leer', 'editar']}),
    ('Gerente SIG', 'Control total del Sistema Integrado de Gestión.', False, {
        'documentos': T, 'hallazgos': T, 'acciones_correctivas': T, 'auditorias': T,
        'procesos': RCEA, 'riesgos': RCEA, 'cumplimiento': RCEA, 'cambios': RCEA,
        'quejas': RCEA, 'indicadores': RCE, 'revision_direccion': RCEA,
        'planeamiento': RCEA, 'legal': RCEA, 'conocimiento': RCEA, 'innovacion': RCEA}),
    ('Asistente SIG', 'Elabora y registra; sin facultad de aprobar.', False, {
        'documentos': RCE, 'hallazgos': RCE, 'acciones_correctivas': RCE,
        'auditorias': RCE, 'quejas': RCE, 'procesos': RCE}),
    ('Gerente Técnico', 'Firma certificados y aprueba documentos técnicos.', False, {
        'documentos': RCEA, 'hallazgos': RCEA, 'acciones_correctivas': RA, 'auditorias': RA,
        'competencia_tecnica': RCEA, 'equipos': RCEA, 'metodos': RCEA,
        'ensayos_aptitud': RCEA, 'trabajo_no_conforme': RCEA, 'ordenes_trabajo': RA}),
    ('Encargado de Laboratorio', 'Gestiona y firma lo de su laboratorio.', False, {
        'documentos': RCE, 'equipos': RCEA, 'metodos': RCEA, 'ensayos_aptitud': RCEA,
        'trabajo_no_conforme': RCEA, 'competencia_tecnica': R, 'hallazgos': RCE,
        'acciones_correctivas': RCE, 'ordenes_trabajo': RCEA}),
    ('Metrólogo / Técnico', 'Ejecuta calibraciones y registra resultados.', False, {
        'documentos': R, 'equipos': RCE, 'metodos': R, 'ensayos_aptitud': RCE,
        'ordenes_trabajo': RCE, 'hallazgos': RC, 'acciones_correctivas': RE,
        'trabajo_no_conforme': RC}),
    ('Auditor Interno', 'Planifica y ejecuta auditorías internas.', False, {
        'auditorias': RCEA, 'hallazgos': RCE, 'documentos': R, 'acciones_correctivas': R}),
    ('Responsable de Área', 'Implementa acciones y aporta evidencias.', False, {
        'hallazgos': RE, 'acciones_correctivas': RE, 'documentos': R, 'auditorias': R}),
    ('Colaborador', 'Acceso básico: reportar hallazgos/quejas y consultar.', False, {
        'documentos': R, 'hallazgos': RC, 'quejas': RC}),
]


def sembrar(apps, schema_editor):
    Rol = apps.get_model('core', 'Rol')
    Permiso = apps.get_model('core', 'Permiso')
    for nombre, desc, es_admin, permisos in ROLES:
        rol, creado = Rol.objects.get_or_create(
            nombre=nombre, defaults={'descripcion': desc, 'es_admin_sistema': es_admin})
        if not creado:
            continue  # respeta personalización si el rol ya existe
        for modulo, ops in permisos.items():
            for op in ops:
                Permiso.objects.get_or_create(
                    rol=rol, modulo=modulo, operacion=op, defaults={'permitido': True})


def revertir(apps, schema_editor):
    Rol = apps.get_model('core', 'Rol')
    Rol.objects.filter(nombre__in=[r[0] for r in ROLES]).delete()


class Migration(migrations.Migration):
    dependencies = [('core', '0004_sembrar_config_modulos')]
    operations = [migrations.RunPython(sembrar, revertir)]
