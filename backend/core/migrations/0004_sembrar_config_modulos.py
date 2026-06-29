from django.db import migrations

from core.constants import MODULOS, DEPENDENCIAS_MODULOS, MODULOS_NUCLEO


def sembrar(apps, schema_editor):
    ConfiguracionSistema = apps.get_model('core', 'ConfiguracionSistema')
    ModuloHabilitado = apps.get_model('core', 'ModuloHabilitado')
    ConfiguracionSistema.objects.get_or_create(pk=1)
    for orden, (clave, nombre) in enumerate(MODULOS, start=1):
        if clave in MODULOS_NUCLEO:
            continue
        ModuloHabilitado.objects.update_or_create(
            clave=clave,
            defaults={
                'nombre': nombre,
                'habilitado': True,
                'dependencias': DEPENDENCIAS_MODULOS.get(clave, []),
                'orden': orden,
            },
        )


def revertir(apps, schema_editor):
    apps.get_model('core', 'ModuloHabilitado').objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [('core', '0003_configuracionsistema_modulohabilitado')]
    operations = [migrations.RunPython(sembrar, revertir)]
