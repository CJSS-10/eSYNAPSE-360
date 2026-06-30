"""
Amplía la solicitud de cambio para soportar más entidades (intervalo de
calibración, nodo de trazabilidad), la operación 'eliminar' y el estado
'devuelta' (devuelta para corrección). Solo cambian choices (sin SQL real).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0032_resultadointervalo_unico_punto_anio'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitudcambioequipo',
            name='entidad',
            field=models.CharField(
                choices=[
                    ('equipo', 'Equipo'), ('registro', 'Registro de bitácora'),
                    ('actividad', 'Actividad del programa anual'), ('movimiento', 'Movimiento'),
                    ('informe', 'Informe'), ('intervalo', 'Intervalo de calibración'),
                    ('nodo', 'Nodo de trazabilidad'),
                ],
                default='equipo', max_length=20, verbose_name='Entidad afectada'),
        ),
        migrations.AlterField(
            model_name='solicitudcambioequipo',
            name='operacion',
            field=models.CharField(
                choices=[('crear', 'Crear'), ('editar', 'Editar'),
                         ('eliminar', 'Eliminar'), ('baja', 'Dar de baja')],
                default='editar', max_length=10, verbose_name='Operación'),
        ),
        migrations.AlterField(
            model_name='solicitudcambioequipo',
            name='estado',
            field=models.CharField(
                choices=[('pendiente', 'Pendiente'), ('aprobada', 'Aprobada'),
                         ('devuelta', 'Devuelta para corrección'), ('rechazada', 'Rechazada')],
                default='pendiente', max_length=12, verbose_name='Estado'),
        ),
    ]
