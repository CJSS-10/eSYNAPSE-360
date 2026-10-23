"""
Ajusta los registros existentes a la secuencia del procedimiento:
- Una auditoría "En ejecución" sin acta de apertura queda en "Reunión de
  apertura" (la ejecución empieza con el acta).
- Los hallazgos de auditoría indican su tratamiento: no conformidades por
  acciones correctivas; observaciones y oportunidades de mejora por riesgos y
  oportunidades.
"""
from django.db import migrations


def aplicar(apps, schema_editor):
    Auditoria = apps.get_model('esynapse_sig', 'Auditoria')
    ActaAuditoria = apps.get_model('esynapse_sig', 'ActaAuditoria')
    Hallazgo = apps.get_model('esynapse_sig', 'Hallazgo')
    con_apertura = set(ActaAuditoria.objects.filter(tipo='apertura').values_list('auditoria_id', flat=True))
    for a in Auditoria.objects.filter(estado='en_ejecucion'):
        if a.pk not in con_apertura:
            a.estado = 'apertura'
            a.save(update_fields=['estado'])
    Hallazgo.objects.filter(auditoria__isnull=False, tipo__in=('nc_mayor', 'nc_menor')).update(tratamiento='accion_correctiva')
    Hallazgo.objects.filter(auditoria__isnull=False, tipo__in=('observacion', 'odm')).update(tratamiento='riesgos_oportunidades')


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0052_flujo_auditoria_procedimiento'),
    ]

    operations = [
        migrations.RunPython(aplicar, migrations.RunPython.noop),
    ]
