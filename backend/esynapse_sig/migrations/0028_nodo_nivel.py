"""Reemplaza 'categoria' por 'nivel' en el nodo de trazabilidad (orden jerárquico por nivel)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0027_nodotrazabilidad_categoria'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='nodotrazabilidad',
            name='categoria',
        ),
        migrations.AddField(
            model_name='nodotrazabilidad',
            name='nivel',
            field=models.PositiveIntegerField(default=1, verbose_name='Nivel'),
        ),
    ]
