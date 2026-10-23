"""
Lista de verificación: el texto de cada requisito pasa a texto largo (las
cláusulas completas del formato 17025 superan los 600 caracteres) y cada fila
indica su bloque (requisitos de la norma / ítems de seguimiento).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0047_fecha_plan_existentes'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemverificacion',
            name='bloque',
            field=models.CharField(choices=[('requisitos', 'Requisitos de la norma'), ('seguimiento', 'Ítems para auditorías internas de seguimiento')], default='requisitos', max_length=12, verbose_name='Bloque'),
        ),
        migrations.AddField(
            model_name='requisitonorma',
            name='bloque',
            field=models.CharField(choices=[('requisitos', 'Requisitos de la norma'), ('seguimiento', 'Ítems para auditorías internas de seguimiento')], default='requisitos', max_length=12, verbose_name='Bloque'),
        ),
        migrations.AlterField(
            model_name='itemverificacion',
            name='titulo',
            field=models.TextField(verbose_name='Requisito'),
        ),
        migrations.AlterField(
            model_name='requisitonorma',
            name='titulo',
            field=models.TextField(verbose_name='Título'),
        ),
        migrations.RemoveConstraint(
            model_name='requisitonorma',
            name='unique_norma_codigo',
        ),
        migrations.AddConstraint(
            model_name='requisitonorma',
            constraint=models.UniqueConstraint(fields=('norma', 'bloque', 'codigo'), name='unique_norma_bloque_codigo'),
        ),
    ]
