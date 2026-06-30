"""Categoría del nodo de trazabilidad: patrón (verde) o equipo/medición (naranja)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0026_nodotrazabilidad'),
    ]

    operations = [
        migrations.AddField(
            model_name='nodotrazabilidad',
            name='categoria',
            field=models.CharField(choices=[('patron', 'Patrón'), ('equipo', 'Equipo / medición')],
                                   default='patron', max_length=10, verbose_name='Categoría'),
        ),
    ]
