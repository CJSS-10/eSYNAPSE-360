"""Registra el formato impreso de la matriz de evaluación del cumplimiento. Es un formato nuevo: el Área SIG le
asigna su código al registrarlo en la lista maestra y vincularlo en Configuración."""
from django.db import migrations


def cargar(apps, schema_editor):
    FormatoImpreso = apps.get_model('esynapse_sig', 'FormatoImpreso')
    FormatoImpreso.objects.update_or_create(
        clave='cumplimiento_matriz', defaults={'nombre': 'Matriz de evaluación del cumplimiento de requisitos',
                                               'modulo': 'cumplimiento', 'codigo_sgc': 'POR ASIGNAR', 'orden': 1})


class Migration(migrations.Migration):

    dependencies = [
        ('cumplimiento', '0002_evaluacion_sede'),
        ('esynapse_sig', '0072_baja_logica_firmas_registros'),
    ]

    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
