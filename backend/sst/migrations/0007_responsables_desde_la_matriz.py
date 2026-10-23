"""
El responsable de los controles de cada fila IPERC pasa a ser uno o más puestos del catálogo
único (el texto original se conserva). Los responsables que la matriz nombra y que no estaban
en el catálogo se crean para que el SIG los revise. Los ejecutantes ya registrados en los ATS
quedan como personal externo (solo nombre) hasta vincularlos a un trabajador.
"""
from django.db import migrations

# Texto de la matriz → puesto del catálogo.
EQUIVALENCIAS = {
    'alta direccion': 'Gerente General', 'alta dirección': 'Gerente General',
    'gerente sig': 'Gerente SIG',
    'jefe de logística': 'Coordinador Logístico', 'jefe de logistica': 'Coordinador Logístico',
    'encargado de laboratorio': 'Encargado de Laboratorio',
    'supervisor de ssoma': 'Supervisor de SSOMA',
    'encargado de rrhh': 'Encargado de Recursos Humanos',
    'encargado de compras': 'Encargado de Compras',
}
# Puestos que la matriz nombra y no estaban en el catálogo: (puesto, área, reporta a).
NUEVOS = {
    'Supervisor de SSOMA': ('Gerencia SIG', 'Gerente SIG'),
    'Encargado de Recursos Humanos': ('Recursos Humanos', 'Gerente de Administración'),
    'Encargado de Compras': ('Administración', 'Gerente de Administración'),
}


def _limpiar(texto):
    # La matriz en Excel arrastraba una referencia de celda pegada al texto («+A12:Z35»).
    return '\n'.join(x.split('+A')[0].strip() for x in (texto or '').split('\n') if x.split('+A')[0].strip())


def trasladar(apps, schema_editor):
    Fila = apps.get_model('sst', 'FilaIPERC')
    Puesto = apps.get_model('organizacion', 'Puesto')
    Area = apps.get_model('organizacion', 'Area')
    ATS = apps.get_model('sst', 'ATS')

    def puesto(nombre):
        p = Puesto.objects.filter(nombre__iexact=nombre).first()
        if not p and nombre in NUEVOS:
            area, jefe = NUEVOS[nombre]
            a = Area.objects.filter(nombre=area).first()
            p = Puesto.objects.create(
                nombre=nombre, area=a, proceso_id=a.proceso_id if a else None,
                reporta_a=Puesto.objects.filter(nombre=jefe).first(),
                historial=[{'fecha': '2026-10-22', 'usuario': 'Carga inicial',
                            'accion': 'Registro (responsable nombrado en la matriz IPERC; revisar)'}])
        return p

    for f in Fila.objects.all():
        texto = _limpiar(f.responsable)
        if texto != f.responsable:
            f.responsable = texto
            f.save(update_fields=['responsable'])
        ids = []
        for linea in texto.split('\n'):
            nombre = EQUIVALENCIAS.get(' '.join(linea.lower().split()))
            p = puesto(nombre) if nombre else None
            if p and p.pk not in ids:
                ids.append(p.pk)
        if ids:
            f.responsables.set(ids)

    for a in ATS.objects.all():
        nuevos = [{'trabajador': e.get('trabajador'), 'nombre': e.get('nombre', ''), 'puesto': e.get('puesto', '')}
                  for e in (a.ejecutantes or []) if isinstance(e, dict)]
        if nuevos != a.ejecutantes:
            a.ejecutantes = nuevos
            a.save(update_fields=['ejecutantes'])


class Migration(migrations.Migration):

    dependencies = [
        ('sst', '0006_responsables_de_controles'),
        ('organizacion', '0003_corrige_tipo_areas_propuestas'),
    ]

    operations = [
        migrations.RunPython(trasladar, migrations.RunPython.noop),
    ]
