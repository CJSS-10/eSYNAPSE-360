"""
El nodo de trazabilidad pasa de un solo 'padre' a varios 'padres' (M2M),
para representar patrones relacionados con varios eslabones (flechas convergentes).
Copia los enlaces existentes padre -> padres antes de eliminar el campo viejo.
"""
from django.db import migrations, models


def copiar(apps, schema_editor):
    Nodo = apps.get_model('esynapse_sig', 'NodoTrazabilidad')
    for n in Nodo.objects.exclude(padre__isnull=True):
        n.padres.add(n.padre_id)


def revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0029_nodo_texto_largo'),
    ]

    operations = [
        migrations.AddField(
            model_name='nodotrazabilidad',
            name='padres',
            field=models.ManyToManyField(blank=True, related_name='+', symmetrical=False,
                                         to='esynapse_sig.nodotrazabilidad', verbose_name='Es trazable a'),
        ),
        migrations.RunPython(copiar, revertir),
        migrations.RemoveField(
            model_name='nodotrazabilidad',
            name='padre',
        ),
        migrations.AlterField(
            model_name='nodotrazabilidad',
            name='padres',
            field=models.ManyToManyField(blank=True, related_name='hijos', symmetrical=False,
                                         to='esynapse_sig.nodotrazabilidad', verbose_name='Es trazable a'),
        ),
    ]
