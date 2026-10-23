"""
Campos para replicar fielmente los formatos MET-PRO-12-r01 (tutor de supervisión)
y r03 (hora, área, preguntas con puntaje, agregados).
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('esynapse_sig', '0034_competencia_tecnica'),
    ]

    operations = [
        migrations.AddField(
            model_name='procesoentrenamiento',
            name='tutor_supervision',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='supervisiones_tutoradas', to=settings.AUTH_USER_MODEL,
                                    verbose_name='Tutor (supervisión)'),
        ),
        migrations.AddField(model_name='evaluacionseguimiento', name='hora',
                            field=models.CharField(blank=True, max_length=10, verbose_name='Hora')),
        migrations.AddField(model_name='evaluacionseguimiento', name='area',
                            field=models.CharField(blank=True, max_length=120, verbose_name='Área')),
        migrations.AddField(model_name='evaluacionseguimiento', name='preguntas',
                            field=models.JSONField(blank=True, default=list, verbose_name='Preguntas y puntajes')),
        migrations.AddField(model_name='evaluacionseguimiento', name='puntaje_total',
                            field=models.FloatField(blank=True, null=True, verbose_name='Puntaje total')),
        migrations.AddField(model_name='evaluacionseguimiento', name='puntaje_minimo',
                            field=models.FloatField(blank=True, null=True, verbose_name='Puntaje mínimo')),
        migrations.AddField(model_name='evaluacionseguimiento', name='puntaje_por_pregunta',
                            field=models.FloatField(blank=True, null=True, verbose_name='Puntaje por pregunta')),
        migrations.AddField(model_name='evaluacionseguimiento', name='n_preguntas',
                            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='N° de preguntas')),
    ]
