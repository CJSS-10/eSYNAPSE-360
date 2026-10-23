"""
Campos de captura para completar los formatos de auditoría:
- Plan (r02): cronograma de entrevistas y observaciones del plan.
- Informe (r04): lugar y personas entrevistadas.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('esynapse_sig', '0038_acta_seccion3')]

    operations = [
        migrations.AddField(
            model_name='auditoria',
            name='cronograma_entrevistas',
            field=models.JSONField(blank=True, default=list, verbose_name='Cronograma de entrevistas'),
        ),
        migrations.AddField(
            model_name='auditoria',
            name='observaciones_plan',
            field=models.TextField(blank=True, verbose_name='Observaciones del plan'),
        ),
        migrations.AddField(
            model_name='auditoria',
            name='lugar',
            field=models.CharField(blank=True, max_length=200, verbose_name='Lugar donde se realizó la auditoría'),
        ),
        migrations.AddField(
            model_name='auditoria',
            name='personas_entrevistadas',
            field=models.TextField(blank=True, verbose_name='Personas entrevistadas'),
        ),
    ]
