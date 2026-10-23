"""Registra los dos formatos impresos de acciones correctivas (Solicitud y
Seguimiento) para vincularlos a la lista maestra."""
from django.db import migrations

FORMATOS = [
    ('sac_solicitud', 'Solicitud de acción correctiva', 'acciones_correctivas', 'SIG-PRO-11-r01', 40),
    ('sac_seguimiento', 'Seguimiento a solicitudes de acciones correctivas y no conformidades',
     'acciones_correctivas', 'SIG-PRO-11-r02', 41),
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
        ('esynapse_sig', '0063_sac_entidad_ciclos'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
