"""El Reglamento Interno de Trabajo del programa 2026 (reprogramado de febrero a mayo) se realizó el 2026-05-14: la
carga inicial lo dejó pendiente porque el Excel anotaba la realización en otra fila."""
from datetime import date

from django.db import migrations


def corregir(apps, schema_editor):
    Item = apps.get_model('capacitacion', 'ItemPrograma')
    Item.objects.filter(programa__anio=2026, tema='Reglamento Interno de Trabajo', fecha_realizada__isnull=True,
                        origen='Carga del Excel').update(fecha_realizada=date(2026, 5, 14))


class Migration(migrations.Migration):

    dependencies = [('capacitacion', '0002_carga_inicial')]

    operations = [migrations.RunPython(corregir, migrations.RunPython.noop)]
