"""Carga inicial de Revisión por la dirección: habilita el módulo y registra sus tres formatos impresos (programa,
informe y plan de acción), vinculados a la lista maestra si el documento ya está registrado."""
from django.db import migrations

FORMATOS = [
    ('rd_programa', 'Programa de revisión por la dirección', 'PES-PRO-03-r01', 10),
    ('rd_informe', 'Informe de revisión por la dirección', 'PES-PRO-03-r02', 11),
    ('rd_plan', 'Plan de acción de la revisión por la dirección', 'PES-PRO-03-r03', 12),
]


def cargar(apps, schema_editor):
    ModuloHabilitado = apps.get_model('core', 'ModuloHabilitado')
    ModuloHabilitado.objects.update_or_create(clave='revision_direccion', defaults={
        'nombre': 'Revisión por la Dirección', 'habilitado': True, 'dependencias': [], 'orden': 5})
    FormatoImpreso = apps.get_model('esynapse_sig', 'FormatoImpreso')
    Documento = apps.get_model('esynapse_sig', 'Documento')
    for clave, nombre, codigo, orden in FORMATOS:
        f, _ = FormatoImpreso.objects.update_or_create(
            clave=clave, defaults={'nombre': nombre, 'modulo': 'revision_direccion', 'codigo_sgc': codigo,
                                   'orden': orden})
        if not f.documento_id:
            doc = Documento.objects.filter(codigo=codigo, is_active=True).first()
            if doc:
                f.documento = doc
                f.save(update_fields=['documento'])


class Migration(migrations.Migration):

    dependencies = [
        ('revision', '0001_initial'),
        ('core', '0018_carga_ubigeo'),
        ('esynapse_sig', '0072_baja_logica_firmas_registros'),
    ]

    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
