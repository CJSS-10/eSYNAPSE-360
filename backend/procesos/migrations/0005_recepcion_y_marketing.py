"""Catálogo: agrega el subproceso «Recepción de Equipos y/o Instrumentos» (de
Metrología) y el proceso de soporte «Marketing» (decisión de César, 2026-10-21,
al cargar la matriz de riesgos y oportunidades)."""
from django.db import migrations

NUEVOS = [
    ('Recepción de Equipos y/o Instrumentos', 'operativo', 'Metrología', 'Coordinador Logístico', 20),
    ('Marketing', 'soporte', None, 'Coordinador Comercial', 21),
]


def agregar(apps, schema_editor):
    Proceso = apps.get_model('procesos', 'Proceso')
    for nombre, tipo, padre, cargo, orden in NUEVOS:
        if Proceso.objects.filter(nombre__iexact=nombre).exists():
            continue
        p_padre = Proceso.objects.filter(nombre=padre).first() if padre else None
        Proceso.objects.create(nombre=nombre, tipo=tipo, padre=p_padre, responsable_cargo=cargo, orden=orden)


class Migration(migrations.Migration):

    dependencies = [
        ('procesos', '0004_alter_aviso_origen'),
    ]

    operations = [
        migrations.RunPython(agregar, migrations.RunPython.noop),
    ]
