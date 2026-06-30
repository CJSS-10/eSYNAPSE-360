"""
Un solo resultado por (punto, año) en el Intervalo de Calibración, para soportar
la edición en matriz (años en filas, puntos en columnas).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0031_intervalo_calibracion'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='resultadointervalo',
            unique_together={('punto', 'anio')},
        ),
    ]
