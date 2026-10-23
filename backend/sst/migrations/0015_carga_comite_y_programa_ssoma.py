"""Carga del Comité de SST vigente (constituido el 30 de mayo de 2025, según el Plan anual SSOMA; los miembros se
registran cuando estén en Organización y personal) y del Programa anual SSOMA 2026 (objetivos y actividades del
plan, meses programados y ejecutados y firmas del Excel); registro de sus formatos impresos."""
from datetime import date

from django.db import migrations

OBJETIVOS = [
    ('OSST1', 'Prevenir incidentes, lesiones y enfermedades ocupacionales en el ambiente de trabajo', [
        ('Control y seguimiento', 'Asistente SIG', [3, 6, 9, 12], []),
        ('Cumplir con el mantenimiento de equipos de emergencia', 'Gerente Técnico', [2, 9, 10], [2]),
        ('Verificar el cumplimiento de estándares mediante inspecciones SST', 'Asistente SIG', list(range(1, 13)), [1]),
        ('Identificación de agentes ocupacionales en las instalaciones del laboratorio', 'Asistente SIG', [11], []),
    ]),
    ('OSST2', 'Fortalecer la cultura de seguridad, salud en el trabajo y medio ambiente, y garantizar la participación '
              'de los trabajadores', [
        ('Asegurar el liderazgo, compromiso, participación y consulta de mando en SST', 'Asistente SIG',
         list(range(1, 13)), [1]),
        ('Cumplir con el programa anual de capacitación y entrenamiento en materia de seguridad y medio ambiente',
         'Asistente SIG', list(range(1, 13)), [1]),
        ('Mantener revisados y/o actualizados los documentos de gestión legal y normativa', 'Asistente SIG',
         [2, 3, 5, 6, 7, 9, 10, 11, 12], []),
    ]),
    ('OAM1', 'Prevenir la contaminación ambiental y proteger los recursos naturales en el desarrollo de nuestras '
             'actividades', [
        ('Realizar una correcta gestión de residuos sólidos', 'Asistente SIG', list(range(1, 13)), [1]),
        ('Fortalecer la cultura y toma de conciencia ambiental', 'Asistente SIG', list(range(1, 13)), [1, 2]),
    ]),
]
FORMATOS = [
    ('sst_acta_comite', 'Acta de reunión del Comité de SST', 'SIG-PRO-13-r08', 150),
    ('sst_programa_ssoma', 'Programa anual de seguridad, salud ocupacional y medio ambiente', 'SIG-PL-01-r01', 151),
]
CARGA = {'origen': 'Carga del programa en Excel'}


def cargar(apps, schema_editor):
    FormatoImpreso = apps.get_model('esynapse_sig', 'FormatoImpreso')
    Documento = apps.get_model('esynapse_sig', 'Documento')
    for clave, nombre, codigo, orden in FORMATOS:
        f, _ = FormatoImpreso.objects.update_or_create(
            clave=clave, defaults={'nombre': nombre, 'modulo': 'sst', 'codigo_sgc': codigo, 'orden': orden})
        if not f.documento_id:
            doc = Documento.objects.filter(codigo=codigo, is_active=True).first()
            if doc:
                f.documento = doc
                f.save(update_fields=['documento'])
    Comite = apps.get_model('sst', 'ComiteSST')
    Programa = apps.get_model('sst', 'ProgramaSSOMA')
    Objetivo = apps.get_model('sst', 'ObjetivoSSOMA')
    Actividad = apps.get_model('sst', 'ActividadSSOMA')
    Puesto = apps.get_model('organizacion', 'Puesto')
    hist = [{'fecha': '2026-10-22T00:00', 'usuario': 'Sistema', 'accion': 'Carga inicial'}]
    if not Comite.objects.exists():
        Comite.objects.create(periodo='2025-2027', fecha_instalacion=date(2025, 5, 30), fecha_fin=date(2027, 5, 29),
                              observaciones='Constituido el 30 de mayo de 2025 al superar los 20 trabajadores (Plan '
                                            'anual SSOMA 2026): César Soto Soria (presidente), Ana Aguilar León '
                                            '(secretaria), Miryam Canaza Choquehuanca y Mauricio López Falcón '
                                            '(miembros titulares). Registrar los miembros cuando estén en '
                                            'Organización y personal.', historial=hist)
    if Programa.objects.filter(anio=2026).exists():
        return
    p = Programa.objects.create(
        anio=2026, estado='aprobado', fecha=date(2026, 1, 1), fecha_actualizacion=date(2026, 2, 15),
        recursos='Recurso humano y económico',
        elaborado={'nombre': 'Ana Aguilar León', 'cargo': 'Asistente SIG', 'fecha': '2025-10-15', **CARGA},
        revisado={'nombre': 'César Soto Soria', 'cargo': 'Presidente del Comité de SST', 'fecha': '2025-10-15',
                  **CARGA},
        aprobado=[{'nombre': n, 'cargo': c, 'fecha': '2026-01-31', **CARGA} for n, c in (
            ('César Soto Soria', 'Presidente del Comité de SST'), ('Ana Aguilar León', 'Secretaria del Comité de SST'),
            ('Miryam Canaza Choquehuanca', 'Miembro titular'), ('Mauricio López Falcón', 'Miembro titular'))],
        historial=hist)
    n = 0
    for i, (cod, desc, acts) in enumerate(OBJETIVOS, 1):
        o = Objetivo.objects.create(programa=p, codigo=cod, descripcion=desc, orden=i)
        for nombre, resp, meses, ejec in acts:
            n += 1
            Actividad.objects.create(programa=p, objetivo=o, orden=n, descripcion=nombre, meta='100%',
                                     indicador='N° de actividades ejecutadas / N° de actividades programadas × 100',
                                     responsable=Puesto.objects.filter(nombre=resp).first(), meses=meses,
                                     meses_ejecutados=ejec,
                                     evidencias={str(m): 'Registrado en el programa en Excel' for m in ejec})


class Migration(migrations.Migration):

    dependencies = [
        ('sst', '0014_comite_programa_ssoma_y_cargo_emo'),
        ('organizacion', '0003_corrige_tipo_areas_propuestas'),
        ('esynapse_sig', '0071_alter_hallazgo_fuente'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
