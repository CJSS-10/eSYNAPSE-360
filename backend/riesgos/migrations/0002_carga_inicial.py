"""Carga inicial de la matriz de riesgos y oportunidades y de la matriz de
oportunidades de mejora (formatos en Excel vigentes al 2026-08-10), y registro de
sus formatos impresos para vincularlos a la lista maestra."""
import json
from datetime import date
from pathlib import Path

from django.db import migrations

DATOS = Path(__file__).resolve().parent.parent / 'datos' / 'carga_inicial.json'

FORMATOS = [
    ('riesgos_matriz', 'Matriz de riesgos y oportunidades', 'riesgos', 'PES-PRO-02-r01', 80),
    ('riesgos_mejoras', 'Matriz de oportunidades de mejora', 'riesgos', 'PES-PRO-02-r02', 81),
]


def _fecha(v):
    return date.fromisoformat(v) if v else None


def cargar(apps, schema_editor):
    Proceso = apps.get_model('procesos', 'Proceso')
    Elemento = apps.get_model('riesgos', 'ElementoContexto')
    Riesgo = apps.get_model('riesgos', 'RiesgoOportunidad')
    Accion = apps.get_model('riesgos', 'AccionRiesgo')
    Mejora = apps.get_model('riesgos', 'OportunidadMejora')
    Revision = apps.get_model('riesgos', 'RevisionMatriz')
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

    if Riesgo.objects.exists() or not DATOS.exists():
        return
    d = json.loads(DATOS.read_text(encoding='utf-8'))
    procesos = {p.nombre: p for p in Proceso.objects.all()}

    elementos = {}
    for e in d['contexto']:
        elementos[e['codigo']] = Elemento.objects.create(tipo=e['tipo'], codigo=e['codigo'], descripcion=e['descripcion'])
    for n, nombre in enumerate(d['partes_interesadas'], start=1):
        elementos[nombre.upper()] = Elemento.objects.create(tipo='parte_interesada', codigo=f'PI{n}', descripcion=nombre)

    usados = set()
    siguiente_r = max(int(x['codigo'][2:]) for x in d['riesgos_oportunidades'] if x['codigo'].startswith('R-'))
    for x in d['riesgos_oportunidades']:
        codigo, historial = x['codigo'], [{'fecha': '2026-08-10', 'usuario': 'Carga inicial',
                                          'accion': 'Carga desde la matriz en Excel'}]
        if codigo in usados:
            siguiente_r += 1
            nuevo = f'R-{siguiente_r:03d}'
            historial.append({'fecha': '2026-08-10', 'usuario': 'Carga inicial', 'accion': 'Renumeración',
                              'motivo': f'Código {codigo} repetido en la matriz original; se asignó {nuevo}.'})
            codigo = nuevo
        usados.add(codigo)
        r = Riesgo.objects.create(
            codigo=codigo, tipo=x['tipo'], estado='vigente', proceso=procesos.get(x['proceso']),
            categoria=x['categoria'], fuente=x['fuente'], fecha_identificacion=_fecha(x['fecha_identificacion']),
            actividad=x['actividad'], descripcion=x['descripcion'], causa=x['causa'], efecto=x['efecto'],
            controles_existentes=x['controles_existentes'], probabilidad=x['probabilidad'], impacto=x['impacto'],
            estrategia=x['estrategia'], residual_probabilidad=x['residual_probabilidad'],
            residual_impacto=x['residual_impacto'], fecha_verificacion=_fecha(x['fecha_verificacion']),
            evidencia_verificacion=x['evidencia_verificacion'], historial=historial)
        r.contexto.set([elementos[c] for c in x['contexto'] + x['partes_interesadas'] if c in elementos])
        for n, a in enumerate(x['acciones'], start=1):
            Accion.objects.create(riesgo=r, orden=n, actividad=a['actividad'],
                                  implementacion_documental=a['implementacion_documental'],
                                  responsable_texto=a['responsable_texto'], fecha_maxima=_fecha(a['fecha_maxima']),
                                  recursos=a['recursos'], estado=a['estado'])

    for m in d['oportunidades_mejora']:
        Mejora.objects.create(
            codigo=m['codigo'], proceso=procesos.get(m['proceso']), fuente=m['fuente'], detectado_por=m['detectado_por'],
            fecha_identificacion=_fecha(m['fecha_identificacion']), descripcion=m['descripcion'],
            situacion=m['situacion'], decision=m['decision'], justificacion=m['justificacion'], accion=m['accion'],
            responsable_texto=m['responsable_texto'], fecha_maxima=_fecha(m['fecha_maxima']),
            estado_accion=m['estado_accion'], fecha_verificacion=_fecha(m['fecha_verificacion']),
            evidencia=m['evidencia'], eficacia=m['eficacia'],
            historial=[{'fecha': '2026-08-10', 'usuario': 'Carga inicial', 'accion': 'Carga desde la matriz en Excel'}])

    for matriz, cab in (('ryo', d['cabecera_ryo']), ('om', d['cabecera_om'])):
        if cab.get('fecha_actualizacion'):
            Revision.objects.create(matriz=matriz, tipo='actualizacion', fecha=_fecha(cab['fecha_actualizacion']),
                                    nombre=cab.get('responsable_actualizacion', ''),
                                    observaciones='Última actualización de la matriz en Excel.')


class Migration(migrations.Migration):

    dependencies = [
        ('riesgos', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(cargar, migrations.RunPython.noop),
    ]
