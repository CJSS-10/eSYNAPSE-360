"""El perfil de competencia por puesto pasa al puesto de Organización y personal (núcleo):
un solo perfil por puesto, que Competencia técnica consulta."""
from django.db import migrations


def trasladar(apps, schema_editor):
    Perfil = apps.get_model('esynapse_sig', 'PerfilCompetencia')
    Puesto = apps.get_model('organizacion', 'Puesto')
    for pf in Perfil.objects.all():
        p = Puesto.objects.filter(nombre__iexact=pf.cargo.strip()).first()
        if not p:
            p = Puesto.objects.create(nombre=pf.cargo.strip(), is_active=pf.is_active, historial=[
                {'fecha': '2026-10-22', 'usuario': 'Carga inicial', 'accion': 'Registro (perfil de Competencia)'}])
        cambios = False
        for c in ('educacion', 'formacion', 'experiencia', 'habilidades', 'responsabilidades'):
            if getattr(pf, c) and not getattr(p, c):
                setattr(p, c, getattr(pf, c))
                cambios = True
        if cambios:
            p.version_perfil = 1
            p.save()


class Migration(migrations.Migration):

    dependencies = [
        ('esynapse_sig', '0069_documento_proceso_catalogo_hallazgo_proceso_catalogo'),
        ('organizacion', '0002_carga_inicial'),
    ]

    operations = [
        migrations.RunPython(trasladar, migrations.RunPython.noop),
        migrations.DeleteModel(name='PerfilCompetencia'),
    ]
