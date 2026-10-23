"""
Dirección de la empresa y responsable del Sistema Integrado de Gestión,
usados en los formatos de auditoría (plan, informe y lista de verificación).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('core', '0011_opcioncatalogo')]

    operations = [
        migrations.AddField(
            model_name='configuracionsistema',
            name='direccion',
            field=models.CharField(blank=True, max_length=200, verbose_name='Dirección de la empresa'),
        ),
        migrations.AddField(
            model_name='configuracionsistema',
            name='responsable_sig',
            field=models.CharField(blank=True, max_length=150, verbose_name='Responsable del Sistema Integrado de Gestión'),
        ),
    ]
