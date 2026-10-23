"""Hallazgos según el procedimiento de no conformidades y acciones correctivas:
- toda NC requiere solicitud de acción correctiva y se trata allí;
- observaciones y oportunidades de mejora abiertas pasan a "Derivado a riesgos
  y oportunidades" (las cerradas se conservan como están);
- cada hallazgo apunta a la solicitud que lo trata (antes solo la solicitud
  apuntaba a su hallazgo de origen)."""
from django.db import migrations


def aplicar(apps, schema_editor):
    Hallazgo = apps.get_model('esynapse_sig', 'Hallazgo')
    SolicitudAC = apps.get_model('esynapse_sig', 'SolicitudAC')
    nc = ('nc_mayor', 'nc_menor')
    Hallazgo.objects.filter(tipo__in=nc).update(requiere_ac=True, tratamiento='accion_correctiva')
    Hallazgo.objects.exclude(tipo__in=nc).update(requiere_ac=False, tratamiento='riesgos_oportunidades')
    (Hallazgo.objects.exclude(tipo__in=nc)
     .filter(estado__in=('registrado', 'en_analisis', 'en_tratamiento', 'reabierto'))
     .update(estado='derivado'))
    for sac in SolicitudAC.objects.filter(is_active=True, hallazgo__isnull=False).order_by('id'):
        Hallazgo.objects.filter(pk=sac.hallazgo_id, sac__isnull=True).update(sac=sac)


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0061_hallazgo_sac_reclasificaciones'),
    ]

    operations = [
        migrations.RunPython(aplicar, migrations.RunPython.noop),
    ]
