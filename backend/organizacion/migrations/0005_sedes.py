"""Catálogo de sedes, niveles y suministros. Convierte la sede y el piso que las áreas tenían como texto libre en
sedes y niveles del catálogo (sin perder ninguno); luego retira los textos."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def _nombre_sede(texto):
    t = ' '.join(texto.split())
    return t if t.lower().startswith('sede') else f'Sede {t[:1].lower()}{t[1:]}'


def _nombre_nivel(texto):
    t = ' '.join(texto.split())
    return f'Piso {t}' if t.isdigit() else t[:1].upper() + t[1:]


def convertir(apps, schema_editor):
    Area = apps.get_model('organizacion', 'Area')
    Sede = apps.get_model('organizacion', 'Sede')
    Nivel = apps.get_model('organizacion', 'Nivel')
    sedes, niveles = {}, {}
    for a in Area.objects.all().order_by('orden', 'nombre'):
        texto = (a.sede_texto or '').strip()
        if not texto:
            continue
        clave = texto.casefold()
        if clave not in sedes:
            sedes[clave] = Sede.objects.create(nombre=_nombre_sede(texto)[:120], orden=len(sedes) + 1, historial=[
                {'fecha': timezone.localtime().isoformat(timespec='minutes'), 'usuario': 'Sistema',
                 'accion': 'Registro', 'motivo': 'creada desde la sede que tenían las áreas'}])
        sede = sedes[clave]
        nivel = None
        piso = (a.piso_texto or '').strip()
        if piso:
            k = (sede.pk, _nombre_nivel(piso).casefold())
            if k not in niveles:
                orden = int(piso) if piso.isdigit() else 100 + len(niveles)
                niveles[k] = Nivel.objects.create(sede=sede, nombre=_nombre_nivel(piso)[:60], orden=orden)
            nivel = niveles[k]
        a.sede, a.nivel = sede, nivel
        a.save(update_fields=['sede', 'nivel'])


class Migration(migrations.Migration):

    dependencies = [
        ('organizacion', '0004_area_sede_texto'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Nivel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')),
                ('nombre', models.CharField(help_text='Piso 1, Sótano, Bloque B…', max_length=60, verbose_name='Nombre')),
                ('orden', models.IntegerField(default=0, verbose_name='Orden')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_actualizados', to=settings.AUTH_USER_MODEL, verbose_name='Actualizado por')),
            ],
            options={
                'verbose_name': 'Nivel / piso',
                'verbose_name_plural': 'Niveles / pisos',
                'ordering': ['sede', 'orden', 'nombre'],
            },
        ),
        migrations.AddField(
            model_name='area',
            name='nivel',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='areas', to='organizacion.nivel', verbose_name='Nivel / piso'),
        ),
        migrations.CreateModel(
            name='Sede',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')),
                ('nombre', models.CharField(max_length=120, unique=True, verbose_name='Nombre')),
                ('codigo', models.CharField(blank=True, help_text='Abreviatura para listados e impresos (p. ej. SO, SA).', max_length=12, verbose_name='Código corto')),
                ('direccion', models.CharField(blank=True, max_length=250, verbose_name='Dirección')),
                ('distrito', models.CharField(blank=True, max_length=80, verbose_name='Distrito')),
                ('provincia', models.CharField(blank=True, max_length=80, verbose_name='Provincia')),
                ('departamento', models.CharField(blank=True, max_length=80, verbose_name='Departamento')),
                ('tenencia', models.CharField(choices=[('propia', 'Propia'), ('alquilada', 'Alquilada')], default='propia', max_length=10, verbose_name='Instalaciones')),
                ('principal', models.BooleanField(default=False, verbose_name='Sede principal (domicilio fiscal)')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción / observaciones')),
                ('orden', models.PositiveIntegerField(default=0, verbose_name='Orden')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('historial', models.JSONField(blank=True, default=list, verbose_name='Historial')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('responsable', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sedes_a_cargo', to='organizacion.puesto', verbose_name='Puesto responsable de la sede')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_actualizados', to=settings.AUTH_USER_MODEL, verbose_name='Actualizado por')),
            ],
            options={
                'verbose_name': 'Sede',
                'verbose_name_plural': 'Sedes',
                'ordering': ['orden', 'nombre'],
            },
        ),
        migrations.AddField(
            model_name='nivel',
            name='sede',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='niveles', to='organizacion.sede', verbose_name='Sede'),
        ),
        migrations.AddField(
            model_name='area',
            name='sede',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='areas', to='organizacion.sede', verbose_name='Sede'),
        ),
        migrations.CreateModel(
            name='Suministro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')),
                ('tipo', models.CharField(choices=[('energia', 'Energía eléctrica'), ('agua', 'Agua')], max_length=8, verbose_name='Servicio')),
                ('modalidad', models.CharField(choices=[('lectura', 'Lectura del medidor'), ('recibo', 'Recibo de la empresa prestadora')], default='lectura', max_length=8, verbose_name='Cómo se obtiene el consumo')),
                ('numero', models.CharField(blank=True, max_length=60, verbose_name='N° de suministro / medidor')),
                ('empresa_prestadora', models.CharField(blank=True, max_length=120, verbose_name='Empresa prestadora')),
                ('ubicacion', models.CharField(blank=True, max_length=150, verbose_name='Ubicación del medidor')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('historial', models.JSONField(blank=True, default=list, verbose_name='Historial')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('nivel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='suministros', to='organizacion.nivel', verbose_name='Nivel (vacío: toda la sede)')),
                ('responsable', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='suministros_a_cargo', to='organizacion.puesto', verbose_name='Responsable del registro (vacío: el de la sede)')),
                ('sede', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='suministros', to='organizacion.sede', verbose_name='Sede')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_actualizados', to=settings.AUTH_USER_MODEL, verbose_name='Actualizado por')),
            ],
            options={
                'verbose_name': 'Suministro',
                'verbose_name_plural': 'Suministros',
                'ordering': ['sede', 'nivel__orden', 'tipo', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='nivel',
            constraint=models.UniqueConstraint(fields=('sede', 'nombre'), name='nivel_unico_por_sede'),
        ),
        migrations.RunPython(convertir, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='area',
            name='piso_texto',
        ),
        migrations.RemoveField(
            model_name='area',
            name='sede_texto',
        ),
    ]
