"""
M12 — Competencia técnica y autorización del personal.
Catálogos (métodos, controles de validez) + Autorizacion, ProcesoEntrenamiento,
EvaluacionSeguimiento, PerfilCompetencia. Siembra los dos controles de validez.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def sembrar_controles(apps, schema_editor):
    ControlValidez = apps.get_model('esynapse_sig', 'ControlValidez')
    datos = [
        ('Ensayo de aptitud / intercomparación interlaboratorio', 1),
        ('Comparación intralaboratorio', 2),
    ]
    for nombre, orden in datos:
        ControlValidez.objects.get_or_create(nombre=nombre, defaults={'orden': orden})


def borrar_controles(apps, schema_editor):
    apps.get_model('esynapse_sig', 'ControlValidez').objects.all().delete()


AUDIT = lambda: [
    ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
    ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
    ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')),
]


def audit_fks():
    return [
        ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                         related_name='%(class)s_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
        ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                         related_name='%(class)s_actualizados', to=settings.AUTH_USER_MODEL, verbose_name='Actualizado por')),
    ]


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('esynapse_sig', '0033_solicitud_estados_entidades'),
    ]

    operations = [
        migrations.CreateModel(
            name='MetodoCalibracion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200, verbose_name='Método / procedimiento')),
                ('codigo', models.CharField(blank=True, max_length=40, verbose_name='Código')),
                ('magnitud', models.CharField(blank=True, max_length=100, verbose_name='Magnitud')),
                ('orden', models.PositiveIntegerField(default=0, verbose_name='Orden')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
            ],
            options={'verbose_name': 'Método de calibración', 'verbose_name_plural': 'Métodos de calibración',
                     'ordering': ['magnitud', 'orden', 'nombre']},
        ),
        migrations.CreateModel(
            name='ControlValidez',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=150, unique=True, verbose_name='Control de validez')),
                ('orden', models.PositiveIntegerField(default=0, verbose_name='Orden')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
            ],
            options={'verbose_name': 'Control de validez de resultados', 'verbose_name_plural': 'Controles de validez de resultados',
                     'ordering': ['orden', 'nombre']},
        ),
        migrations.CreateModel(
            name='Autorizacion',
            fields=AUDIT() + [
                ('magnitud', models.CharField(blank=True, max_length=100, verbose_name='Magnitud')),
                ('funciones', models.JSONField(blank=True, default=list, verbose_name='Funciones autorizadas')),
                ('alcance_firma', models.CharField(blank=True, choices=[('', 'No aplica'), ('todos', 'Todos los laboratorios'), ('laboratorio', 'Un laboratorio')], default='', max_length=12, verbose_name='Alcance de firma')),
                ('laboratorio', models.CharField(blank=True, max_length=120, verbose_name='Laboratorio (alcance de firma)')),
                ('fecha_autorizacion', models.DateField(blank=True, null=True, verbose_name='Fecha de autorización')),
                ('estado', models.CharField(choices=[('en_entrenamiento', 'En entrenamiento'), ('vigente', 'Vigente'), ('suspendida', 'Suspendida'), ('revocada', 'Revocada')], default='en_entrenamiento', max_length=20, verbose_name='Estado')),
                ('frecuencia_seguimiento_meses', models.PositiveSmallIntegerField(default=12, verbose_name='Frecuencia de seguimiento (meses)')),
                ('fecha_ultimo_seguimiento', models.DateField(blank=True, null=True, verbose_name='Último seguimiento')),
                ('evidencia', models.FileField(blank=True, null=True, upload_to='competencia/autorizaciones/%Y/', verbose_name='Evidencia')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('autorizado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='autorizaciones_otorgadas', to=settings.AUTH_USER_MODEL, verbose_name='Autorizado por')),
                ('metodo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='autorizaciones', to='esynapse_sig.metodocalibracion', verbose_name='Método')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='autorizaciones', to=settings.AUTH_USER_MODEL, verbose_name='Personal')),
            ] + audit_fks(),
            options={'verbose_name': 'Autorización', 'verbose_name_plural': 'Autorizaciones',
                     'ordering': ['usuario__last_name', 'usuario__first_name', 'metodo__nombre']},
        ),
        migrations.CreateModel(
            name='ProcesoEntrenamiento',
            fields=AUDIT() + [
                ('tipo', models.CharField(choices=[('entrenamiento', 'Entrenamiento'), ('reentrenamiento', 'Re-entrenamiento')], default='entrenamiento', max_length=15, verbose_name='Tipo')),
                ('checklist_entrenamiento', models.JSONField(blank=True, default=list, verbose_name='Checklist de entrenamiento')),
                ('periodo_supervision_dias', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Periodo de supervisión (días)')),
                ('fecha_inicio_supervision', models.DateField(blank=True, null=True, verbose_name='Inicio de supervisión')),
                ('checklist_supervision', models.JSONField(blank=True, default=list, verbose_name='Checklist de supervisión')),
                ('nota_teorica', models.FloatField(blank=True, null=True, verbose_name='Nota teórica (0-20)')),
                ('resultado_control', models.CharField(blank=True, max_length=20, verbose_name='Resultado del control')),
                ('estado', models.CharField(choices=[('en_proceso', 'En proceso'), ('completado', 'Completado (conforme)'), ('no_conforme', 'No conforme')], default='en_proceso', max_length=15, verbose_name='Estado')),
                ('comentarios', models.TextField(blank=True, verbose_name='Comentarios')),
                ('evidencia', models.FileField(blank=True, null=True, upload_to='competencia/entrenamiento/%Y/', verbose_name='Evidencia')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('control_validez', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='esynapse_sig.controlvalidez', verbose_name='Control de validez aplicado')),
                ('metodo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='entrenamientos', to='esynapse_sig.metodocalibracion', verbose_name='Método')),
                ('tutor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entrenamientos_tutorados', to=settings.AUTH_USER_MODEL, verbose_name='Tutor')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entrenamientos', to=settings.AUTH_USER_MODEL, verbose_name='Personal')),
            ] + audit_fks(),
            options={'verbose_name': 'Proceso de entrenamiento', 'verbose_name_plural': 'Procesos de entrenamiento',
                     'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='EvaluacionSeguimiento',
            fields=AUDIT() + [
                ('fecha', models.DateField(blank=True, null=True, verbose_name='Fecha')),
                ('tipo', models.CharField(choices=[('entrevista', 'Entrevista de seguimiento'), ('control_validez', 'Control de validez'), ('testificacion', 'Testificación'), ('otro', 'Otro')], default='entrevista', max_length=20, verbose_name='Tipo')),
                ('tema', models.CharField(blank=True, max_length=200, verbose_name='Tema')),
                ('puntaje_obtenido', models.FloatField(blank=True, null=True, verbose_name='Puntaje obtenido')),
                ('puntaje_maximo', models.FloatField(blank=True, null=True, verbose_name='Puntaje máximo')),
                ('resultado', models.CharField(blank=True, choices=[('satisfactorio', 'Satisfactorio'), ('no_satisfactorio', 'No satisfactorio')], max_length=20, verbose_name='Resultado')),
                ('decision', models.CharField(blank=True, choices=[('mantener', 'Mantener autorización'), ('suspender', 'Suspender'), ('reautorizar', 'Reautorizar')], max_length=15, verbose_name='Decisión')),
                ('conclusiones', models.TextField(blank=True, verbose_name='Conclusiones')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones')),
                ('evidencia', models.FileField(blank=True, null=True, upload_to='competencia/seguimiento/%Y/', verbose_name='Evidencia')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('autorizacion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='seguimientos', to='esynapse_sig.autorizacion', verbose_name='Autorización')),
                ('control_validez', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='esynapse_sig.controlvalidez')),
                ('evaluador', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='seguimientos_evaluados', to=settings.AUTH_USER_MODEL, verbose_name='Evaluador')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='seguimientos', to=settings.AUTH_USER_MODEL, verbose_name='Personal')),
            ] + audit_fks(),
            options={'verbose_name': 'Evaluación de seguimiento', 'verbose_name_plural': 'Evaluaciones de seguimiento',
                     'ordering': ['-fecha', '-created_at']},
        ),
        migrations.CreateModel(
            name='PerfilCompetencia',
            fields=AUDIT() + [
                ('cargo', models.CharField(max_length=120, unique=True, verbose_name='Cargo')),
                ('educacion', models.TextField(blank=True, verbose_name='Educación')),
                ('formacion', models.TextField(blank=True, verbose_name='Formación')),
                ('experiencia', models.TextField(blank=True, verbose_name='Experiencia')),
                ('habilidades', models.TextField(blank=True, verbose_name='Habilidades')),
                ('responsabilidades', models.TextField(blank=True, verbose_name='Responsabilidades')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
            ] + audit_fks(),
            options={'verbose_name': 'Perfil de competencia por puesto', 'verbose_name_plural': 'Perfiles de competencia por puesto',
                     'ordering': ['cargo']},
        ),
        migrations.RunPython(sembrar_controles, borrar_controles),
    ]
