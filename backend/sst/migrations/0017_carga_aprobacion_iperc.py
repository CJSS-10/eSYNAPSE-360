"""Retira las filas que la carga inicial tomó por error del pie de cada hoja (datos del empleador: razón social, RUC,
domicilio; dos por hoja) y carga la aprobación vigente de la matriz IPERC: todas las hojas, realizadas y aprobadas
por el Comité de SST el 15 de diciembre de 2025 (según el formato en Excel, firmado en papel)."""
from datetime import date

from django.db import migrations

FIRMAS = [('César Soto Soria', 'Presidente del Comité de SST'), ('Ana Aguilar León', 'Secretaria del Comité de SST'),
          ('Mauricio López Falcón', 'Miembro titular del Comité de SST'),
          ('Miryam Canaza Choquehuanca', 'Miembro titular del Comité de SST')]


def es_pie(f):
    act, pel = (f.actividad or '').strip().upper(), (f.peligro or '').strip().upper()
    return (act.endswith('RUC:') and 'DOMICILIO' in pel) or (act == '20601338204' and pel.startswith('CAL. LOS JAZMINES'))


def cargar(apps, schema_editor):
    Fila = apps.get_model('sst', 'FilaIPERC')
    for f in Fila.objects.filter(is_active=True, estado='vigente'):
        if es_pie(f):
            f.estado = 'retirado'
            f.historial = list(f.historial or []) + [{
                'fecha': '2026-10-22T00:00', 'usuario': 'Sistema', 'accion': 'Retiro',
                'motivo': 'No es una fila de la matriz: era el pie del formato (datos del empleador) tomado por la '
                          'carga inicial.'}]
            f.save(update_fields=['estado', 'historial', 'updated_at'])
    Aprobacion = apps.get_model('sst', 'AprobacionIPERC')
    if Aprobacion.objects.exists():
        return
    areas = sorted(set(Fila.objects.filter(is_active=True).values_list('area', flat=True)))
    if not areas:
        return
    Aprobacion.objects.create(
        fecha=date(2025, 12, 15), areas=areas,
        firmas=[{'nombre': n, 'cargo': c, 'metodo': 'carga', 'fecha': '2025-12-15'} for n, c in FIRMAS],
        observaciones='Aprobación registrada en el formato en Excel (firmas en papel); carga inicial del sistema.',
        registro={'nombre': 'Sistema', 'origen': 'Carga de la matriz en Excel'})


class Migration(migrations.Migration):

    dependencies = [
        ('sst', '0016_aprobacion_iperc_comite'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
