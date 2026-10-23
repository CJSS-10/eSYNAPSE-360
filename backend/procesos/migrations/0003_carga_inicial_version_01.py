"""Las fichas de la carga inicial empiezan en la versión 01 (decisión de César,
2026-10-21): se renumeran las que entraron como 02 y aún no tienen otra versión.
La primera versión no lleva motivo de cambio."""
from django.db import migrations

MOTIVO = 'Carga inicial desde las fichas en Excel'


def renumerar(apps, schema_editor):
    Ficha = apps.get_model('procesos', 'Ficha')
    for f in Ficha.objects.filter(version='02', estado='borrador', motivo_cambio__startswith=MOTIVO):
        if not Ficha.objects.filter(proceso_id=f.proceso_id).exclude(pk=f.pk).exists():
            f.version = '01'
            f.motivo_cambio = ''
            f.save(update_fields=['version', 'motivo_cambio'])


class Migration(migrations.Migration):

    dependencies = [('procesos', '0002_carga_inicial')]

    operations = [migrations.RunPython(renumerar, migrations.RunPython.noop)]
