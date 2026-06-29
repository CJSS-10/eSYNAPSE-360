from django.db import migrations


def renombrar(apps, schema_editor):
    Rol = apps.get_model('core', 'Rol')
    if Rol.objects.filter(nombre='Administrador de Sistema').exists():
        return
    for viejo in ('Administrador de sistema', 'Administrador de empresa'):
        if Rol.objects.filter(nombre=viejo).exists():
            Rol.objects.filter(nombre=viejo).update(nombre='Administrador de Sistema')
            return


def revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [('core', '0006_renombrar_rol_admin')]
    operations = [migrations.RunPython(renombrar, revertir)]
