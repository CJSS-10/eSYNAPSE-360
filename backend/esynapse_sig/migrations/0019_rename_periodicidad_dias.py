from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0018_equipo_resolucion_alter_equipo_cantidad_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='equipo',
            old_name='periodicidad_meses',
            new_name='periodicidad_dias',
        ),
        migrations.AlterField(
            model_name='equipo',
            name='periodicidad_dias',
            field=__import__('django.db.models', fromlist=['PositiveSmallIntegerField']).PositiveSmallIntegerField(blank=True, null=True, verbose_name='Periodicidad (días)'),
        ),
    ]
