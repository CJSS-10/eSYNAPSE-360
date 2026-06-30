"""
Catálogos gestionables de Magnitud y Clasificación de equipos (módulo Equipos).
- Crea MagnitudEquipo (con prefijo de código) y ClasificacionEquipo.
- Equipo/CartaTrazabilidad pasan a guardar el NOMBRE (no el código interno).
- Siembra los valores actuales y convierte registros existentes (si los hubiera).
"""
from django.db import migrations, models


MAGNITUDES = [
    ('Masa', 'M', 1),
    ('Temperatura', 'TH', 2),
    ('Electricidad', 'ET', 3),
    ('Presión', 'FP', 4),
    ('Longitud', 'LA', 5),
    ('Grandes Volúmenes y Flujo', 'GV', 6),
    ('Análisis Químico', 'AQ', 7),
]

CLASIFICACIONES = [
    ('Patrón de Referencia', 1),
    ('Patrón de Verificación', 2),
    ('Patrón de Trabajo', 3),
    ('Equipamiento Auxiliar', 4),
]

MAP_MAGNITUD = {
    'masa': 'Masa', 'temperatura': 'Temperatura', 'electricidad': 'Electricidad',
    'presion': 'Presión', 'longitud': 'Longitud',
    'grandes_volumenes': 'Grandes Volúmenes y Flujo', 'analisis_quimico': 'Análisis Químico',
}

MAP_CLASIFICACION = {
    'patron_referencia': 'Patrón de Referencia', 'patron_verificacion': 'Patrón de Verificación',
    'patron_trabajo': 'Patrón de Trabajo', 'equipamiento': 'Equipamiento Auxiliar',
}


def sembrar(apps, schema_editor):
    MagnitudEquipo = apps.get_model('esynapse_sig', 'MagnitudEquipo')
    ClasificacionEquipo = apps.get_model('esynapse_sig', 'ClasificacionEquipo')
    Equipo = apps.get_model('esynapse_sig', 'Equipo')
    CartaTrazabilidad = apps.get_model('esynapse_sig', 'CartaTrazabilidad')

    for nombre, prefijo, orden in MAGNITUDES:
        MagnitudEquipo.objects.get_or_create(nombre=nombre, defaults={'prefijo': prefijo, 'orden': orden})
    for nombre, orden in CLASIFICACIONES:
        ClasificacionEquipo.objects.get_or_create(nombre=nombre, defaults={'orden': orden})

    # Convertir registros existentes (códigos -> nombres). En BD vacía no hace nada.
    for codigo, nombre in MAP_MAGNITUD.items():
        Equipo.objects.filter(magnitud=codigo).update(magnitud=nombre)
        CartaTrazabilidad.objects.filter(magnitud=codigo).update(magnitud=nombre)
    for codigo, nombre in MAP_CLASIFICACION.items():
        Equipo.objects.filter(clasificacion=codigo).update(clasificacion=nombre)


def revertir(apps, schema_editor):
    MagnitudEquipo = apps.get_model('esynapse_sig', 'MagnitudEquipo')
    ClasificacionEquipo = apps.get_model('esynapse_sig', 'ClasificacionEquipo')
    MagnitudEquipo.objects.all().delete()
    ClasificacionEquipo.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0022_documento_padre'),
    ]

    operations = [
        migrations.CreateModel(
            name='MagnitudEquipo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Magnitud')),
                ('prefijo', models.CharField(help_text='Prefijo del código de equipo (ej: M, TH, FP).', max_length=4, verbose_name='Prefijo de código')),
                ('orden', models.PositiveIntegerField(default=0, verbose_name='Orden')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
            ],
            options={
                'verbose_name': 'Magnitud de equipo',
                'verbose_name_plural': 'Magnitudes de equipo',
                'ordering': ['orden', 'nombre'],
            },
        ),
        migrations.CreateModel(
            name='ClasificacionEquipo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True, verbose_name='Clasificación')),
                ('orden', models.PositiveIntegerField(default=0, verbose_name='Orden')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
            ],
            options={
                'verbose_name': 'Clasificación de equipo',
                'verbose_name_plural': 'Clasificaciones de equipo',
                'ordering': ['orden', 'nombre'],
            },
        ),
        migrations.AlterField(
            model_name='equipo',
            name='magnitud',
            field=models.CharField(blank=True, max_length=100, verbose_name='Magnitud'),
        ),
        migrations.AlterField(
            model_name='equipo',
            name='clasificacion',
            field=models.CharField(blank=True, default='Equipamiento Auxiliar', max_length=100, verbose_name='Clasificación'),
        ),
        migrations.AlterField(
            model_name='cartatrazabilidad',
            name='magnitud',
            field=models.CharField(blank=True, max_length=100, verbose_name='Magnitud'),
        ),
        migrations.RunPython(sembrar, revertir),
    ]
