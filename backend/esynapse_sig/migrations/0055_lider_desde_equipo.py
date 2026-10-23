"""El auditor líder se define solo en el equipo auditor. Para los registros
existentes: si el equipo no tiene líder y el campo de la auditoría sí, ese
usuario pasa al equipo como líder; si el equipo ya tiene líder, el campo se
ajusta a él (vacío cuando el líder es externo)."""
from django.db import migrations


def unificar_lider(apps, schema_editor):
    Auditoria = apps.get_model('esynapse_sig', 'Auditoria')
    Equipo = apps.get_model('esynapse_sig', 'EquipoAuditoria')
    for a in Auditoria.objects.all():
        lider = Equipo.objects.filter(auditoria=a, rol='lider').order_by('id').first()
        if lider is None:
            if a.auditor_lider_id:
                u = a.auditor_lider
                Equipo.objects.create(auditoria=a, usuario=u, rol='lider',
                                      cargo=getattr(u, 'cargo', '') or 'Auditor líder',
                                      created_by_id=a.created_by_id, updated_by_id=a.updated_by_id)
        elif a.auditor_lider_id != lider.usuario_id:
            Auditoria.objects.filter(pk=a.pk).update(auditor_lider_id=lider.usuario_id)


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0054_trazabilidad_items_hallazgos'),
    ]

    operations = [
        migrations.RunPython(unificar_lider, migrations.RunPython.noop),
    ]
