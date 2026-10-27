"""Puesto «Jefe de Laboratorio» (César, 2026-10-27): el procedimiento de trabajos y salidas no conformes le
asigna, con el Gerente Técnico, la autorización de la reanudación de un trabajo técnico. Es un puesto nuevo:
«Supervisor de Laboratorio» y «Encargado de Laboratorio» se mantienen."""
from django.db import migrations

HIST = [{'fecha': '2026-10-27', 'usuario': 'Carga inicial',
         'accion': 'Registro (procedimiento de trabajos y salidas no conformes)'}]


def crear(apps, schema_editor):
    Puesto = apps.get_model('organizacion', 'Puesto')
    if Puesto.objects.filter(nombre__iexact='Jefe de Laboratorio').exists():
        return
    gt = Puesto.objects.filter(nombre__iexact='Gerente Técnico').first()
    ref = Puesto.objects.filter(nombre__iexact='Supervisor de Laboratorio').first() or gt
    Puesto.objects.create(nombre='Jefe de Laboratorio', area=ref.area if ref else None,
                          proceso=ref.proceso if ref else None, reporta_a=gt, historial=HIST)


class Migration(migrations.Migration):

    dependencies = [
        ('organizacion', '0006_sede_ubigeo'),
    ]

    operations = [migrations.RunPython(crear, migrations.RunPython.noop)]
