from django.db import migrations


def renombrar(apps, schema_editor):
    Rol = apps.get_model('core', 'Rol')
    existe_destino = Rol.objects.filter(nombre='Administrador de Sistema').exists()
    if not existe_destino:
        Rol.objects.filter(nombre='Administrador de empresa').update(
            nombre='Administrador de Sistema')


def revertir(apps, schema_editor):
    Rol = apps.get_model('core', 'Rol')
    if not Rol.objects.filter(nombre='Administrador de empresa').exists():
        Rol.objects.filter(nombre='Administrador de Sistema').update(
            nombre='Administrador de empresa')


class Migration(migrations.Migration):
    dependencies = [('core', '0005_sembrar_roles')]
    operations = [migrations.RunPython(renombrar, revertir)]
