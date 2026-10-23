"""Indicadores de las dos matrices (hojas «Indicadores» de los formatos) y mapa de calor."""
from collections import Counter

from .models import FUENTES_MEJORA, NIVELES


def estado_acciones(r):
    """Estado agregado de las acciones de un registro: ejecutado, en_proceso, pendiente o ''."""
    acciones = [a for a in r.acciones_activas() if a.estado != 'no_aplica']
    if not acciones:
        return ''
    if all(a.estado == 'ejecutado' for a in acciones):
        return 'ejecutado'
    if any(a.estado in ('en_proceso', 'ejecutado') for a in acciones):
        return 'en_proceso'
    return 'pendiente'


def indicadores(registros, mejoras):
    filas = []
    def fila(nombre, cond):
        r = sum(1 for x in registros if x.tipo == 'riesgo' and cond(x))
        o = sum(1 for x in registros if x.tipo == 'oportunidad' and cond(x))
        filas.append({'indicador': nombre, 'riesgos': r, 'oportunidades': o, 'total': r + o})

    fila('Identificados', lambda x: True)
    fila('Que requieren acción', lambda x: x.debe_tratarse)
    fila('Con acciones ejecutadas', lambda x: estado_acciones(x) == 'ejecutado')
    fila('Con acciones en proceso', lambda x: estado_acciones(x) == 'en_proceso')
    fila('Con acciones pendientes de implementar', lambda x: estado_acciones(x) == 'pendiente')
    fila('Con acciones evaluadas como eficaces', lambda x: x.eficacia == 'eficaz')
    fila('Con acciones evaluadas como no eficaces', lambda x: x.eficacia == 'no_eficaz')
    fila('Con acciones sin cambio en la valoración', lambda x: x.eficacia == 'sin_cambio')
    fila('Con acciones pendientes de evaluar su eficacia',
         lambda x: x.eficacia == 'pendiente' and estado_acciones(x) == 'ejecutado')

    distribucion = []
    for clave, nombre in reversed(NIVELES):
        r = sum(1 for x in registros if x.tipo == 'riesgo' and x.nivel == clave)
        o = sum(1 for x in registros if x.tipo == 'oportunidad' and x.nivel == clave)
        distribucion.append({'nivel': clave, 'nombre': nombre, 'riesgos': r, 'oportunidades': o, 'total': r + o})

    def mapa(tipo):
        c = Counter((x.impacto, x.probabilidad) for x in registros if x.tipo == tipo and x.valor)
        return [[c.get((i, p), 0) for p in range(1, 6)] for i in range(5, 0, -1)]

    def codigos(tipo):
        """Códigos de los registros de cada casilla (fila: impacto 5→1; columna: probabilidad 1→5)."""
        celdas = [[[] for _ in range(5)] for _ in range(5)]
        for x in sorted(registros, key=lambda r: r.codigo):
            if x.tipo == tipo and x.valor:
                celdas[5 - x.impacto][x.probabilidad - 1].append(x.codigo)
        return celdas

    implementadas = sum(1 for x in registros if x.eficacia in ('eficaz', 'no_eficaz', 'sin_cambio'))
    eficaces = sum(1 for x in registros if x.eficacia == 'eficaz')

    total_om = len(mejoras)
    def om(nombre, cond):
        n = sum(1 for m in mejoras if cond(m))
        return {'indicador': nombre, 'cantidad': n, 'porcentaje': round(100 * n / total_om, 1) if total_om else None}
    filas_om = [
        om('Identificadas', lambda m: True),
        om('Seleccionadas para implementar', lambda m: m.decision == 'se_implementa'),
        om('En evaluación', lambda m: m.decision == 'en_evaluacion'),
        om('Descartadas', lambda m: m.decision == 'no_se_implementa'),
        om('Con acción y responsables definidos', lambda m: bool(m.accion and m.responsable_nombre)),
        om('Ejecutadas', lambda m: m.decision == 'se_implementa' and m.estado_accion == 'ejecutado'),
        om('En proceso', lambda m: m.decision == 'se_implementa' and m.estado_accion == 'en_proceso'),
        om('Pendientes de implementar', lambda m: m.decision == 'se_implementa' and m.estado_accion == 'pendiente'),
        om('Con eficacia lograda', lambda m: m.eficacia == 'lograda'),
        om('Con eficacia parcial o no lograda', lambda m: m.eficacia in ('parcial', 'no_lograda')),
        om('Sin evaluar su eficacia', lambda m: m.estado_accion == 'ejecutado' and m.eficacia == 'pendiente'),
    ]
    origen = Counter(m.fuente for m in mejoras)
    return {
        'riesgos_oportunidades': filas,
        'distribucion': distribucion,
        'mapa_riesgos': mapa('riesgo'),
        'mapa_oportunidades': mapa('oportunidad'),
        'mapa_riesgos_codigos': codigos('riesgo'),
        'mapa_oportunidades_codigos': codigos('oportunidad'),
        'eficacia_acciones': {'eficaces': eficaces, 'implementadas': implementadas,
                              'porcentaje': round(100 * eficaces / implementadas, 1) if implementadas else None,
                              'meta': 80},
        'mejoras': filas_om,
        'mejoras_por_origen': [{'fuente': k, 'nombre': n, 'cantidad': origen.get(k, 0)}
                               for k, n in FUENTES_MEJORA if origen.get(k)],
        'alertas': {
            'acciones_vencidas': sum(len(x.acciones_vencidas) for x in registros),
            'sin_tratamiento': sum(1 for x in registros if x.situacion == 'sin_tratamiento'),
            'sin_valoracion': sum(1 for x in registros if not x.valor),
            'en_cartera_sin_decision': sum(1 for x in registros if x.situacion == 'en_cartera'),
            'por_verificar': sum(1 for x in registros if x.situacion == 'por_verificar'),
            'mejoras_en_evaluacion_vencidas': sum(1 for m in mejoras if m.evaluacion_vencida),
            'mejoras_accion_vencida': sum(1 for m in mejoras if m.accion_vencida),
        },
    }
