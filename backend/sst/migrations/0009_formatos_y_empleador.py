"""Formatos impresos de incidentes, accidentes, enfermedades ocupacionales y estadísticas, y
los datos del empleador que imprimen los registros oficiales (solo si están vacíos)."""
from django.db import migrations

FORMATOS = [
    ('sst_reg_accidentes', 'Registro de accidentes de trabajo', 'sst', 'SIG-PRO-10-r01', 102),
    ('sst_reg_enfermedades', 'Registro de enfermedades ocupacionales', 'sst', 'SIG-PRO-10-r02', 103),
    ('sst_reg_incidentes', 'Registro de accidentes e incidentes peligrosos', 'sst', 'SIG-PRO-10-r03', 104),
    ('sst_informe_investigacion', 'Informe de investigación de accidentes y emergencias', 'sst', 'SIG-PRO-10-r04', 105),
    ('sst_reg_estadisticas', 'Registro de estadísticas de seguridad y salud en el trabajo', 'sst', 'SIG-PRO-10-r05',
     106),
    ('sst_datos_estadisticas', 'Datos para el registro de estadísticas de SST', 'sst', 'SIG-PRO-10-r06', 107),
]
EMPLEADOR = {
    'razon_social': 'METROLOGÍA E INSTRUMENTACIÓN INDUSTRIAL S.A.C.',
    'ruc': '20601338204',
    'actividad_economica': '3313 - Reparación de equipo electrónico y óptico',
    'direccion': 'Calle Los Jazmines Mz. G Lt. 13 Coop. Talavera de la Reyna – El Agustino, Lima – Perú',
}


def cargar(apps, schema_editor):
    FormatoImpreso = apps.get_model('esynapse_sig', 'FormatoImpreso')
    Documento = apps.get_model('esynapse_sig', 'Documento')
    for clave, nombre, modulo, codigo, orden in FORMATOS:
        f, _ = FormatoImpreso.objects.update_or_create(
            clave=clave, defaults={'nombre': nombre, 'modulo': modulo, 'codigo_sgc': codigo, 'orden': orden})
        if not f.documento_id:
            doc = Documento.objects.filter(codigo=codigo, is_active=True).first()
            if doc:
                f.documento = doc
                f.save(update_fields=['documento'])
    Config = apps.get_model('core', 'ConfiguracionSistema')
    cfg, _ = Config.objects.get_or_create(pk=1)
    cambios = [k for k, v in EMPLEADOR.items() if not getattr(cfg, k)]
    for k in cambios:
        setattr(cfg, k, EMPLEADOR[k])
    if cambios:
        cfg.save(update_fields=cambios)


class Migration(migrations.Migration):

    dependencies = [
        ('sst', '0008_incidentes_accidentes_estadisticas'),
        ('core', '0015_datos_del_empleador'),
        ('esynapse_sig', '0071_alter_hallazgo_fuente'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
