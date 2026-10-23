"""Corrige el tipo de las áreas de la propuesta inicial que la lista anterior marcaba como
laboratorio (p. ej. Mantenimiento), si nadie las ha modificado todavía."""
import importlib

from django.db import migrations

AREAS = importlib.import_module('organizacion.migrations.0002_carga_inicial').AREAS


def corregir(apps, schema_editor):
    Area = apps.get_model('organizacion', 'Area')
    for nombre, tipo, *_ in AREAS:
        a = Area.objects.filter(nombre=nombre).first()
        if a and a.tipo != tipo and len(a.historial or []) <= 1:
            a.tipo = tipo
            a.save(update_fields=['tipo'])


class Migration(migrations.Migration):

    dependencies = [
        ('organizacion', '0002_carga_inicial'),
    ]

    operations = [
        migrations.RunPython(corregir, migrations.RunPython.noop),
    ]
