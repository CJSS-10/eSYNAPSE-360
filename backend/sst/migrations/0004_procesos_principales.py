"""En SST el proceso es el área (proceso principal del mapa). Los registros que apuntaban a un
subproceso (Logística → Recepción de Equipos y/o Instrumentos) pasan a su proceso principal."""
from django.db import migrations


def a_principal(apps, schema_editor):
    for modelo in ('Puesto', 'FilaIPERC', 'ATS', 'ATSTipo'):
        M = apps.get_model('sst', modelo)
        for obj in M.objects.filter(proceso__padre__isnull=False).select_related('proceso'):
            obj.proceso_id = obj.proceso.padre_id
            obj.save(update_fields=['proceso'])


class Migration(migrations.Migration):

    dependencies = [
        ('sst', '0003_ats_en_campo'),
    ]

    operations = [
        migrations.RunPython(a_principal, migrations.RunPython.noop),
    ]
