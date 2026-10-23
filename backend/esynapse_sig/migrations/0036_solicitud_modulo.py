"""
Generaliza el motor de aprobación a multi-módulo: campo 'modulo' (por defecto
'equipos') y entidades de competencia (autorización, entrenamiento, seguimiento).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0035_competencia_formatos_fieles'),
    ]

    operations = [
        migrations.AddField(
            model_name='solicitudcambioequipo',
            name='modulo',
            field=models.CharField(default='equipos', max_length=30, verbose_name='Módulo'),
        ),
        migrations.AlterField(
            model_name='solicitudcambioequipo',
            name='entidad',
            field=models.CharField(
                choices=[
                    ('equipo', 'Equipo'), ('registro', 'Registro de bitácora'),
                    ('actividad', 'Actividad del programa anual'), ('movimiento', 'Movimiento'),
                    ('informe', 'Informe'), ('intervalo', 'Intervalo de calibración'),
                    ('nodo', 'Nodo de trazabilidad'), ('autorizacion', 'Autorización de competencia'),
                    ('entrenamiento', 'Proceso de entrenamiento'), ('seguimiento', 'Evaluación de seguimiento'),
                ],
                default='equipo', max_length=20, verbose_name='Entidad afectada'),
        ),
    ]
