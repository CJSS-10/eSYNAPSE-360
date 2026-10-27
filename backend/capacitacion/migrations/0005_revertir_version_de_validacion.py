"""
Durante la validación en pantalla, reenviar el contenido de la inducción sin cambios reales creó por error la versión 2
(solo se normalizó la forma de los datos: claves vacías y tipos). Se vuelve a la versión 1 sin esa entrada del historial;
el contenido es el mismo.
"""
from django.db import migrations


def revertir(apps, schema_editor):
    Plantilla = apps.get_model('capacitacion', 'PlantillaInduccion')
    for pl in Plantilla.objects.filter(version=2):
        h = pl.historial or []
        if len(h) == 1 and h[0].get('motivo') == 'validación':
            pl.version = 1
            pl.historial = []
            pl.save(update_fields=['version', 'historial'])


class Migration(migrations.Migration):

    dependencies = [('capacitacion', '0004_contenido_induccion_versionado')]

    operations = [migrations.RunPython(revertir, migrations.RunPython.noop)]
