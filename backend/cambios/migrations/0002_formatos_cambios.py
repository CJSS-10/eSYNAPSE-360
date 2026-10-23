"""Registra los tres formatos impresos de cambios (Solicitud, Planificación y
Seguimiento) para vincularlos a la lista maestra."""
from django.db import migrations

FORMATOS = [
    ('cambios_solicitud', 'Solicitud de cambios', 'cambios', 'SIG-PRO-23-r01', 70),
    ('cambios_planificacion', 'Planificación de cambios', 'cambios', 'SIG-PRO-23-r02', 71),
    ('cambios_seguimiento', 'Seguimiento de cambios', 'cambios', 'SIG-PRO-23-r03', 72),
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
        ('cambios', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
