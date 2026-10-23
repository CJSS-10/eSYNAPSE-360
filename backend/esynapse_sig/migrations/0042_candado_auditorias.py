"""
Candado de aprobación en Auditorías: nuevas entidades (programa anual e
informe de cierre) y operación "aprobar" en las solicitudes de cambio.
Solo cambian las opciones; no afecta datos.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('esynapse_sig', '0041_programa_anual_formato')]

    operations = [
        migrations.AlterField(
            model_name='solicitudcambioequipo',
            name='entidad',
            field=models.CharField(
                choices=[('equipo', 'Equipo'), ('registro', 'Registro de bitácora'),
                         ('actividad', 'Actividad del programa anual'), ('movimiento', 'Movimiento'),
                         ('informe', 'Informe'), ('intervalo', 'Intervalo de calibración'),
                         ('nodo', 'Nodo de trazabilidad'), ('autorizacion', 'Autorización de competencia'),
                         ('entrenamiento', 'Proceso de entrenamiento'), ('seguimiento', 'Evaluación de seguimiento'),
                         ('programa_auditoria', 'Programa anual de auditorías'),
                         ('informe_auditoria', 'Informe de auditoría (cierre)')],
                default='equipo', max_length=20, verbose_name='Entidad afectada'),
        ),
        migrations.AlterField(
            model_name='solicitudcambioequipo',
            name='operacion',
            field=models.CharField(
                choices=[('crear', 'Crear'), ('editar', 'Editar'), ('eliminar', 'Eliminar'),
                         ('baja', 'Dar de baja'), ('aprobar', 'Aprobar / cerrar')],
                default='editar', max_length=10, verbose_name='Operación'),
        ),
    ]
