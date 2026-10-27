"""Paso previo al consumo por suministro: el archivo del recibo pasa a ser la evidencia (recibo o foto del medidor) y
el número de suministro escrito a mano se retira (ahora viene del catálogo de suministros de la sede)."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ambiente', '0002_carga_inicial'),
    ]

    operations = [
        migrations.RemoveField(model_name='consumomensual', name='suministro'),
        migrations.RenameField(model_name='consumomensual', old_name='recibo', new_name='evidencia'),
    ]
