"""
Control de cambios de equipos: solicitudes de cambio pendientes de aprobación.
Cuando un usuario sin permiso de aprobar edita un equipo, el cambio se guarda
aquí en estado pendiente hasta que un supervisor lo aprueba o rechaza.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('esynapse_sig', '0024_equipo_cantidad_unidades'),
    ]

    operations = [
        migrations.CreateModel(
            name='SolicitudCambioEquipo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')),
                ('entidad', models.CharField(choices=[('equipo', 'Equipo'), ('registro', 'Registro de bitácora'), ('actividad', 'Actividad del programa anual'), ('movimiento', 'Movimiento'), ('informe', 'Informe')], default='equipo', max_length=20, verbose_name='Entidad afectada')),
                ('operacion', models.CharField(choices=[('crear', 'Crear'), ('editar', 'Editar'), ('baja', 'Dar de baja')], default='editar', max_length=10, verbose_name='Operación')),
                ('entidad_id', models.IntegerField(blank=True, null=True, verbose_name='ID del registro objetivo')),
                ('payload', models.JSONField(blank=True, default=dict, verbose_name='Datos propuestos')),
                ('archivo', models.FileField(blank=True, null=True, upload_to='equipos/solicitudes/%Y/', verbose_name='Archivo adjunto propuesto')),
                ('resumen', models.CharField(blank=True, max_length=255, verbose_name='Resumen del cambio')),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('aprobada', 'Aprobada'), ('rechazada', 'Rechazada')], default='pendiente', max_length=12, verbose_name='Estado')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones del aprobador')),
                ('resuelto_at', models.DateTimeField(blank=True, null=True, verbose_name='Fecha de resolución')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_actualizados', to=settings.AUTH_USER_MODEL, verbose_name='Actualizado por')),
                ('equipo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='solicitudes_cambio', to='esynapse_sig.equipo', verbose_name='Equipo')),
                ('resuelto_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='solicitudes_equipo_resueltas', to=settings.AUTH_USER_MODEL, verbose_name='Resuelto por')),
            ],
            options={
                'verbose_name': 'Solicitud de cambio de equipo',
                'verbose_name_plural': 'Solicitudes de cambio de equipo',
                'ordering': ['-created_at'],
            },
        ),
    ]
