"""
Los puestos de SST pasan al catálogo único de Organización y personal (núcleo), y cada
fila IPERC se enlaza además al área del organigrama cuando su hoja corresponde a una
sola área. La hoja de la matriz se conserva (es la estructura del formato).
"""
from django.db import migrations, models
import django.db.models.deletion

HOJA_A_AREA = {
    'Alta Dirección': 'Gerencia General', 'Comercial': 'Gerencia Comercial y Marketing',
    'Administración': 'Administración', 'Logística': 'Logística', 'Mantenimiento': 'Mantenimiento',
    'SIG': 'Gerencia SIG',
    'Laboratorio de Temperatura y Humedad': 'Laboratorio de Temperatura y Humedad',
    'Laboratorio de Fuerza y Presión': 'Laboratorio de Fuerza y Presión',
    'Laboratorio de Electricidad y Potencia': 'Laboratorio de Electricidad y Potencia',
    'Laboratorio de Masa y Volumen': 'Laboratorio de Masa y Volumen',
    'Laboratorio de Grandes Volúmenes': 'Laboratorio de Grandes Volúmenes',
    'Laboratorio de Longitud y Ángulo': 'Laboratorio de Longitud y Ángulo',
}


def trasladar(apps, schema_editor):
    Viejo = apps.get_model('sst', 'Puesto')
    Nuevo = apps.get_model('organizacion', 'Puesto')
    Area = apps.get_model('organizacion', 'Area')
    Fila = apps.get_model('sst', 'FilaIPERC')
    equivalente = {}
    for v in Viejo.objects.all():
        n = Nuevo.objects.filter(nombre__iexact=v.nombre).first()
        if not n:
            n = Nuevo.objects.create(nombre=v.nombre, tipo=v.tipo, proceso_id=v.proceso_id,
                                     responsabilidades=v.descripcion, is_active=v.is_active,
                                     historial=[{'fecha': '2026-10-22', 'usuario': 'Carga inicial',
                                                 'accion': 'Registro (traslado desde SST)'}])
        equivalente[v.pk] = n
    areas = {a.nombre: a for a in Area.objects.all()}
    for f in Fila.objects.all():
        f.puestos_org.set([equivalente[p.pk] for p in f.puestos.all()])
        a = areas.get(HOJA_A_AREA.get(f.area, ''))
        if a:
            f.unidad = a
            f.save(update_fields=['unidad'])


class Migration(migrations.Migration):

    dependencies = [
        ('sst', '0004_procesos_principales'),
        ('organizacion', '0002_carga_inicial'),
    ]

    operations = [
        migrations.AddField(
            model_name='filaiperc',
            name='puestos_org',
            field=models.ManyToManyField(blank=True, related_name='filas_iperc_tmp', to='organizacion.puesto'),
        ),
        migrations.AddField(
            model_name='filaiperc',
            name='unidad',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='filas_iperc', to='organizacion.area',
                                    verbose_name='Área del organigrama'),
        ),
        migrations.RunPython(trasladar, migrations.RunPython.noop),
        migrations.RemoveField(model_name='filaiperc', name='puestos'),
        migrations.RenameField(model_name='filaiperc', old_name='puestos_org', new_name='puestos'),
        migrations.AlterField(
            model_name='filaiperc',
            name='puestos',
            field=models.ManyToManyField(blank=True, related_name='filas_iperc', to='organizacion.puesto',
                                         verbose_name='Puestos expuestos'),
        ),
        migrations.AlterField(
            model_name='filaiperc',
            name='area',
            field=models.CharField(max_length=120, verbose_name='Hoja de la matriz'),
        ),
        migrations.DeleteModel(name='Puesto'),
    ]
