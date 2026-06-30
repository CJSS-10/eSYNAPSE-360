"""
Árbol de las Cartas de Trazabilidad: nodos (eslabones) encadenados por 'padre'.
Cada nodo puede enlazarse a un equipo del inventario o describir un patrón/entidad externa.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('esynapse_sig', '0025_solicitudcambioequipo'),
    ]

    operations = [
        migrations.CreateModel(
            name='NodoTrazabilidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Fecha de actualización')),
                ('orden', models.PositiveIntegerField(default=0, verbose_name='Orden')),
                ('entidad', models.CharField(blank=True, max_length=150, verbose_name='Entidad que calibró')),
                ('descripcion', models.CharField(blank=True, max_length=200, verbose_name='Descripción del patrón')),
                ('codigo', models.CharField(blank=True, max_length=50, verbose_name='Código de identificación')),
                ('procedimiento', models.CharField(blank=True, max_length=200, verbose_name='Procedimiento de calibración')),
                ('certificado', models.CharField(blank=True, max_length=120, verbose_name='N° de certificado de calibración')),
                ('incertidumbre', models.CharField(blank=True, max_length=120, verbose_name='Incertidumbre (U)')),
                ('nota', models.CharField(blank=True, max_length=255, verbose_name='Nota / método')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_actualizados', to=settings.AUTH_USER_MODEL, verbose_name='Actualizado por')),
                ('carta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nodos', to='esynapse_sig.cartatrazabilidad', verbose_name='Carta')),
                ('padre', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='hijos', to='esynapse_sig.nodotrazabilidad', verbose_name='Es trazable a')),
                ('equipo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='nodos_trazabilidad', to='esynapse_sig.equipo', verbose_name='Equipo del inventario')),
            ],
            options={
                'verbose_name': 'Nodo de trazabilidad',
                'verbose_name_plural': 'Nodos de trazabilidad',
                'ordering': ['orden', 'id'],
            },
        ),
    ]
