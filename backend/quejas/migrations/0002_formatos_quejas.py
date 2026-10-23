"""Registra los dos formatos impresos de quejas (Reporte y Registro de
Seguimiento) para vincularlos a la lista maestra."""
from django.db import migrations

FORMATOS = [
    ('quejas_reporte', 'Reporte de quejas', 'quejas', 'SIG-PRO-04-r01', 50),
    ('quejas_seguimiento', 'Registro de seguimiento de quejas', 'quejas', 'SIG-PRO-04-r02', 51),
]


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


class Migration(migrations.Migration):

    dependencies = [
        ('quejas', '0001_initial'),
        ('esynapse_sig', '0068_accion_sac_reaperturas'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
