"""
Programa anual de auditorías fiel al formato del procedimiento:
clase interna/externa (color en el programa), requisitos a auditar por norma,
mes reprogramado separado del programado y observaciones del programa.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('esynapse_sig', '0040_sincronizar_metadatos')]

    operations = [
        migrations.AddField(
            model_name='auditoria',
            name='clase',
            field=models.CharField(choices=[('interna', 'Interna'), ('externa', 'Externa')],
                                   default='interna', max_length=10, verbose_name='Clase'),
        ),
        migrations.AddField(
            model_name='auditoria',
            name='requisitos_por_norma',
            field=models.JSONField(blank=True, default=dict, verbose_name='Requisitos a auditar por norma'),
        ),
        migrations.AddField(
            model_name='auditoria',
            name='observaciones_programa',
            field=models.TextField(blank=True, verbose_name='Observaciones (programa anual)'),
        ),
        migrations.AddField(
            model_name='auditoria',
            name='mes_reprogramado',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Mes reprogramado'),
        ),
    ]
