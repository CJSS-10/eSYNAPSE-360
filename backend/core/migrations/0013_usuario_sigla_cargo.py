"""
Sigla del cargo del usuario (ASIG, GSIG, GT, GG…), usada en la caja de
control de los formatos para elaboró / revisó / aprobó.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('core', '0012_config_direccion_responsable')]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='sigla_cargo',
            field=models.CharField(blank=True, max_length=12, verbose_name='Sigla del cargo'),
        ),
    ]
