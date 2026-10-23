"""
Programa anual como documento controlado: estado "en modificación", número de
revisión y trazabilidad de quién lo abrió, cuándo y por qué.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0043_formatos_impresos'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='programaauditoria',
            name='estado',
            field=models.CharField(choices=[('borrador', 'Borrador'), ('en_modificacion', 'En modificación'),
                                            ('aprobado', 'Aprobado')],
                                   default='borrador', max_length=15, verbose_name='Estado'),
        ),
        migrations.AddField(
            model_name='programaauditoria',
            name='revision',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Revisión'),
        ),
        migrations.AddField(
            model_name='programaauditoria',
            name='modificado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='programas_modificados', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='programaauditoria',
            name='fecha_modificacion',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Abierto para modificación'),
        ),
        migrations.AddField(
            model_name='programaauditoria',
            name='motivo_modificacion',
            field=models.CharField(blank=True, max_length=255, verbose_name='Motivo de la modificación'),
        ),
    ]
