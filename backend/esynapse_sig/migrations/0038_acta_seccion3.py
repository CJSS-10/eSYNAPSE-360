"""
Tercera sección de texto en el acta de auditoría, para replicar los formatos
reales (apertura: propósito / consideraciones / compromisos; cierre:
resultados / observaciones del equipo / observaciones de la empresa).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('esynapse_sig', '0037_lista_sig_integrado')]

    operations = [
        migrations.AddField(
            model_name='actaauditoria',
            name='seccion3',
            field=models.TextField(blank=True, verbose_name='Sección 3 (consideraciones / observaciones del equipo)'),
        ),
    ]
