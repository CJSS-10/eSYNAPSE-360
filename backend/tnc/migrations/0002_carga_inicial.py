"""Carga inicial: habilita el módulo y registra el formato impreso del registro de trabajos y salidas no conformes,
vinculado a la lista maestra si el documento ya está registrado."""
from django.db import migrations


def cargar(apps, schema_editor):
    ModuloHabilitado = apps.get_model('core', 'ModuloHabilitado')
    ModuloHabilitado.objects.update_or_create(clave='trabajo_no_conforme', defaults={
        'nombre': 'Trabajo No Conforme', 'habilitado': True, 'dependencias': [], 'orden': 20})
    FormatoImpreso = apps.get_model('esynapse_sig', 'FormatoImpreso')
    Documento = apps.get_model('esynapse_sig', 'Documento')
    f, _ = FormatoImpreso.objects.update_or_create(
        clave='tnc_registro', defaults={'nombre': 'Registro de trabajos y salidas no conformes',
                                        'modulo': 'trabajo_no_conforme', 'codigo_sgc': 'SIG-PRO-05-r01', 'orden': 1})
    if not f.documento_id:
        doc = Documento.objects.filter(codigo='SIG-PRO-05-r01', is_active=True).first()
        if doc:
            f.documento = doc
            f.save(update_fields=['documento'])


class Migration(migrations.Migration):

    dependencies = [
        ('tnc', '0001_initial'),
        ('core', '0018_carga_ubigeo'),
        ('esynapse_sig', '0072_baja_logica_firmas_registros'),
    ]

    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
