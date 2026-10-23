"""
Carga inicial del organigrama y de los puestos (propuesta a revisar en la pantalla de
Organización y personal), y traslado de lo que estaba disperso:
- la lista de áreas y laboratorios de Configuración;
- el área, el cargo y la sigla escritos en cada usuario activo (se crea su trabajador).
Los puestos de SST y los perfiles de Competencia técnica se trasladan en las migraciones
de esas apps.
"""
from django.db import migrations

# (nombre, tipo, depende de, proceso principal, sede, piso, descripción)
AREAS = [
    ('Gerencia General', 'gerencia', None, 'Gestión Estratégica', 'Administrativa', '', ''),
    ('Gerencia SIG', 'gerencia', 'Gerencia General', 'Sistema Integrado de Gestión', 'Administrativa', '', ''),
    ('Gerencia Técnica', 'gerencia', 'Gerencia General', 'Metrología', 'Operativa', '', ''),
    ('Gerencia Comercial y Marketing', 'gerencia', 'Gerencia General', 'Comercial', 'Administrativa', '', ''),
    ('Administración', 'gerencia', 'Gerencia General', 'Recursos Humanos', 'Administrativa', '',
     'Administración, contabilidad y recursos humanos'),
    ('Gerencia de I+D+i', 'gerencia', 'Gerencia General', 'Gestión Estratégica', 'Administrativa', '', ''),
    ('Recursos Humanos', 'area', 'Administración', 'Recursos Humanos', 'Administrativa', '', ''),
    ('Tecnologías de la Información', 'area', 'Administración', 'Sistemas', 'Administrativa', '', ''),
    ('Logística', 'area', 'Gerencia Técnica', 'Metrología', 'Operativa', '1',
     'Recepción, ingreso, distribución y devolución de equipos'),
    ('Mantenimiento', 'area', 'Gerencia Técnica', 'Mantenimiento', 'Operativa', '3', ''),
    ('Laboratorio de Longitud y Ángulo', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '1', ''),
    ('Laboratorio de Grandes Volúmenes', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '1', ''),
    ('Laboratorio de Análisis Químico', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '2', ''),
    ('Laboratorio de Gases', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '2', ''),
    ('Laboratorio de Topografía y Geodesia', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '2', ''),
    ('Laboratorio de Fuerza y Presión', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '2', ''),
    ('Laboratorio de Temperatura y Humedad', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '2', ''),
    ('Laboratorio de Masa y Volumen', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '3', ''),
    ('Laboratorio de Electricidad y Potencia', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '3', ''),
    ('Laboratorio de Tiempo y Frecuencia', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '3', ''),
    ('Laboratorio de Fotometría', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '3', ''),
    ('Laboratorio de Telecomunicaciones', 'laboratorio', 'Gerencia Técnica', 'Metrología', 'Operativa', '3', ''),
]

# Nombres usados hasta ahora (lista de Configuración, área escrita en los usuarios) → área del organigrama.
EQUIVALENCIAS = {
    'dirección': 'Gerencia General', 'direccion': 'Gerencia General', 'alta dirección': 'Gerencia General',
    'calidad': 'Gerencia SIG', 'sig': 'Gerencia SIG', 'laboratorio': 'Gerencia Técnica',
    'comercial': 'Gerencia Comercial y Marketing', 'ti': 'Tecnologías de la Información',
    'recepción y logística': 'Logística', 'longitud': 'Laboratorio de Longitud y Ángulo',
    'temperatura': 'Laboratorio de Temperatura y Humedad', 'electricidad': 'Laboratorio de Electricidad y Potencia',
    'análisis químico': 'Laboratorio de Análisis Químico', 'gases': 'Laboratorio de Gases',
    'fotometría': 'Laboratorio de Fotometría', 'fuerza y presión': 'Laboratorio de Fuerza y Presión',
    'grandes volúmenes': 'Laboratorio de Grandes Volúmenes', 'masa y volumen': 'Laboratorio de Masa y Volumen',
    'telecomunicaciones': 'Laboratorio de Telecomunicaciones', 'tiempo y frecuencia': 'Laboratorio de Tiempo y Frecuencia',
    'topografía y geodesia': 'Laboratorio de Topografía y Geodesia',
}

# (puesto, sigla, área, reporta a, tipo)
PUESTOS = [
    ('Gerente General', 'GG', 'Gerencia General', None, 'propio'),
    ('Gerente SIG', 'GSIG', 'Gerencia SIG', 'Gerente General', 'propio'),
    ('Asistente SIG', 'ASIG', 'Gerencia SIG', 'Gerente SIG', 'propio'),
    ('Gerente Técnico', 'GT', 'Gerencia Técnica', 'Gerente General', 'propio'),
    ('Supervisor de Laboratorio', '', 'Gerencia Técnica', 'Gerente Técnico', 'propio'),
    ('Encargado de Laboratorio', '', 'Gerencia Técnica', 'Supervisor de Laboratorio', 'propio'),
    ('Metrólogo', '', 'Gerencia Técnica', 'Encargado de Laboratorio', 'propio'),
    ('Coordinador Logístico', '', 'Logística', 'Gerente Técnico', 'propio'),
    ('Asistente Logístico', '', 'Logística', 'Coordinador Logístico', 'propio'),
    ('Auxiliar Logístico', '', 'Logística', 'Coordinador Logístico', 'propio'),
    ('Conductor / Operador Logístico', '', 'Logística', 'Coordinador Logístico', 'propio'),
    ('Coordinador de Mantenimiento', '', 'Mantenimiento', 'Gerente Técnico', 'propio'),
    ('Técnico de Mantenimiento', '', 'Mantenimiento', 'Coordinador de Mantenimiento', 'propio'),
    ('Gerente Comercial y Marketing', '', 'Gerencia Comercial y Marketing', 'Gerente General', 'propio'),
    ('Asistente Comercial', '', 'Gerencia Comercial y Marketing', 'Gerente Comercial y Marketing', 'propio'),
    ('Ejecutivo de Ventas', '', 'Gerencia Comercial y Marketing', 'Gerente Comercial y Marketing', 'propio'),
    ('Coordinador de Marketing', '', 'Gerencia Comercial y Marketing', 'Gerente Comercial y Marketing', 'propio'),
    ('Diseñador Gráfico', '', 'Gerencia Comercial y Marketing', 'Coordinador de Marketing', 'propio'),
    ('Gerente de Administración', '', 'Administración', 'Gerente General', 'propio'),
    ('Coordinador Administrativo', '', 'Administración', 'Gerente de Administración', 'propio'),
    ('Asistente Administrativo', '', 'Administración', 'Coordinador Administrativo', 'propio'),
    ('Analista Contable', '', 'Administración', 'Gerente de Administración', 'propio'),
    ('Soporte de TI', '', 'Tecnologías de la Información', 'Gerente de Administración', 'propio'),
    ('Gerente de I+D+i', '', 'Gerencia de I+D+i', 'Gerente General', 'propio'),
    ('Personal de limpieza', '', None, None, 'tercero'),
    ('Encargado de fumigación', '', None, None, 'tercero'),
    ('Encargado de mantenimiento de pozo a tierra', '', None, None, 'tercero'),
    ('Encargado de monitoreo ocupacional', '', None, None, 'tercero'),
    ('Médico ocupacional', '', None, None, 'tercero'),
]
HIST = [{'fecha': '2026-10-22', 'usuario': 'Carga inicial', 'accion': 'Registro (propuesta de organigrama)'}]


def cargar(apps, schema_editor):
    Proceso = apps.get_model('procesos', 'Proceso')
    Area = apps.get_model('organizacion', 'Area')
    Puesto = apps.get_model('organizacion', 'Puesto')
    Trabajador = apps.get_model('organizacion', 'Trabajador')
    Opcion = apps.get_model('core', 'OpcionCatalogo')
    Usuario = apps.get_model('core', 'Usuario')

    def proceso(nombre):
        return Proceso.objects.filter(nombre=nombre, padre__isnull=True).first() if nombre else None

    areas = {}
    for n, (nombre, tipo, padre, proc, sede, piso, desc) in enumerate(AREAS, start=1):
        a, _ = Area.objects.get_or_create(nombre=nombre, defaults={
            'tipo': tipo, 'padre': areas.get(padre), 'proceso': proceso(proc), 'sede': sede, 'piso': piso,
            'descripcion': desc, 'orden': n, 'historial': HIST})
        areas[nombre] = a

    def area_de(texto):
        texto = (texto or '').strip()
        if not texto:
            return None
        nombre = EQUIVALENCIAS.get(texto.lower(), texto)
        a = areas.get(nombre) or Area.objects.filter(nombre__iexact=nombre).first()
        if not a:
            a = Area.objects.create(nombre=nombre, tipo='area', orden=len(areas) + 1,
                                    historial=[{**HIST[0], 'accion': 'Registro (traslado de la lista anterior)'}])
            areas[nombre] = a
        return a

    # Lista anterior de áreas y laboratorios de Configuración.
    for o in Opcion.objects.all():
        a = area_de(o.nombre)
        if o.tipo == 'laboratorio' and a.tipo == 'area' and a.nombre == o.nombre and a.nombre not in {x[0] for x in AREAS}:
            a.tipo = 'laboratorio'
            a.padre = areas['Gerencia Técnica']
            a.save(update_fields=['tipo', 'padre'])
        if not o.is_active and a.nombre not in {x[0] for x in AREAS}:
            a.is_active = False
            a.save(update_fields=['is_active'])

    puestos = {}
    for nombre, sigla, area, jefe, tipo in PUESTOS:
        a = areas.get(area)
        p, _ = Puesto.objects.get_or_create(nombre=nombre, defaults={
            'sigla': sigla, 'area': a, 'reporta_a': puestos.get(jefe), 'tipo': tipo,
            'proceso': a.proceso if a else proceso('Compras'), 'historial': HIST})
        puestos[nombre] = p
    for a_nombre, p_nombre in (('Gerencia General', 'Gerente General'), ('Gerencia SIG', 'Gerente SIG'),
                               ('Gerencia Técnica', 'Gerente Técnico'),
                               ('Gerencia Comercial y Marketing', 'Gerente Comercial y Marketing'),
                               ('Administración', 'Gerente de Administración'),
                               ('Gerencia de I+D+i', 'Gerente de I+D+i'), ('Logística', 'Coordinador Logístico'),
                               ('Mantenimiento', 'Coordinador de Mantenimiento')):
        Area.objects.filter(nombre=a_nombre, responsable__isnull=True).update(responsable=puestos[p_nombre])

    # Usuarios activos con cargo escrito → trabajador vinculado a su puesto.
    for u in Usuario.objects.filter(is_active=True).exclude(cargo=''):
        if Trabajador.objects.filter(usuario=u).exists():
            continue
        p = Puesto.objects.filter(nombre__iexact=u.cargo.strip()).first()
        a = area_de(u.laboratorio) or area_de(u.area)
        if not p:
            p = Puesto.objects.create(nombre=u.cargo.strip(), sigla=(u.sigla_cargo or '').upper(), area=a,
                                      proceso=a.proceso if a else None,
                                      historial=[{**HIST[0], 'accion': 'Registro (cargo escrito en el usuario)'}])
        Trabajador.objects.create(
            nombres=u.first_name or u.username, apellidos=u.last_name or '', puesto=p,
            area=a if a and a != p.area else None, correo=u.email, telefono=u.telefono, usuario=u,
            historial=[{**HIST[0], 'accion': 'Registro (desde el usuario del sistema)'}])


class Migration(migrations.Migration):

    dependencies = [
        ('organizacion', '0001_initial'),
        ('core', '0014_alter_permiso_modulo'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
