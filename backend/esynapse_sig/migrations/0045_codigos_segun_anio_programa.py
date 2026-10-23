"""
Corrección única: el código de una auditoría lleva el año del programa anual
al que pertenece. Las auditorías registradas antes de esta regla (o movidas
de programa) que aún no se ejecutaron reciben el siguiente correlativo del
año de su programa. Las que ya están en ejecución o cerradas conservan su
código, porque sus actas y listas ya lo llevan impreso.
"""
from django.db import migrations


def recodificar(apps, schema_editor):
    Auditoria = apps.get_model('esynapse_sig', 'Auditoria')
    pendientes = (Auditoria.objects.filter(programa__isnull=False, estado__in=('programada', 'planificada'))
                  .select_related('programa').order_by('created_at', 'pk'))
    for aud in pendientes:
        sufijo = f'-{aud.programa.anio}'
        if aud.codigo.endswith(sufijo):
            continue
        ultimo = (Auditoria.objects.filter(codigo__endswith=sufijo)
                  .order_by('-codigo').values_list('codigo', flat=True).first())
        n = int(ultimo.split('-')[1]) + 1 if ultimo else 1
        aud.codigo = f'AI-{n:02d}{sufijo}'
        aud.save(update_fields=['codigo'])


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0044_programa_bloqueo_revision'),
    ]

    operations = [
        migrations.RunPython(recodificar, migrations.RunPython.noop),
    ]
