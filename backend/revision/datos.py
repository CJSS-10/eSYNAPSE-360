"""
Datos del sistema para cada elemento de entrada de la revisión por la dirección, calculados para el periodo evaluado.
Cada entrada devuelve bloques {'titulo', 'filas': [[etiqueta, valor], …], 'nota'} que el Gerente SIG analiza; si un
módulo aún no existe, se indica que la información se registra manualmente.
"""
from collections import Counter
from datetime import date

from django.db.models import Q
from django.utils import timezone

MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic']


def _bloque(titulo, filas=None, nota=''):
    return {'titulo': titulo, 'filas': [[str(a), str(b)] for a, b in (filas or [])], 'nota': nota}


def _manual(texto):
    return [_bloque('Sin fuente en el sistema', nota=texto)]


def _conteo(qs, campo, opciones):
    nombres = dict(opciones)
    c = Counter(qs.values_list(campo, flat=True))
    return [[nombres.get(k, k or '—'), n] for k, n in sorted(c.items(), key=lambda x: -x[1])]


def _anios(desde, hasta):
    return list(range(desde.year, hasta.year + 1))


# ------------------------------------------------------------------------------------------------ entradas
def a_contexto(r, desde, hasta):
    from riesgos.models import TIPOS_CONTEXTO, ElementoContexto
    qs = ElementoContexto.objects.filter(is_active=True)
    nuevos = qs.filter(created_at__date__range=(desde, hasta)).count()
    cambiados = qs.filter(updated_at__date__range=(desde, hasta)).exclude(created_at__date__range=(desde, hasta))
    return [_bloque('Análisis del contexto (Riesgos y oportunidades)',
                    _conteo(qs, 'tipo', TIPOS_CONTEXTO) + [['Registrados en el periodo', nuevos],
                                                          ['Actualizados en el periodo', cambiados.count()]])]


def b_objetivos(r, desde, hasta):
    from sst.comite import ProgramaSSOMA
    bloques = []
    for anio in _anios(desde, hasta):
        p = ProgramaSSOMA.objects.filter(anio=anio).first()
        if not p:
            continue
        filas = []
        for o in p.objetivos.filter(is_active=True):
            acts = [a for a in o.actividades.filter(is_active=True)]
            av = round(sum(a.avance for a in acts) / len(acts)) if acts else 0
            filas.append([f'{o.codigo} {o.descripcion}', f'{av} % ({len(acts)} actividades)'])
        bloques.append(_bloque(f'Objetivos del Programa SSOMA {anio}', filas))
    bloques.append(_bloque('Objetivos de calidad', nota='El tablero de control de objetivos se integrará con el '
                                                       'módulo de Planeamiento; registre aquí su evaluación.'))
    return bloques


def c_documentos(r, desde, hasta):
    from esynapse_sig.models import Documento, VersionDocumento
    aprob = VersionDocumento.objects.filter(fecha_aprobacion__date__range=(desde, hasta)).select_related('documento')
    vencidas = VersionDocumento.objects.filter(estado='vigente', fecha_proxima_revision__lt=hasta)
    filas = [['Versiones aprobadas en el periodo', aprob.count()],
             ['Documentos vigentes con revisión vencida', vencidas.count()],
             ['Documentos activos', Documento.objects.filter(is_active=True).count()]]
    detalle = ', '.join(sorted({v.documento.codigo for v in aprob})[:25])
    return [_bloque('Documentos del SIG', filas, f'Aprobados: {detalle}' if detalle else '')]


def d_acuerdos_anteriores(r, desde, hasta):
    from .models import ESTADOS_ACUERDO, AcuerdoRevision
    qs = AcuerdoRevision.objects.filter(is_active=True, revision__is_active=True, revision__estado='cerrada') \
        .exclude(revision=r)
    filas = _conteo(qs, 'estado', ESTADOS_ACUERDO)
    vencidos = [a for a in qs.exclude(estado='cerrado') if a.vencido]
    filas.append(['Vencidos sin cerrar', len(vencidos)])
    pend = '; '.join(f'{a.revision.codigo} N.° {a.numero}: {a.descripcion[:70]}'
                     for a in qs.exclude(estado='cerrado').select_related('revision')[:15])
    return [_bloque('Acuerdos de revisiones anteriores', filas, f'Pendientes: {pend}' if pend else '')]


def _auditorias(clase, fuente, desde, hasta):
    from esynapse_sig.models import ESTADOS_AUDITORIA, TIPOS_HALLAZGO, Auditoria, Hallazgo
    auds = Auditoria.objects.filter(is_active=True, clase=clase).filter(
        Q(fecha_inicio__range=(desde, hasta)) | Q(fecha_inicio__isnull=True, fecha_programada__range=(desde, hasta)))
    hall = Hallazgo.objects.filter(is_active=True, fuente=fuente, fecha_deteccion__range=(desde, hasta))
    return [_bloque('Auditorías del periodo', [['Total', auds.count()]] + _conteo(auds, 'estado', ESTADOS_AUDITORIA),
                    ', '.join(auds.values_list('codigo', flat=True)[:20])),
            _bloque('Hallazgos', [['Total', hall.count()]] + _conteo(hall, 'tipo', TIPOS_HALLAZGO))]


def e_auditorias_internas(r, desde, hasta):
    return _auditorias('interna', 'auditoria_interna', desde, hasta)


def f_acciones_correctivas(r, desde, hasta):
    from esynapse_sig.models import ESTADOS_SAC, SolicitudAC
    qs = SolicitudAC.objects.filter(is_active=True)
    periodo = qs.filter(Q(fecha_registro__range=(desde, hasta)) |
                        Q(fecha_registro__isnull=True, created_at__date__range=(desde, hasta)))
    abiertas = qs.exclude(estado__in=['cerrada_conforme', 'cerrada_sin_ac'])
    return [_bloque('Solicitudes de acción correctiva', [['Registradas en el periodo', periodo.count()]]
                    + _conteo(periodo, 'estado', ESTADOS_SAC) + [['Abiertas a la fecha (todas)', abiertas.count()]])]


def g_organismos_externos(r, desde, hasta):
    return _auditorias('externa', 'auditoria_externa', desde, hasta)


def h_volumen(r, desde, hasta):
    return _manual('La producción de servicios de calibración se obtendrá de las órdenes de trabajo (cadena operativa). '
                   'Registre el resumen anual por procedimiento de calibración.')


def i_retroalimentacion(r, desde, hasta):
    return _manual('Las encuestas de satisfacción de clientes y la retroalimentación del personal aún no se registran '
                   'en el sistema. Registre sus resultados.')


def j_quejas(r, desde, hasta):
    from quejas.models import ESTADOS_QUEJA, RESULTADOS_QUEJA, Queja
    qs = Queja.objects.filter(is_active=True, fecha_recepcion__date__range=(desde, hasta))
    meses = Counter((timezone.localtime(q.fecha_recepcion).year, timezone.localtime(q.fecha_recepcion).month)
                    for q in qs)
    por_mes = ', '.join(f'{MESES[m - 1]} {a}: {n}' for (a, m), n in sorted(meses.items()))
    return [_bloque('Quejas recibidas en el periodo', [['Total', qs.count()]] + _conteo(qs, 'estado', ESTADOS_QUEJA)
                    + [[f'Resultado: {k}', n] for k, n in _conteo(qs.exclude(resultado=''), 'resultado',
                                                                   RESULTADOS_QUEJA)],
                    f'Por mes: {por_mes}' if por_mes else '')]


def k_mejoras(r, desde, hasta):
    from riesgos.models import DECISIONES_MEJORA, ESTADOS_ACCION, OportunidadMejora
    qs = OportunidadMejora.objects.filter(is_active=True, fecha_identificacion__range=(desde, hasta))
    impl = qs.filter(decision='se_implementa')
    return [_bloque('Oportunidades de mejora identificadas en el periodo', [['Total', qs.count()]]
                    + _conteo(qs, 'decision', DECISIONES_MEJORA)
                    + [[f'Implementación: {k}', n] for k, n in _conteo(impl, 'estado_accion', ESTADOS_ACCION)]
                    + [['Con eficacia verificada', impl.exclude(eficacia='pendiente').count()]])]


def l_recursos(r, desde, hasta):
    return _manual('El presupuesto del SIG se integrará con el módulo de Planeamiento. Registre la evaluación de la '
                   'adecuación de los recursos (humanos, infraestructura, equipos, financieros).')


def m_riesgos(r, desde, hasta):
    from riesgos.models import ESTADOS_ACCION, TIPOS, AccionRiesgo, RiesgoOportunidad
    vig = RiesgoOportunidad.objects.filter(is_active=True, estado='vigente')
    acc = AccionRiesgo.objects.filter(is_active=True, riesgo__in=vig)
    niveles = Counter(x.nivel for x in vig if getattr(x, 'valor', None) is not None)
    return [_bloque('Matriz de riesgos y oportunidades', [['En la matriz', vig.count()]] + _conteo(vig, 'tipo', TIPOS)
                    + [[f'Nivel {k}', n] for k, n in sorted(niveles.items())]),
            _bloque('Acciones para abordarlos', _conteo(acc, 'estado', ESTADOS_ACCION))]


def n_validez(r, desde, hasta):
    return _manual('El aseguramiento de la validez de los resultados (ensayos de aptitud, intercomparaciones, controles '
                   'internos) se integrará con su módulo. Registre su resumen.')


def o_formacion(r, desde, hasta):
    from capacitacion.models import Asistente, ItemPrograma, Sesion
    ses = Sesion.objects.filter(is_active=True, estado='cerrada', fecha__range=(desde, hasta))
    asis = Asistente.objects.filter(is_active=True, sesion__in=ses)
    prog = ItemPrograma.objects.filter(is_active=True, cancelado=False, fecha_programada__range=(desde, hasta))
    real = prog.filter(fecha_realizada__isnull=False).count()
    return [_bloque('Capacitación', [['Sesiones realizadas (cerradas)', ses.count()], ['Asistencias registradas',
                                                                                       asis.count()],
                                     ['Programadas en el periodo', prog.count()], ['Realizadas del programa', real],
                                     ['Cumplimiento del programa', f'{round(100 * real / prog.count())} %'
                                      if prog.count() else '—']])]


def _cumplimiento_normas():
    """Grado de cumplimiento actual de cada norma (módulo de Cumplimiento)."""
    from cumplimiento.servicio import tablero
    filas = []
    for n in tablero()['normas']:
        pct = f'{n["porcentaje"]} %' if n['porcentaje'] is not None else 'sin evaluar'
        filas.append([n['nombre'], f'{pct} · cobertura {n["cobertura"] or 0} % · {n["en_riesgo"]} en riesgo · '
                                   f'{n["no_cumple"]} no cumplen'])
    return _bloque('Cumplimiento de los requisitos de las normas (estado actual)', filas,
                   'Cumple = 100, parcial = 50, no cumple = 0; no aplica se excluye. Detalle en Cumplimiento.')


def p_desempeno(r, desde, hasta):
    from sst.inspecciones import Inspeccion
    from tnc.models import NIVELES, TIPOS, TrabajoNoConforme
    insp = Inspeccion.objects.filter(is_active=True, fecha__range=(desde, hasta)).exclude(estado='anulada')
    tnc = TrabajoNoConforme.objects.filter(is_active=True, fecha_deteccion__range=(desde, hasta))
    filas = _conteo(tnc, 'tipo', TIPOS) + [[f'Nivel {n}', x] for n, x in _conteo(tnc, 'nivel_riesgo', NIVELES)]
    filas += [['Cerrados', tnc.filter(estado='cerrado').count()],
              ['Con solicitud de acción correctiva', tnc.filter(sac__isnull=False).count()]]
    return [_bloque('Inspecciones programadas', [['Inspecciones registradas en el periodo', insp.count()]]),
            _bloque('Trabajos y salidas no conformes', [['Registrados en el periodo', tnc.count()]] + filas),
            _cumplimiento_normas(),
            _bloque('Indicadores de los procesos', nota='Los indicadores de proceso se integrarán con su módulo; '
                                                        'registre su resumen.')]


def q_proveedores(r, desde, hasta):
    return _manual('La evaluación y reevaluación de proveedores se integrará con el módulo de Proveedores. Registre su '
                   'resumen.')


def r_legal(r, desde, hasta):
    from legal.models import AMBITOS, RESULTADOS, Evaluacion, ResultadoEvaluacion
    nombres = dict(AMBITOS)
    bloques = []
    for ev in Evaluacion.objects.filter(anio__in=_anios(desde, hasta)).order_by('anio', 'ambito'):
        res = ResultadoEvaluacion.objects.filter(evaluacion=ev)
        bloques.append(_bloque(f'Evaluación {ev.anio} · {nombres.get(ev.ambito, ev.ambito)}'
                               f'{" (" + ev.periodo + ")" if getattr(ev, "periodo", "") else ""}',
                               _conteo(res, 'resultado', RESULTADOS)))
    return bloques or [_bloque('Evaluación del cumplimiento legal', nota='No hay evaluaciones registradas en el periodo.')]


def s_ambiental(r, desde, hasta):
    from ambiente.models import AspectoAmbiental, ConsumoMensual, PesajeResiduos
    asp = list(AspectoAmbiental.objects.filter(estado='vigente'))
    sig = [a for a in asp if a.significativo]
    bloques = [_bloque('Aspectos ambientales', [['Vigentes', len(asp)], ['Significativos', len(sig)]],
                       '; '.join(a.aspecto[:60] for a in sig[:10]))]
    filas = []
    for tipo, unidad in (('energia', 'kWh'), ('agua', 'm³')):
        total = sum(c.consumo for c in ConsumoMensual.objects.filter(is_active=True, tipo=tipo)
                    if desde <= date(c.anio, c.mes, 1) <= hasta)
        filas.append([f'Consumo de {"energía eléctrica" if tipo == "energia" else "agua"}', f'{total:,.2f} {unidad}'])
    bloques.append(_bloque('Consumos en el periodo', filas))
    pes = PesajeResiduos.objects.filter(estado='cerrado', tipo='ingreso', fecha__range=(desde, hasta))
    tot = [p.totales() for p in pes]
    bloques.append(_bloque('Residuos sólidos generados', [
        ['No peligrosos', f'{sum(t["no_peligrosos_kg"] for t in tot):,.2f} kg'],
        ['Peligrosos', f'{sum(t["peligrosos_kg"] for t in tot):,.2f} kg'], ['Pesajes cerrados', len(tot)]]))
    return bloques


def t_sst(r, desde, hasta):
    from sst.eventos import ESTADOS_EVENTO, TIPOS_EVENTO, EnfermedadOcupacional, Evento
    ev = Evento.objects.filter(is_active=True, fecha_hora__date__range=(desde, hasta)).exclude(estado='anulado')
    enf = EnfermedadOcupacional.objects.filter(is_active=True, fecha__range=(desde, hasta)).exclude(estado='anulada')
    abiertos = ev.exclude(estado='cerrado')
    return [_bloque('Eventos de SST en el periodo', _conteo(ev, 'tipo', TIPOS_EVENTO)
                    + [['Enfermedades ocupacionales', enf.count()],
                       ['Investigaciones sin cerrar', abiertos.count()]]),
            _bloque('Estado de las investigaciones', _conteo(ev, 'estado', ESTADOS_EVENTO))]


def u_iperc(r, desde, hasta):
    from sst.models import AprobacionIPERC, FilaIPERC
    filas = FilaIPERC.objects.filter(estado='vigente')
    areas = filas.values('area').distinct().count()
    aprob = AprobacionIPERC.objects.filter(fecha__range=(desde, hasta))
    actualizadas = filas.filter(updated_at__date__range=(desde, hasta)).count()
    return [_bloque('Matriz IPERC', [['Filas vigentes', filas.count()], ['Áreas', areas],
                                     ['Filas actualizadas en el periodo', actualizadas],
                                     ['Aprobaciones del Comité en el periodo', aprob.count()]])]


def v_participacion(r, desde, hasta):
    from sst.comite import ESTADOS_ACUERDO, AcuerdoComite, ComiteSST, ReunionComite
    hoy = timezone.localdate()
    c = ComiteSST.objects.filter(is_active=True, fecha_instalacion__lte=hoy, fecha_fin__gte=hoy).first()
    reu = ReunionComite.objects.filter(is_active=True, fecha__range=(desde, hasta))
    acu = AcuerdoComite.objects.filter(is_active=True, reunion__in=reu)
    return [_bloque('Comité de SST', [['Comité vigente', c.periodo if c else 'Sin comité vigente'],
                                      ['Reuniones realizadas', reu.filter(estado='realizada').count()],
                                      ['Reuniones programadas', reu.count()]]),
            _bloque('Acuerdos del Comité en el periodo', _conteo(acu, 'estado', ESTADOS_ACUERDO))]


def w_ssoma(r, desde, hasta):
    from capacitacion.models import Sesion
    from sst.comite import ProgramaSSOMA
    from sst.inspecciones import Monitoreo, RecomendacionMonitoreo
    bloques = []
    for anio in _anios(desde, hasta):
        p = ProgramaSSOMA.objects.filter(anio=anio).first()
        if p:
            acts = list(p.actividades.filter(is_active=True))
            av = round(sum(a.avance for a in acts) / len(acts)) if acts else 0
            bloques.append(_bloque(f'Programa Anual SSOMA {anio}', [['Actividades', len(acts)],
                                                                   ['Avance promedio', f'{av} %'],
                                                                   ['Estado', p.get_estado_display()]]))
    sim = Sesion.objects.filter(is_active=True, fecha__range=(desde, hasta), tipo_actividad='simulacro') \
        .exclude(estado='anulada')
    mon = Monitoreo.objects.filter(is_active=True, fecha__range=(desde, hasta)).exclude(estado='anulado')
    rec = RecomendacionMonitoreo.objects.filter(is_active=True).exclude(estado__in=['ejecutada', 'no_aplica'])
    bloques.append(_bloque('Simulacros y monitoreos', [['Simulacros realizados', sim.count()],
                                                       ['Monitoreos registrados', mon.count()],
                                                       ['Recomendaciones de monitoreo pendientes', rec.count()]]))
    return bloques


FUENTES = {'a': a_contexto, 'b': b_objetivos, 'c': c_documentos, 'd': d_acuerdos_anteriores,
           'e': e_auditorias_internas, 'f': f_acciones_correctivas, 'g': g_organismos_externos, 'h': h_volumen,
           'i': i_retroalimentacion, 'j': j_quejas, 'k': k_mejoras, 'l': l_recursos, 'm': m_riesgos, 'n': n_validez,
           'o': o_formacion, 'p': p_desempeno, 'q': q_proveedores, 'r': r_legal, 's': s_ambiental, 't': t_sst,
           'u': u_iperc, 'v': v_participacion, 'w': w_ssoma}


def periodo(r):
    hoy = timezone.localdate()
    desde = r.periodo_desde or date((r.fecha or hoy).year, 1, 1)
    hasta = r.periodo_hasta or (r.fecha or hoy)
    return desde, hasta


def generar(r, clave):
    """Datos de una entrada; si un módulo falla, lo informa en el bloque en lugar de interrumpir la revisión."""
    desde, hasta = periodo(r)
    try:
        return FUENTES[clave](r, desde, hasta)
    except Exception as e:  # pragma: no cover - se informa en pantalla
        return [_bloque('No se pudieron obtener los datos', nota=f'{type(e).__name__}: {e}')]
