"""La secretaria actual del Comité de SST 2025-2027 es Erika Vega Rondo (confirmado por César, 2026-10-23; figura así en
el programa anual de capacitación 2026). La aprobación de la matriz IPERC del 15/12/2025 conserva a quien firmó."""
from django.db import migrations


def actualizar(apps, schema_editor):
    Comite = apps.get_model('sst', 'ComiteSST')
    c = Comite.objects.filter(periodo='2025-2027').first()
    if not c or 'Erika Vega Rondo' in (c.observaciones or ''):
        return
    c.observaciones = (c.observaciones or '').replace(
        'Ana Aguilar León (secretaria)', 'Erika Vega Rondo (secretaria actual; antes, Ana Aguilar León)')
    c.historial = list(c.historial or []) + [{'fecha': '2026-10-23T00:00', 'usuario': 'Sistema',
                                              'accion': 'Secretaria actual: Erika Vega Rondo'}]
    c.save(update_fields=['observaciones', 'historial'])


class Migration(migrations.Migration):

    dependencies = [
        ('sst', '0017_carga_aprobacion_iperc'),
    ]

    operations = [
        migrations.RunPython(actualizar, migrations.RunPython.noop),
    ]
