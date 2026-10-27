"""Paso previo al catálogo de sedes: la sede y el piso de las áreas, que eran texto libre, quedan como respaldo
para convertirlos en la migración siguiente."""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizacion', '0003_corrige_tipo_areas_propuestas'),
    ]

    operations = [
        migrations.RenameField(model_name='area', old_name='sede', new_name='sede_texto'),
        migrations.RenameField(model_name='area', old_name='piso', new_name='piso_texto'),
    ]
