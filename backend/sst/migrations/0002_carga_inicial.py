"""Carga inicial: catálogo de puestos de trabajo, tabla de peligros y riesgos, filas de
la matriz IPERC en Excel (una hoja por área) y registro de los formatos impresos."""
import json
from datetime import date
from pathlib import Path

from django.db import migrations

DATOS = Path(__file__).resolve().parent.parent / 'datos'

FORMATOS = [
    ('sst_iperc', 'Matriz IPERC', 'sst', 'SIG-PRO-08-r01', 100),
    ('sst_ats', 'Análisis de Trabajo Seguro', 'sst', 'SIG-PRO-08-r02', 101),
]

# (puesto, tipo, proceso)
PUESTOS = [
    ('Gerente General', 'propio', 'Gestión Estratégica'),
    ('Gerente Técnico', 'propio', 'Metrología'),
    ('Gerente SIG', 'propio', 'Sistema Integrado de Gestión'),
    ('Gerente de I+D+i', 'propio', 'Gestión Estratégica'),
    ('Gerente Comercial y Marketing', 'propio', 'Comercial'),
    ('Gerente de Administración', 'propio', 'Recursos Humanos'),
    ('Coordinador Administrativo', 'propio', 'Recursos Humanos'),
    ('Asistente Administrativo', 'propio', 'Recursos Humanos'),
    ('Analista Contable', 'propio', 'Facturación y Cobranzas'),
    ('Asistente Comercial', 'propio', 'Comercial'),
    ('Ejecutivo de Ventas', 'propio', 'Comercial'),
    ('Coordinador de Marketing', 'propio', 'Marketing'),
    ('Diseñador Gráfico', 'propio', 'Marketing'),
    ('Coordinador Logístico', 'propio', 'Recepción de Equipos y/o Instrumentos'),
    ('Asistente Logístico', 'propio', 'Recepción de Equipos y/o Instrumentos'),
    ('Auxiliar Logístico', 'propio', 'Recepción de Equipos y/o Instrumentos'),
    ('Conductor / Operador Logístico', 'propio', 'Recepción de Equipos y/o Instrumentos'),
    ('Supervisor de Laboratorio', 'propio', 'Metrología'),
    ('Encargado de Laboratorio', 'propio', 'Metrología'),
    ('Metrólogo', 'propio', 'Metrología'),
    ('Coordinador de Mantenimiento', 'propio', 'Mantenimiento'),
    ('Técnico de Mantenimiento', 'propio', 'Mantenimiento'),
    ('Soporte de TI', 'propio', 'Sistemas'),
    ('Asistente SIG', 'propio', 'Sistema Integrado de Gestión'),
    ('Personal de limpieza', 'tercero', 'Compras'),
    ('Encargado de fumigación', 'tercero', 'Compras'),
    ('Encargado de mantenimiento de pozo a tierra', 'tercero', 'Compras'),
    ('Encargado de monitoreo ocupacional', 'tercero', 'Compras'),
    ('Médico ocupacional', 'tercero', 'Compras'),
]

LAB = ['Supervisor de Laboratorio', 'Encargado de Laboratorio', 'Metrólogo']
# Texto de la columna «puestos» de la matriz → puestos del catálogo.
EQUIVALENCIAS = {
    'Gerente General': ['Gerente General'],
    'Gerente Tecnico / Gerente SIG/ Gerente de I+D/ Gerente de Comercial y Marketing':
        ['Gerente Técnico', 'Gerente SIG', 'Gerente de I+D+i', 'Gerente Comercial y Marketing'],
    'Coordinador de Mantenimiento / Tecnico de Mantenimiento': ['Coordinador de Mantenimiento', 'Técnico de Mantenimiento'],
    'Asistente SIG': ['Asistente SIG'],
    'ENCARGADO LOGÍSTICO/ASISTENTE DE LOGISTICA /AUXILIAR LOGÍSTICO /OPERADOR LOGÍSTICO':
        ['Coordinador Logístico', 'Asistente Logístico', 'Auxiliar Logístico', 'Conductor / Operador Logístico'],
    'GERENTE COMERCIAL / ASISTENTE COMERCIAL / EJECUTIVO DE VENTAS /  Coordinador de Marketing y Diseñador Grafico':
        ['Gerente Comercial y Marketing', 'Asistente Comercial', 'Ejecutivo de Ventas', 'Coordinador de Marketing',
         'Diseñador Gráfico'],
    'Gerente de Administración, Coordinador Administrativo Asistente de Administrativo y Analista Contable':
        ['Gerente de Administración', 'Coordinador Administrativo', 'Asistente Administrativo', 'Analista Contable'],
    'Médico Ocupacional': ['Médico ocupacional'],
    'Encargado de Fumigación': ['Encargado de fumigación'],
    'Soporte de TI': ['Soporte de TI'],
    'Encargado de la ejecución del Monitoreo': ['Encargado de monitoreo ocupacional'],
    'Encargado del Mantenieminto Pozo a Tierra': ['Encargado de mantenimiento de pozo a tierra'],
    'Operador logístico': ['Conductor / Operador Logístico'],
    'ÁREA DE LIMPIEZA': ['Personal de limpieza'],
}
NIVELES = {'T': 'Trivial', 'TO': 'Tolerable', 'M': 'Moderado', 'IM': 'Importante', 'IT': 'Intolerable'}


def _nivel(valor):
    if not valor:
        return ''
    for tope, n in ((4, 'T'), (8, 'TO'), (16, 'M'), (24, 'IM')):
        if valor <= tope:
            return n
    return 'IT'


def _puestos_de(texto):
    if texto in EQUIVALENCIAS:
        return EQUIVALENCIAS[texto]
    if texto.startswith('Supervisor de Laboratorio'):
        return LAB
    return []


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

    Proceso = apps.get_model('procesos', 'Proceso')
    Puesto = apps.get_model('sst', 'Puesto')
    Peligro = apps.get_model('sst', 'PeligroCatalogo')
    Fila = apps.get_model('sst', 'FilaIPERC')
    Revision = apps.get_model('sst', 'RevisionIPERC')

    def proceso(nombre):
        return Proceso.objects.filter(nombre=nombre).order_by('-is_active', 'id').first() if nombre else None

    if not Puesto.objects.exists():
        for nombre, tipo, proc in PUESTOS:
            Puesto.objects.create(nombre=nombre, tipo=tipo, proceso=proceso(proc))
    if not Peligro.objects.exists() and (DATOS / 'peligros.json').exists():
        for p in json.loads((DATOS / 'peligros.json').read_text(encoding='utf-8')):
            Peligro.objects.create(**p)
    if Fila.objects.exists() or not (DATOS / 'iperc.json').exists():
        return

    d = json.loads((DATOS / 'iperc.json').read_text(encoding='utf-8'))
    puestos = {p.nombre: p for p in Puesto.objects.all()}
    procesos = {}
    # Puestos de cada área (para las filas «todas las actividades» del área).
    por_area = {}
    for f in d['filas']:
        por_area.setdefault(f['area'], [])
        for n in _puestos_de(f['puestos_texto'].strip()):
            if n not in por_area[f['area']]:
                por_area[f['area']].append(n)
    fecha = d.get('actualizacion') or '2025-12-15'
    for i, f in enumerate(d['filas'], start=1):
        if f['proceso'] not in procesos:
            procesos[f['proceso']] = proceso(f['proceso'])
        texto = f['puestos_texto'].strip()
        todos = texto.lower() == 'todos los puestos'
        nombres = por_area[f['area']] if texto.upper() == 'TODAS LAS ACTIVIDADES' else _puestos_de(texto)
        hist = [{'fecha': fecha, 'usuario': 'Carga inicial',
                 'accion': f'Carga desde la matriz en Excel (hoja «{f["hoja"]}», fila {f["fila"]})'}]
        prob = (f['a'] or 0) + (f['b'] or 0) + (f['c'] or 0) + (f['d'] or 0)
        calc = _nivel(prob * f['s']) if all((f['a'], f['b'], f['c'], f['d'], f['s'])) else ''
        excel = f.get('excel_nr')
        if calc and excel and excel != prob * f['s']:
            hist.append({'fecha': fecha, 'usuario': 'Carga inicial', 'accion': 'Observación de la carga',
                         'motivo': f'En el Excel el nivel de riesgo figuraba como {excel} '
                                   f'({NIVELES[_nivel(excel)]}); recalculado con A+B+C+D × S = {prob * f["s"]} '
                                   f'({NIVELES[calc]}).'})
        fila = Fila.objects.create(
            codigo=f'IPR-{i:03d}', area=f['area'], proceso=procesos[f['proceso']], subproceso=f['subproceso'][:200],
            todos_los_puestos=todos, puestos_texto=texto[:255], actividad=f['actividad'] or '—',
            peligro=f['peligro'] or '—', riesgo=f['riesgo'] or '—', consecuencia=f['consecuencia'],
            situaciones=f['situacion'], controles_existentes=f['controles_existentes'],
            personas=f['a'], procedimientos=f['b'], capacitacion=f['c'], exposicion=f['d'], severidad=f['s'],
            control_eliminacion=f['eliminacion'], control_sustitucion=f['sustitucion'],
            control_ingenieria=f['ingenieria'], control_administrativo=f['administrativo'], control_epp=f['epp'],
            responsable=f['responsable'][:200], r_personas=f['ra'], r_procedimientos=f['rb'],
            r_capacitacion=f['rc'], r_exposicion=f['rd'], r_severidad=f['rs'], historial=hist)
        if not todos:
            fila.puestos.set([puestos[n] for n in nombres if n in puestos])
    for area in por_area:
        Revision.objects.create(area=area, fecha=date.fromisoformat(fecha), nombre='Matriz en Excel (versión 01)',
                                observaciones='Última actualización registrada en la matriz anterior.')


class Migration(migrations.Migration):

    dependencies = [
        ('sst', '0001_initial'),
        ('esynapse_sig', '0069_documento_proceso_catalogo_hallazgo_proceso_catalogo'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
