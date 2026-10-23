"""Indicadores de requisitos legales: cumplimiento por ámbito, tendencia y alertas."""
from django.utils import timezone

from .models import AMBITOS, Evaluacion, Obligacion, Requisito, calificacion

DIAS_EVALUACION = 183


def indicadores():
    hoy = timezone.localdate()
    ambitos = []
    total_cumple = total_eval = 0
    for clave, nombre in AMBITOS:
        evs = list(Evaluacion.objects.filter(ambito=clave, is_active=True).prefetch_related('resultados'))
        cerradas = [e for e in evs if e.estado == 'cerrada']
        ultima = cerradas[0] if cerradas else None
        en_curso = next((e for e in evs if e.estado == 'en_curso'), None)
        res_ultima = ultima.resumen() if ultima else None
        if res_ultima:
            total_cumple += res_ultima['cumple']
            total_eval += res_ultima['evaluadas']
        avance = None
        if en_curso:
            r = en_curso.resumen()
            n = sum(r[k] for k in ('pendiente', 'cumple', 'no_cumple', 'no_aplica'))
            avance = round(100 * (n - r['pendiente']) / n, 1) if n else None
        referencia = ultima.fecha_cierre.date() if ultima and ultima.fecha_cierre else None
        vencida = bool(not en_curso and Obligacion.objects.filter(ambito=clave, is_active=True, estado='vigente')
                       .exists() and (referencia is None or (hoy - referencia).days > DIAS_EVALUACION))
        ambitos.append({
            'ambito': clave, 'nombre': nombre,
            'requisitos': Requisito.objects.filter(ambito=clave, is_active=True, estado='vigente').count(),
            'derogados': Requisito.objects.filter(ambito=clave, is_active=True, estado='derogada').count(),
            'obligaciones': Obligacion.objects.filter(ambito=clave, is_active=True, estado='vigente').count(),
            'ultima': ({'id': ultima.id, 'periodo': f'{ultima.anio} · {ultima.periodo}', **res_ultima}
                       if ultima else None),
            'en_curso': ({'id': en_curso.id, 'periodo': f'{en_curso.anio} · {en_curso.periodo}', 'avance': avance}
                         if en_curso else None),
            'evaluacion_vencida': vencida,
            'tendencia': [{'periodo': f'{e.anio} · {e.periodo}', 'porcentaje': e.resumen()['porcentaje']}
                          for e in reversed(cerradas[:6])],
        })
    pct = round(100 * total_cumple / total_eval, 1) if total_eval else None
    return {'ambitos': ambitos, 'cumplimiento_global': {'porcentaje': pct, 'calificacion': calificacion(pct),
                                                        'cumplidos': total_cumple, 'evaluados': total_eval,
                                                        'meta': 100}}
