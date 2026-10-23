"""
Corrección única: las auditorías que ya estaban planificadas (o más avanzadas)
antes de existir el campo "fecha de elaboración del plan" reciben como fecha la
de su última modificación, para que el plan impreso no salga sin fecha.
"""
from django.db import migrations


def completar(apps, schema_editor):
    Auditoria = apps.get_model('esynapse_sig', 'Auditoria')
    for a in Auditoria.objects.filter(fecha_elaboracion_plan__isnull=True).exclude(estado='programada'):
        base = a.updated_at or a.created_at
        if base:
            a.fecha_elaboracion_plan = base.date()
            a.save(update_fields=['fecha_elaboracion_plan'])


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0046_fecha_elaboracion_plan'),
    ]

    operations = [
        migrations.RunPython(completar, migrations.RunPython.noop),
    ]
