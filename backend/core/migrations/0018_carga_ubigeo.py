"""Carga el catálogo completo de ubigeos del Perú (1 893 distritos, 196 provincias, 25 departamentos). Si se vuelve a
ejecutar con un archivo más reciente, agrega los distritos nuevos y actualiza los nombres; no borra ninguno."""
import json
from pathlib import Path

from django.db import migrations

ARCHIVO = Path(__file__).resolve().parent.parent / 'datos' / 'ubigeo_peru.json'


def cargar(apps, schema_editor):
    Ubigeo = apps.get_model('core', 'Ubigeo')
    datos = json.loads(ARCHIVO.read_text(encoding='utf-8'))['distritos']
    existentes = set(Ubigeo.objects.values_list('codigo', flat=True))
    nuevos = [Ubigeo(codigo=c, departamento=d, provincia=p, distrito=x) for c, d, p, x in datos if c not in existentes]
    Ubigeo.objects.bulk_create(nuevos, batch_size=500)
    for c, d, p, x in datos:
        if c in existentes:
            Ubigeo.objects.filter(codigo=c).update(departamento=d, provincia=p, distrito=x)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_ubigeo'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
