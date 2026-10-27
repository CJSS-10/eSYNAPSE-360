"""Carga inicial de Capacitación e inducción: habilita el módulo, registra sus formatos impresos, el contenido de la
inducción (tres partes, del formato de inducción del personal) y los programas anuales de capacitación 2026
(aprobado por el Comité de SST el 2026-05-11) y 2025 (histórico), del Excel del programa.

Correcciones del programa 2026 frente al Excel (revisadas con César, 2026-10-23): el Reglamento Interno de Trabajo
reprogramado de febrero a mayo queda como una sola capacitación con su reprogramación; «Manipulación segura de
sustancias químicas» queda reprogramada al 2026-10-24 (no realizada); el PC-017 se reprogramó del 23/05 al 27/06;
«Puntos a considerar en calibración de autoclaves» es de tipo Metrología y «Pausas activas», de SST."""
import json
from datetime import date
from pathlib import Path

from django.db import migrations

FORMATOS = [
    ('cap_induccion', 'Inducción al personal', 'TH-PRO-01-r05', 160),
    ('cap_lista_asistencia', 'Lista de asistencia', 'TH-PRO-01-r06', 161),
    ('cap_programa', 'Programa anual de capacitación', 'TH-PRO-01-r09', 162),
]
APROBACION_2026 = [('César Soto Soria', 'Presidente del Comité de SST'),
                   ('Erika Vega Rondo', 'Secretaria del Comité de SST'),
                   ('Mauricio López Falcón', 'Miembro titular del Comité de SST'),
                   ('Miryam Canaza Choquehuanca', 'Miembro titular del Comité de SST')]
ELABORADO = {'nombre': 'Ana Aguilar León', 'cargo': 'Asistente SIG', 'sigla': 'ASIG', 'origen': 'Carga del Excel'}


def cargar(apps, schema_editor):
    from django.utils import timezone
    ModuloHabilitado = apps.get_model('core', 'ModuloHabilitado')
    ModuloHabilitado.objects.update_or_create(clave='capacitacion', defaults={
        'nombre': 'Capacitación e Inducción', 'habilitado': True, 'dependencias': [], 'orden': 30})
    FormatoImpreso = apps.get_model('esynapse_sig', 'FormatoImpreso')
    Documento = apps.get_model('esynapse_sig', 'Documento')
    for clave, nombre, codigo, orden in FORMATOS:
        f, _ = FormatoImpreso.objects.update_or_create(
            clave=clave, defaults={'nombre': nombre, 'modulo': 'capacitacion', 'codigo_sgc': codigo, 'orden': orden})
        if not f.documento_id:
            doc = Documento.objects.filter(codigo=codigo, is_active=True).first()
            if doc:
                f.documento = doc
                f.save(update_fields=['documento'])

    datos = json.loads((Path(__file__).resolve().parent.parent / 'datos' / 'carga.json').read_text(encoding='utf-8'))
    Plantilla = apps.get_model('capacitacion', 'PlantillaInduccion')
    for parte, c in datos['plantillas'].items():
        Plantilla.objects.update_or_create(parte=parte, defaults={
            'temas': c['temas'], 'documentos': c['documentos'], 'preguntas': c['preguntas'],
            'evaluacion_url': c.get('evaluacion_url') or ''})

    Programa = apps.get_model('capacitacion', 'ProgramaCapacitacion')
    Item = apps.get_model('capacitacion', 'ItemPrograma')
    Area = apps.get_model('organizacion', 'Area')
    labs = list(Area.objects.filter(tipo='laboratorio', is_active=True))
    hist = [{'fecha': '2026-10-23T00:00', 'usuario': 'Sistema', 'accion': 'Carga inicial del programa en Excel'}]
    for anio, clave in ((2026, 'programa_2026'), (2025, 'programa_2025')):
        if Programa.objects.filter(anio=anio).exists():
            continue
        p = Programa.objects.create(anio=anio, historico=(anio == 2025), elaborado=ELABORADO, historial=hist)
        if anio == 2026:
            p.aprobacion = {'fecha': '2026-05-11', 'origen': 'Carga del Excel', 'observaciones': '',
                            'firmas': [{'nombre': n, 'cargo': c, 'metodo': 'carga', 'fecha': '2026-05-11'}
                                       for n, c in APROBACION_2026]}
            p.aprobado_en = timezone.now()
            p.save(update_fields=['aprobacion', 'aprobado_en'])
        for n, x in enumerate(datos[clave], 1):
            i = Item.objects.create(
                programa=p, orden=n, tema=x['tema'], tipo=x['tipo'], responsable=x['responsable'],
                externo=x['responsable'].lower() == 'externo', alcance=x['alcance'],
                dirigido_texto=x['dirigido_texto'], fecha_programada=date.fromisoformat(x['fecha_programada']),
                horas=x['horas'], fecha_realizada=date.fromisoformat(x['fecha_realizada']) if x['fecha_realizada']
                else None, reprogramaciones=[{**r, 'fecha': '2026-10-23T00:00', 'usuario': 'Carga del Excel'}
                                             for r in x['reprogramaciones']],
                vb=x['vb'], origen='Carga del Excel')
            areas = []
            for a in x['areas']:
                areas += labs if a == 'LABS' else list(Area.objects.filter(nombre=a))
            if areas:
                i.areas.set(areas)


class Migration(migrations.Migration):

    dependencies = [
        ('capacitacion', '0001_initial'),
        ('core', '0016_alter_permiso_modulo'),
        ('esynapse_sig', '0071_alter_hallazgo_fuente'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
