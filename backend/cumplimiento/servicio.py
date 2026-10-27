"""Armado de la matriz de cumplimiento por norma y de sus resúmenes (tablero, cortes, revisión por la dirección)."""
from collections import defaultdict

from .models import ESTADOS

from .evidencias import ALERTA, Evidencias
from .models import NORMAS, PUNTAJE, EvaluacionRequisito, RequisitoAdicional, normas_equivalentes

NOMBRE_NORMA = dict(NORMAS)
SEGUIMIENTO_17025 = 'Ítems de seguimiento del organismo de acreditación'


def catalogo(norma):
    """Filas del catálogo de Auditorías para la norma, en orden: secciones (títulos) y requisitos evaluables."""
    from esynapse_sig.models import RequisitoNorma
    filas = []
    qs = RequisitoNorma.objects.filter(norma=norma, bloque='requisitos').order_by('orden')
    for r in qs:
        seccion = r.es_seccion or r.codigo.endswith('.')
        filas.append(('seccion' if seccion else 'requisito', r))
    if norma == 'iso_17025':
        seg = list(RequisitoNorma.objects.filter(norma=norma, bloque='seguimiento').order_by('orden'))
        if seg:
            filas.append(('seccion', SEGUIMIENTO_17025))
            filas += [('requisito', r) for r in seg]
    return filas


def _codigo_visible(r):
    return f'S{r.codigo}' if r.bloque == 'seguimiento' else r.codigo


def sedes_activas():
    from organizacion.models import Sede
    return list(Sede.objects.filter(is_active=True).order_by('orden', 'nombre'))


def estado_sig(ev):
    """Estado del SIG completo: su propia evaluación (independiente de las de cada sede)."""
    return ev.estado if ev else 'sin_evaluar'


def estado_en(fila, sede=None):
    """Estado de una fila para el SIG completo (sede=None) o para una sede: cada una con su propia evaluación."""
    ev = fila['evaluacion'] or {}
    if sede is None:
        return ev.get('estado', 'sin_evaluar')
    return (ev.get('sedes') or {}).get(str(sede), {}).get('estado') or 'sin_evaluar'


def vencida_en(fila, sede=None):
    ev = fila['evaluacion'] or {}
    if sede is None:
        return bool(ev.get('vencida'))
    return bool((ev.get('sedes') or {}).get(str(sede), {}).get('vencida'))


def _riesgo(estado, vencida, evidencias):
    return estado in ('cumple', 'parcial') and (vencida or any(e['nivel'] == ALERTA for e in evidencias))


def riesgo_en(fila, sede=None):
    return _riesgo(estado_en(fila, sede), vencida_en(fila, sede), fila['evidencias'])


def en_riesgo(ev, evidencias):
    return bool(ev) and _riesgo(estado_sig(ev), ev.vencida, evidencias)


def evaluacion_dict(ev):
    if not ev:
        return None
    nombres = dict(ESTADOS)
    sig = estado_sig(ev)
    return {
        'id': ev.id, 'estado': ev.estado, 'estado_display': ev.get_estado_display(),
        'estado_sig': sig, 'estado_sig_display': nombres[sig],
        'sedes': {str(s.sede_id): {'estado': s.estado, 'estado_display': s.get_estado_display(),
                                   'observacion': s.observacion, 'sede_nombre': s.sede.nombre,
                                   'fecha_evaluacion': s.fecha_evaluacion, 'vencida': s.vencida,
                                   'sede_codigo': s.sede.codigo} for s in ev.sedes.all()},
        'justificacion': ev.justificacion, 'proceso': ev.proceso_id,
        'proceso_nombre': ev.proceso.nombre if ev.proceso_id else '',
        'como_se_cumple': ev.como_se_cumple, 'evidencia': ev.evidencia,
        'documentos': [{'id': d.id, 'codigo': d.codigo, 'titulo': d.titulo} for d in ev.documentos.all()],
        'fecha_evaluacion': ev.fecha_evaluacion, 'vencida': ev.vencida,
        'evaluado_por': (ev.evaluado_por.get_full_name() or ev.evaluado_por.username) if ev.evaluado_por_id else '',
        'hallazgo': ev.hallazgo_id, 'hallazgo_codigo': ev.hallazgo.codigo if ev.hallazgo_id else '',
        'hallazgo_estado': ev.hallazgo.get_estado_display() if ev.hallazgo_id else '',
        'historial': ev.historial[-20:],
    }


def _evaluaciones(**filtro):
    return {e.requisito_id if 'requisito__in' in filtro else e.adicional_id: e
            for e in EvaluacionRequisito.objects.filter(**filtro).select_related(
                'proceso', 'evaluado_por', 'hallazgo').prefetch_related('documentos', 'sedes__sede')}


def matriz(norma, evidencias=None):
    """Filas de la matriz de una norma: secciones y requisitos con su evaluación, evidencia automática y riesgo;
    al final, los otros requisitos vinculados a la norma."""
    evidencias = evidencias or Evidencias()
    cat = catalogo(norma)
    evs = _evaluaciones(requisito__in=[r.id for t, r in cat if t == 'requisito'])
    filas = []
    for tipo, r in cat:
        if tipo == 'seccion':
            filas.append({'tipo': 'seccion', 'codigo': '' if isinstance(r, str) else r.codigo.rstrip('.'),
                          'titulo': r if isinstance(r, str) else r.titulo.split('\n')[0]})
            continue
        ev = evs.get(r.id)
        evid = evidencias.para(norma, r.codigo) if r.bloque == 'requisitos' else []
        filas.append({'tipo': 'requisito', 'clave': f'n{r.id}', 'requisito': r.id, 'codigo': _codigo_visible(r),
                      'titulo': r.titulo, 'evaluacion': evaluacion_dict(ev), 'evidencias': evid,
                      'en_riesgo': en_riesgo(ev, evid),
                      'equivalentes': [NOMBRE_NORMA[n] for n in normas_equivalentes(norma, r.codigo)]
                      if r.bloque == 'requisitos' else []})
    adic = list(RequisitoAdicional.objects.filter(norma=norma, is_active=True))
    if adic:
        filas.append({'tipo': 'seccion', 'codigo': '', 'titulo': 'Otros requisitos vinculados a esta norma'})
        filas += filas_adicionales(adic)
    return filas


def filas_adicionales(adic):
    evs = _evaluaciones(adicional__in=[a.id for a in adic])
    salida = []
    for a in adic:
        ev = evs.get(a.id)
        salida.append({'tipo': 'requisito', 'clave': f'a{a.id}', 'adicional': a.id,
                       'codigo': a.codigo or '—', 'titulo': a.texto,
                       'referencia': f'{a.get_fuente_display()} · {a.referencia}',
                       'evaluacion': evaluacion_dict(ev), 'evidencias': [], 'en_riesgo': en_riesgo(ev, []),
                       'equivalentes': []})
    return salida


def resumen(filas, sede=None):
    """Grado de cumplimiento de un conjunto de filas (del SIG completo o de una sede): cumple 100, parcial 50,
    no cumple 0; no aplica se excluye."""
    req = [f for f in filas if f['tipo'] == 'requisito']
    cuenta = defaultdict(int)
    riesgo = 0
    for f in req:
        est = estado_en(f, sede)
        cuenta[est] += 1
        riesgo += _riesgo(est, vencida_en(f, sede), f['evidencias'])
    aplicables = len(req) - cuenta['no_aplica']
    evaluados = sum(cuenta[k] for k in PUNTAJE)
    puntos = sum(PUNTAJE[k] * cuenta[k] for k in PUNTAJE)
    return {
        'total': len(req), 'aplicables': aplicables, 'evaluados': evaluados,
        'cumple': cuenta['cumple'], 'parcial': cuenta['parcial'], 'no_cumple': cuenta['no_cumple'],
        'no_aplica': cuenta['no_aplica'], 'sin_evaluar': cuenta['sin_evaluar'],
        'en_riesgo': riesgo,
        'porcentaje': round(puntos / evaluados, 1) if evaluados else None,
        'cobertura': round(100 * (evaluados + cuenta['no_aplica']) / len(req), 1) if req else None,
    }


def tablero():
    evidencias = Evidencias()
    sedes = sedes_activas()
    normas, por_proceso, riesgo = [], defaultdict(list), []
    por_sede = {s.id: [] for s in sedes}
    for clave, nombre in NORMAS:
        filas = matriz(clave, evidencias)
        normas.append({'norma': clave, 'nombre': nombre, **resumen(filas)})
        for s in sedes:
            por_sede[s.id].append({'norma': clave, 'nombre': nombre, **resumen(filas, s.id)})
        for f in filas:
            if f['tipo'] != 'requisito':
                continue
            ev = f['evaluacion'] or {}
            if ev.get('proceso_nombre'):
                por_proceso[ev['proceso_nombre']].append(f)
            sedes_mal = [x for x in (ev.get('sedes') or {}).values() if x['estado'] in ('parcial', 'no_cumple')]
            if f['en_riesgo'] or ev.get('estado') in ('parcial', 'no_cumple') or sedes_mal:
                detalle = [f'{x["sede_codigo"] or x["sede_nombre"]}: {x["estado_display"]}'
                           for x in (ev.get('sedes') or {}).values() if x['estado'] != 'sin_evaluar']
                riesgo.append({'norma': nombre, 'norma_clave': clave, 'codigo': f['codigo'],
                               'titulo': f['titulo'][:160], 'estado': ev.get('estado_sig_display', ''),
                               'estado_clave': ev.get('estado_sig', 'sin_evaluar'), 'sedes': ' · '.join(detalle),
                               'en_riesgo': f['en_riesgo'], 'hallazgo_codigo': ev.get('hallazgo_codigo', ''),
                               'motivo': '; '.join(e['texto'] for e in f['evidencias'] if e['nivel'] == ALERTA)
                               or ('Evaluación con más de 12 meses' if ev.get('vencida') else '')})
    otros = filas_adicionales(list(RequisitoAdicional.objects.filter(is_active=True, norma='')))
    return {
        'normas': normas,
        'sedes': [{'id': s.id, 'nombre': s.nombre, 'codigo': s.codigo, 'normas': por_sede[s.id]} for s in sedes],
        'otros': resumen(otros) if otros else None,
        'procesos': sorted([{'proceso': p, **resumen(fs)} for p, fs in por_proceso.items()],
                           key=lambda x: x['proceso']),
        'atencion': riesgo,
        'evidencias': [evidencias.resultado(c) for c in evidencias_claves()],
    }


def evidencias_claves():
    from .evidencias import VERIFICACIONES
    return [c for c, *_ in VERIFICACIONES]


def resultados_corte():
    """Resultado por norma para guardar un corte."""
    t = tablero()
    campos = ('nombre', 'porcentaje', 'cobertura', 'total', 'evaluados', 'cumple', 'parcial', 'no_cumple',
              'no_aplica', 'en_riesgo')
    datos = {n['norma']: {k: n[k] for k in campos} for n in t['normas']}
    datos['sedes'] = {str(s['id']): {'nombre': s['nombre'], 'codigo': s['codigo'],
                                     **{n['norma']: n['porcentaje'] for n in s['normas']}} for s in t['sedes']}
    return datos
