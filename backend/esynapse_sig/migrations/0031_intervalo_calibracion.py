"""
Intervalo de Calibración (MET-PRO-04-r08): puntos nominales de un patrón y sus
resultados anuales para el cálculo del periodo (método OIML D10 por deriva).
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('esynapse_sig', '0030_nodo_varios_padres'),
    ]

    operations = [
        migrations.CreateModel(
            name='PuntoIntervalo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')),
                ('valor_nominal', models.CharField(max_length=60, verbose_name='Valor nominal')),
                ('orden', models.PositiveIntegerField(default=0, verbose_name='Orden')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_actualizados', to=settings.AUTH_USER_MODEL, verbose_name='Actualizado por')),
                ('equipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='puntos_intervalo', to='esynapse_sig.equipo', verbose_name='Patrón')),
            ],
            options={
                'verbose_name': 'Punto de intervalo de calibración',
                'verbose_name_plural': 'Puntos de intervalo de calibración',
                'ordering': ['orden', 'id'],
            },
        ),
        migrations.CreateModel(
            name='ResultadoIntervalo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')),
                ('anio', models.PositiveIntegerField(verbose_name='Año de calibración')),
                ('resultado', models.FloatField(default=0, verbose_name='Resultado (desviación)')),
                ('incertidumbre', models.FloatField(default=0, verbose_name='Incertidumbre')),
                ('emp', models.FloatField(default=0, verbose_name='EMP (error máximo permitido)')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_actualizados', to=settings.AUTH_USER_MODEL, verbose_name='Actualizado por')),
                ('punto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resultados', to='esynapse_sig.puntointervalo', verbose_name='Punto')),
            ],
            options={
                'verbose_name': 'Resultado de intervalo',
                'verbose_name_plural': 'Resultados de intervalo',
                'ordering': ['anio', 'id'],
            },
        ),
    ]
