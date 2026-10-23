"""Carga de las 11 plantillas de inspección, del programa anual de monitoreos 2025 y 2026, del registro
del monitoreo de diciembre de 2025 y de su programa de seguimiento de recomendaciones (datos de los
formatos del procedimiento de seguimiento y medición), y registro de sus formatos impresos."""
import json
from datetime import date
from pathlib import Path

from django.db import migrations

DATOS = Path(__file__).resolve().parent.parent / 'datos' / 'inspecciones.json'
FORMATOS_EXTRA = [
    ('sst_programa_monitoreos', 'Programa anual de monitoreos de agentes ocupacionales', 'SIG-PRO-06-r07'),
    ('sst_monitoreo', 'Monitoreo de agentes ocupacionales', 'SIG-PRO-06-r08'),
    ('sst_seguimiento_recomendaciones', 'Programa de seguimiento de recomendaciones de monitoreos', 'SIG-PRO-06-r09'),
]


def _f(texto):
    return date.fromisoformat(texto[:10]) if texto else None


def cargar(apps, schema_editor):
    if not DATOS.exists():
        return
    d = json.loads(DATOS.read_text(encoding='utf-8'))
    Plantilla = apps.get_model('sst', 'PlantillaInspeccion')
    FormatoImpreso = apps.get_model('esynapse_sig', 'FormatoImpreso')
    Documento = apps.get_model('esynapse_sig', 'Documento')

    def formato(clave, nombre, codigo, orden):
        f, _ = FormatoImpreso.objects.update_or_create(
            clave=clave, defaults={'nombre': nombre, 'modulo': 'sst', 'codigo_sgc': codigo, 'orden': orden})
        if not f.documento_id:
            doc = Documento.objects.filter(codigo=codigo, is_active=True).first()
            if doc:
                f.documento = doc
                f.save(update_fields=['documento'])

    for n, p in enumerate(d['plantillas']):
        datos = dict(p)
        datos['fecha_formato'] = _f(datos.get('fecha_formato'))
        datos['historial'] = [{'fecha': '2026-10-22T00:00', 'usuario': 'Sistema',
                               'accion': 'Carga desde el formato del procedimiento'}]
        if not Plantilla.objects.filter(nombre=p['nombre']).exists():
            Plantilla.objects.create(**datos)
        formato(f"sst_insp_{p['codigo_formato'][-3:].lower()}", p['nombre'], p['codigo_formato'], 110 + n)
    for n, (clave, nombre, codigo) in enumerate(FORMATOS_EXTRA):
        formato(clave, nombre, codigo, 125 + n)

    Programa = apps.get_model('sst', 'ProgramaMonitoreo')
    Programado = apps.get_model('sst', 'MonitoreoProgramado')
    Monitoreo = apps.get_model('sst', 'Monitoreo')
    Recomendacion = apps.get_model('sst', 'RecomendacionMonitoreo')
    if Programa.objects.exists() or Monitoreo.objects.exists():
        return
    hist = [{'fecha': '2026-10-22T00:00', 'usuario': 'Sistema', 'accion': 'Carga desde el registro en Excel'}]
    m = d['monitoreos']
    items_2025 = []
    for pr in m['programas']:
        prog = Programa.objects.create(anio=pr['anio'], fecha_actualizacion=_f(pr['fecha_actualizacion']),
                                       historial=hist)
        for i, it in enumerate(pr['items'], 1):
            obj = Programado.objects.create(programa=prog, orden=i, agente=it['agente'], detalle=it['detalle'],
                                            fecha_programada=_f(it['fecha']), frecuencia='anual', meses=it['meses'],
                                            comentarios=it['comentarios'])
            if pr['anio'] == 2025:
                items_2025.append(obj)
    r = m['monitoreo']
    mon = Monitoreo.objects.create(
        codigo='MON-001-2025', estado='registrado', area_monitoreada=r['area'], fecha=_f(r['fecha']),
        frecuencia=r['frecuencia'], tipo_riesgo=r['tipo_riesgo'], n_expuestos=r['n_expuestos'],
        organizacion=r['organizacion'], resultados=r['resultados'], causas_desviacion=r['causas'],
        conclusiones=r['conclusiones'], firma_registro=r['firma'], historial=hist)
    mon.programados.set(items_2025)
    for rec in m['recomendaciones']:
        f = _f(rec['fecha'])
        ejecutada = rec['estado'] == 'ejecutada'
        Recomendacion.objects.create(
            anio=2026, monitoreo=mon, orden=rec['orden'], agente=rec['agente'], actividad=rec['actividad'],
            fecha_programada=f, programacion=rec['programacion'],
            meses=[f.month] if f and f.year == 2026 else [], meses_ejecutados=[],
            estado=rec['estado'], fecha_ejecucion=f if ejecutada and f else None,
            observaciones=rec['observaciones'], historial=hist)


class Migration(migrations.Migration):

    dependencies = [
        ('sst', '0010_inspecciones_y_monitoreos'),
        ('esynapse_sig', '0071_alter_hallazgo_fuente'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
