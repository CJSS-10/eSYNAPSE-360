"""
Catálogo de formatos impresos: cada PDF que genera el sistema, con su código
de formato y el vínculo (opcional) al documento de la lista maestra del que
toma versión, fecha y firmas. Carga inicial con todos los formatos existentes
y hereda el vínculo que la configuración ya tenía para la Hoja de Vida.
"""
from django.db import migrations, models
import django.db.models.deletion


FORMATOS = [
    # (clave, nombre, módulo, código, orden)
    ('equipos_hoja_vida', 'Hoja de vida del equipo', 'equipos', 'MET-PRO-04-r01', 10),
    ('equipos_inventario', 'Inventario de equipos', 'equipos', 'MET-PRO-04-r02', 11),
    ('equipos_programa', 'Programa de mantenimiento, calibración, comprobaciones y caracterización', 'equipos', 'MET-PRO-04-r03', 12),
    ('equipos_carta_trazabilidad', 'Carta de trazabilidad', 'equipos', 'MET-PRO-04-r04', 13),
    ('equipos_intervalo', 'Intervalo de calibración', 'equipos', 'MET-PRO-04-r08', 14),
    ('competencia_entrenamiento', 'Entrenamiento y supervisión de actividades', 'competencia_tecnica', 'MET-PRO-12-r01', 20),
    ('competencia_autorizacion', 'Autorización del personal', 'competencia_tecnica', 'MET-PRO-12-r02', 21),
    ('competencia_seguimiento', 'Entrevista de seguimiento al personal', 'competencia_tecnica', 'MET-PRO-12-r03', 22),
    ('auditoria_programa_anual', 'Programa anual de auditorías', 'auditorias', 'SIG-PRO-16-r01', 30),
    ('auditoria_plan', 'Plan de auditoría interna', 'auditorias', 'SIG-PRO-16-r02', 31),
    ('auditoria_acta_apertura', 'Acta de reunión de apertura', 'auditorias', 'SIG-PRO-16-r03', 32),
    ('auditoria_informe', 'Informe de auditoría interna', 'auditorias', 'SIG-PRO-16-r04', 33),
    ('auditoria_acta_cierre', 'Acta de reunión de cierre', 'auditorias', 'SIG-PRO-16-r05', 34),
    ('auditoria_lista_17025', 'Lista de verificación NTP ISO/IEC 17025', 'auditorias', 'SIG-PRO-16-r06', 35),
    ('auditoria_lista_integrada', 'Lista de verificación ISO 9001, 14001, 45001', 'auditorias', 'SIG-PRO-16-r07', 36),
]


def cargar(apps, schema_editor):
    FormatoImpreso = apps.get_model('esynapse_sig', 'FormatoImpreso')
    Documento = apps.get_model('esynapse_sig', 'Documento')
    for clave, nombre, modulo, codigo, orden in FORMATOS:
        FormatoImpreso.objects.update_or_create(
            clave=clave, defaults={'nombre': nombre, 'modulo': modulo, 'codigo_sgc': codigo, 'orden': orden})
    # Vínculo automático: si en la lista maestra ya existe un documento con el
    # mismo código del formato, se enlaza.
    for f in FormatoImpreso.objects.filter(documento__isnull=True):
        doc = Documento.objects.filter(codigo=f.codigo_sgc, is_active=True).first()
        if doc:
            f.documento = doc
            f.save(update_fields=['documento'])
    # Hereda el vínculo que la configuración tenía para la Hoja de Vida.
    try:
        Config = apps.get_model('core', 'ConfiguracionSistema')
        cfg = Config.objects.first()
        cod = (getattr(cfg, 'formato_hv_codigo', '') or '').strip() if cfg else ''
        if cod:
            doc = Documento.objects.filter(codigo=cod, is_active=True).first()
            hv = FormatoImpreso.objects.filter(clave='equipos_hoja_vida').first()
            if doc and hv and not hv.documento_id:
                hv.documento = doc
                hv.save(update_fields=['documento'])
    except LookupError:
        pass


def borrar(apps, schema_editor):
    apps.get_model('esynapse_sig', 'FormatoImpreso').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0042_candado_auditorias'),
        ('core', '0013_usuario_sigla_cargo'),
    ]

    operations = [
        migrations.CreateModel(
            name='FormatoImpreso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clave', models.CharField(max_length=60, unique=True, verbose_name='Clave interna')),
                ('nombre', models.CharField(max_length=150, verbose_name='Formato')),
                ('modulo', models.CharField(max_length=40, verbose_name='Módulo')),
                ('codigo_sgc', models.CharField(max_length=30, verbose_name='Código del formato (respaldo)')),
                ('orden', models.PositiveIntegerField(default=0, verbose_name='Orden')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('documento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                                related_name='formatos_impresos', to='esynapse_sig.documento',
                                                verbose_name='Documento de la lista maestra')),
            ],
            options={'verbose_name': 'Formato impreso', 'verbose_name_plural': 'Formatos impresos', 'ordering': ['orden', 'nombre']},
        ),
        migrations.RunPython(cargar, borrar),
    ]
