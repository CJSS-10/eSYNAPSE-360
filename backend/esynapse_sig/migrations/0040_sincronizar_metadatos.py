"""
Sincroniza etiquetas (verbose_name) de campos con los modelos. No cambia
datos ni estructura: solo deja modelos y migraciones alineados para que la
verificación automática (makemigrations --check) quede limpia.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0039_campos_plan_informe'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='actaauditoria',
            name='contenido',
            field=models.TextField(blank=True, verbose_name='Sección 2 (propósito / resultados)'),
        ),
        migrations.AlterField(
            model_name='actaauditoria',
            name='observaciones_auditado',
            field=models.TextField(blank=True, verbose_name='Sección 4 (compromisos / observaciones de la empresa)'),
        ),
        migrations.AlterField(
            model_name='evaluacionseguimiento',
            name='evaluador',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='seguimientos_evaluados', to=settings.AUTH_USER_MODEL, verbose_name='Responsable de la entrevista'),
        ),
        migrations.AlterField(
            model_name='procesoentrenamiento',
            name='checklist_entrenamiento',
            field=models.JSONField(blank=True, default=list, verbose_name='Actividades de entrenamiento'),
        ),
        migrations.AlterField(
            model_name='procesoentrenamiento',
            name='tutor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='entrenamientos_tutorados', to=settings.AUTH_USER_MODEL, verbose_name='Tutor (entrenamiento)'),
        ),
    ]
