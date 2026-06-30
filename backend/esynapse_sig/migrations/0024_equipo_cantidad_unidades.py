"""Campo nuevo 'Cantidad' (cantidad_unidades) en Equipo + relabel de 'cantidad' a 'Alcance / Valor nominal'."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0023_catalogos_magnitud_clasificacion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='equipo',
            name='cantidad',
            field=models.CharField(blank=True, max_length=40, verbose_name='Alcance / Valor nominal'),
        ),
        migrations.AddField(
            model_name='equipo',
            name='cantidad_unidades',
            field=models.CharField(blank=True, max_length=40, verbose_name='Cantidad'),
        ),
    ]
