from django.db import migrations, models


def sembrar(apps, schema_editor):
    Opcion = apps.get_model('core', 'OpcionCatalogo')
    areas = [
        'Dirección', 'Calidad', 'Laboratorio', 'Comercial',
        'Logística', 'Administración', 'TI', 'Recursos Humanos',
    ]
    labs = [
        'Recepción y Logística', 'Longitud', 'Grandes Volúmenes', 'Análisis Químico',
        'Gases', 'Topografía y Geodesia', 'Fuerza y Presión', 'Temperatura',
        'Masa y Volumen', 'Electricidad', 'Tiempo y Frecuencia', 'Fotometría',
        'Telecomunicaciones', 'Mantenimiento',
    ]
    for i, n in enumerate(areas):
        Opcion.objects.get_or_create(tipo='area', nombre=n, defaults={'orden': i})
    for i, n in enumerate(labs):
        Opcion.objects.get_or_create(tipo='laboratorio', nombre=n, defaults={'orden': i})


def revertir(apps, schema_editor):
    apps.get_model('core', 'OpcionCatalogo').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_usuario_foto'),
    ]

    operations = [
        migrations.CreateModel(
            name='OpcionCatalogo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('area', 'Área'), ('laboratorio', 'Laboratorio')], db_index=True, max_length=20, verbose_name='Tipo')),
                ('nombre', models.CharField(max_length=100, verbose_name='Nombre')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('orden', models.PositiveIntegerField(default=0, verbose_name='Orden')),
            ],
            options={
                'verbose_name': 'Opción de catálogo',
                'verbose_name_plural': 'Opciones de catálogo (áreas/laboratorios)',
                'ordering': ['tipo', 'orden', 'nombre'],
                'constraints': [models.UniqueConstraint(fields=('tipo', 'nombre'), name='unique_opcion_tipo_nombre')],
            },
        ),
        migrations.RunPython(sembrar, revertir),
    ]
