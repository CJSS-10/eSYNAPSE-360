"""Procedimiento y Nota del nodo pasan a texto sin límite (los métodos de calibración son largos)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0028_nodo_nivel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nodotrazabilidad',
            name='procedimiento',
            field=models.TextField(blank=True, verbose_name='Procedimiento de calibración'),
        ),
        migrations.AlterField(
            model_name='nodotrazabilidad',
            name='nota',
            field=models.TextField(blank=True, verbose_name='Nota / método'),
        ),
    ]
