"""Carga inicial de la lista de requisitos legales y de la matriz de evaluación de
cumplimiento (formatos en Excel), con las evaluaciones de 2025 como históricas, y
registro de sus formatos impresos para vincularlos a la lista maestra."""
import json
from datetime import date, datetime
from pathlib import Path

from django.db import migrations
from django.utils import timezone

DATOS = Path(__file__).resolve().parent.parent / 'datos' / 'carga_inicial.json'

FORMATOS = [
    ('legal_lista', 'Lista de requisitos legales y otros requisitos', 'legal', 'SIG-PRO-09-r01', 90),
    ('legal_matriz', 'Matriz de evaluación de cumplimiento legal', 'legal', 'SIG-PRO-09-r02', 91),
]
# Evaluaciones de la matriz anterior: tres cuatrimestres de 2025 (SST, otros requisitos y
# sociolaboral) y una anual (medio ambiente).
PERIODOS = {'sst': ['Cuatrimestre 1', 'Cuatrimestre 2', 'Cuatrimestre 3'], 'otros': ['Cuatrimestre 1', 'Cuatrimestre 2',
            'Cuatrimestre 3'], 'sociolaboral': ['Cuatrimestre 1', 'Cuatrimestre 2', 'Cuatrimestre 3'],
            'ma': ['Anual']}


def _fecha(texto):
    texto = (texto or '').strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            pass
    return None


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

    Requisito = apps.get_model('legal', 'Requisito')
    Obligacion = apps.get_model('legal', 'Obligacion')
    Evaluacion = apps.get_model('legal', 'Evaluacion')
    Resultado = apps.get_model('legal', 'ResultadoEvaluacion')
    Actualizacion = apps.get_model('legal', 'ActualizacionAmbito')
    if Requisito.objects.exists() or not DATOS.exists():
        return
    d = json.loads(DATOS.read_text(encoding='utf-8'))
    hist = [{'fecha': '2025-12-19', 'usuario': 'Carga inicial', 'accion': 'Carga desde la lista en Excel'}]
    reqs = []
    for r in d['requisitos']:
        reqs.append(Requisito.objects.create(
            ambito=r['ambito'], tema=r['tema'], orden=r['orden'], tipo=r['tipo'], codigo=r['codigo'],
            nombre=r['nombre'], fecha_aprobacion=r['fecha_aprobacion'], modificatorias='\n'.join(r['modificatorias']),
            observaciones=r['observaciones'][:255], estado=r['estado'], fecha_identificacion=date(2025, 12, 19),
            historial=hist))
    evaluaciones = {}
    cierre = timezone.make_aware(datetime(2025, 12, 15, 12, 0))
    contador = {}
    for o in d['obligaciones']:
        contador[o['ambito']] = contador.get(o['ambito'], 0) + 1
        ob = Obligacion.objects.create(
            ambito=o['ambito'], tema=o['tema'], orden=contador[o['ambito']],
            requisito=reqs[o['requisito']] if o.get('requisito') is not None else None,
            documento_legal=o['documento_legal'], articulo=o['articulo'][:120], extracto=o['extracto'] or '—',
            evidencia_documento=o['evidencia_documento'], proceso_sede=o['proceso_sede'][:150],
            responsable=o['responsable'][:150], periodicidad=o['periodicidad'][:80],
            observaciones=o['observaciones'], estado=o['estado'])
        for k, valor in enumerate(o['resultados']):
            if not valor:
                continue
            periodos = PERIODOS[o['ambito']]
            clave = (o['ambito'], k)
            if clave not in evaluaciones:
                evaluaciones[clave] = Evaluacion.objects.create(
                    ambito=o['ambito'], anio=2025, periodo=periodos[k], orden=k + 1, estado='cerrada',
                    fecha_inicio=date(2025, 1, 1), fecha_cierre=cierre, historica=True)
            resultado, _, obs = valor.partition(':')
            Resultado.objects.create(evaluacion=evaluaciones[clave], obligacion=ob, resultado=resultado,
                                     observaciones=obs, fecha=date(2025, 12, 15))
    for amb, cab in d['cabeceras'].items():
        Actualizacion.objects.create(ambito=amb, fecha_lista=_fecha(cab.get('fecha_lista')),
                                     fecha_matriz=_fecha(cab.get('fecha_matriz')))


class Migration(migrations.Migration):

    dependencies = [
        ('legal', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
