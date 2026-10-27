"""Carga inicial de Medio ambiente: habilita el módulo, registra sus formatos impresos y carga la matriz de aspectos e
impactos ambientales del Excel (actualizada el 2025-12-25), consolidada sin duplicados (decisión de César del
2026-10-24): 330 filas en 12 hojas → 176 aspectos. La lista de cambios está en docs/modulos/M22_carga_matriz.md."""
import json
from pathlib import Path

from django.db import migrations

FORMATOS = [
    ('amb_matriz', 'Matriz de aspectos e impactos ambientales', 'SIG-PRO-14-r01', 170),
    ('amb_pesaje', 'Pesaje de residuos sólidos', 'SIG-PRO-19-r01', 171),
]
CAMPOS = ['legal', 'severidad', 'partes', 'escala', 'frecuencia']


def cargar(apps, schema_editor):
    ModuloHabilitado = apps.get_model('core', 'ModuloHabilitado')
    ModuloHabilitado.objects.update_or_create(clave='medio_ambiente', defaults={
        'nombre': 'Medio Ambiente', 'habilitado': True, 'dependencias': [], 'orden': 31})
    FormatoImpreso = apps.get_model('esynapse_sig', 'FormatoImpreso')
    Documento = apps.get_model('esynapse_sig', 'Documento')
    for clave, nombre, codigo, orden in FORMATOS:
        f, _ = FormatoImpreso.objects.update_or_create(
            clave=clave, defaults={'nombre': nombre, 'modulo': 'medio_ambiente', 'codigo_sgc': codigo, 'orden': orden})
        if not f.documento_id:
            doc = Documento.objects.filter(codigo=codigo, is_active=True).first()
            if doc:
                f.documento = doc
                f.save(update_fields=['documento'])

    Aspecto = apps.get_model('ambiente', 'AspectoAmbiental')
    if Aspecto.objects.exists():
        return
    Area = apps.get_model('organizacion', 'Area')
    Proceso = apps.get_model('procesos', 'Proceso')
    Puesto = apps.get_model('organizacion', 'Puesto')
    areas = {a.nombre: a for a in Area.objects.all()}
    procesos = {p.nombre: p for p in Proceso.objects.all()}
    puestos = {p.nombre: p for p in Puesto.objects.all()}
    datos = json.loads((Path(__file__).resolve().parent.parent / 'datos' / 'matriz_aspectos.json')
                       .read_text(encoding='utf-8'))
    for d in datos:
        crit = d['criterios'] if d['clase'] == 'negativo' else [None] * 5
        a = Aspecto.objects.create(
            alcance=d['alcance'], lugar=d['lugar'], proceso=procesos.get(d['proceso']) if d['proceso'] else None,
            actividad=d['actividad'], aspecto=d['aspecto'], impacto=d['impacto'], situaciones=d['situaciones'],
            generacion=d['generacion'], clase=d['clase'], controles_existentes=d['controles_existentes'],
            control_operacional=d['control_operacional'], registro_asociado=d['registro_asociado'],
            responsable=puestos.get(d['responsable']) if d['responsable'] else None, orden=d['orden'],
            historial=[{'fecha': '2026-10-24T00:00', 'usuario': 'Sistema',
                        'accion': f'Carga inicial de la matriz en Excel ({d["origen"]})'}],
            **dict(zip(CAMPOS, crit)))
        if d['alcance'] == 'areas':
            a.areas.set([areas[n] for n in d['areas'] if n in areas])


class Migration(migrations.Migration):

    dependencies = [
        ('ambiente', '0001_initial'),
        ('core', '0016_alter_permiso_modulo'),
        ('esynapse_sig', '0072_baja_logica_firmas_registros'),
        ('organizacion', '0003_corrige_tipo_areas_propuestas'),
        ('procesos', '0005_recepcion_y_marketing'),
    ]

    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
