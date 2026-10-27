"""
Evidencia automática del cumplimiento: cada verificación consulta un módulo del sistema y devuelve su resultado
para los requisitos que sustenta.

Niveles: «conforme» (la evidencia está al día), «alerta» (algo vencido, no aprobado o inexistente: hecho objetivo) e
«informativo» (conteos que el evaluador interpreta). Solo la alerta deja un requisito «en riesgo».
"""
from datetime import timedelta

from django.utils import timezone

CONFORME, ALERTA, INFO = 'conforme', 'alerta', 'informativo'


def _r(nivel, texto, ruta):
    return {'nivel': nivel, 'texto': texto, 'ruta': ruta}


def _hace(dias):
    return timezone.localdate() - timedelta(days=dias)


# ------------------------------------------------------------------------------------------------ verificaciones
def auditorias():
    from esynapse_sig.models import Auditoria, ProgramaAuditoria
    anio = timezone.localdate().year
    p = ProgramaAuditoria.objects.filter(anio=anio, is_active=True).first()
    hechas = Auditoria.objects.filter(is_active=True, programa__anio=anio, estado='cerrada').count()
    total = Auditoria.objects.filter(is_active=True, programa__anio=anio).count()
    if not p or p.estado != 'aprobado':
        return _r(ALERTA, f'El programa de auditorías {anio} no está aprobado.', '/auditorias')
    return _r(CONFORME, f'Programa {anio} aprobado (revisión {p.revision}); {hechas} de {total} auditorías cerradas.',
              '/auditorias')


def revision_direccion():
    from revision.models import Revision
    r = Revision.objects.filter(is_active=True, estado='cerrada').order_by('-fecha').first()
    if not r or not r.fecha or r.fecha < _hace(365):
        return _r(ALERTA, 'No hay una revisión por la dirección cerrada en los últimos 12 meses.',
                  '/revision-direccion')
    return _r(CONFORME, f'Última revisión cerrada: {r.codigo} del {r.fecha:%Y-%m-%d}.', '/revision-direccion')


def riesgos():
    from riesgos.models import RevisionMatriz, RiesgoOportunidad
    vigentes = RiesgoOportunidad.objects.filter(is_active=True, estado='vigente')
    rev = RevisionMatriz.objects.filter(matriz='ryo').order_by('-fecha').first()
    if not vigentes.exists():
        return _r(ALERTA, 'La matriz de riesgos y oportunidades no tiene registros vigentes.', '/riesgos')
    if not rev or rev.fecha < _hace(365):
        return _r(ALERTA, f'{vigentes.count()} riesgos y oportunidades vigentes, pero la matriz no se revisa desde '
                          f'hace más de 12 meses.', '/riesgos')
    return _r(CONFORME, f'{vigentes.filter(tipo="riesgo").count()} riesgos y '
                        f'{vigentes.filter(tipo="oportunidad").count()} oportunidades vigentes; última revisión de la '
                        f'matriz el {rev.fecha:%Y-%m-%d}.', '/riesgos')


def imparcialidad():
    from riesgos.models import RiesgoOportunidad
    n = RiesgoOportunidad.objects.filter(is_active=True, estado='vigente', categoria='imparcialidad').count()
    if not n:
        return _r(ALERTA, 'No hay riesgos a la imparcialidad identificados en la matriz de riesgos.', '/riesgos')
    return _r(CONFORME, f'{n} riesgo(s) a la imparcialidad vigentes en la matriz de riesgos.', '/riesgos')


def legal():
    from legal.models import Evaluacion
    e = Evaluacion.objects.filter(is_active=True, estado='cerrada', fecha_cierre__isnull=False) \
        .order_by('-fecha_cierre').first()
    if not e or timezone.localtime(e.fecha_cierre).date() < _hace(365):
        return _r(ALERTA, 'No hay una evaluación del cumplimiento legal cerrada en los últimos 12 meses.', '/legal')
    return _r(CONFORME, f'Última evaluación legal cerrada: {e.get_ambito_display()} {e.anio} '
                        f'({timezone.localtime(e.fecha_cierre):%Y-%m-%d}).', '/legal')


def iperc():
    from sst.models import AprobacionIPERC
    a = AprobacionIPERC.objects.order_by('-fecha').first()
    if not a or a.fecha < _hace(365):
        return _r(ALERTA, 'La matriz IPERC no tiene una aprobación del Comité en los últimos 12 meses.', '/sst')
    return _r(CONFORME, f'Matriz IPERC aprobada por el Comité el {a.fecha:%Y-%m-%d}.', '/sst')


def aspectos():
    from ambiente.models import AprobacionMatrizAmbiental
    a = AprobacionMatrizAmbiental.objects.order_by('-fecha').first()
    if not a or a.fecha < _hace(365):
        return _r(ALERTA, 'La matriz de aspectos ambientales no tiene una aprobación en los últimos 12 meses.',
                  '/medio-ambiente')
    return _r(CONFORME, f'Matriz de aspectos ambientales aprobada el {a.fecha:%Y-%m-%d}.', '/medio-ambiente')


def comite():
    from sst.comite import ComiteSST, ReunionComite
    c = next((x for x in ComiteSST.objects.filter(is_active=True) if x.vigente), None)
    if not c:
        return _r(ALERTA, 'No hay un Comité de SST vigente.', '/sst')
    ultima = ReunionComite.objects.filter(comite=c, is_active=True, estado='realizada').order_by('-fecha').first()
    if not ultima or ultima.fecha < _hace(62):
        return _r(ALERTA, f'Comité de SST {c.periodo} vigente, sin reuniones realizadas en los últimos 2 meses.',
                  '/sst')
    return _r(CONFORME, f'Comité de SST {c.periodo} vigente; última reunión realizada el {ultima.fecha:%Y-%m-%d}.',
              '/sst')


def programa_ssoma():
    from sst.comite import ProgramaSSOMA
    anio = timezone.localdate().year
    p = ProgramaSSOMA.objects.filter(anio=anio).order_by('-version').first()
    if not p or p.estado != 'aprobado':
        return _r(ALERTA, f'El Programa SSOMA {anio} no está aprobado.', '/sst')
    return _r(CONFORME, f'Programa SSOMA {anio} aprobado (versión {p.version}).', '/sst')


def capacitacion():
    from capacitacion.models import ProgramaCapacitacion
    anio = timezone.localdate().year
    p = ProgramaCapacitacion.objects.filter(anio=anio).first()
    if not p or not p.aprobado_en:
        return _r(ALERTA, f'El programa de capacitación {anio} no tiene la aprobación registrada.', '/capacitacion')
    return _r(CONFORME, f'Programa de capacitación {anio} aprobado el '
                        f'{timezone.localtime(p.aprobado_en):%Y-%m-%d}.', '/capacitacion')


def autorizaciones():
    from esynapse_sig.models import Autorizacion
    vig = [a for a in Autorizacion.objects.filter(is_active=True, estado='vigente')]
    vencidas = sum(1 for a in vig if a.estado_seguimiento == 'vencido')
    if not vig:
        return _r(ALERTA, 'No hay autorizaciones vigentes del personal técnico.', '/competencia')
    if vencidas:
        return _r(ALERTA, f'{len(vig)} autorizaciones vigentes; {vencidas} con el seguimiento vencido.',
                  '/competencia')
    return _r(CONFORME, f'{len(vig)} autorizaciones vigentes con el seguimiento al día.', '/competencia')


def equipos():
    from esynapse_sig.models import Equipo
    qs = Equipo.objects.filter(is_active=True, requiere_calibracion=True, estado__in=('operativo', 'calibrado'))
    vencidos = qs.filter(fecha_proxima_calibracion__lt=timezone.localdate()).count()
    if vencidos:
        return _r(ALERTA, f'{vencidos} equipo(s) en uso con la calibración vencida (de {qs.count()} que requieren '
                          f'calibración).', '/equipos')
    return _r(CONFORME, f'{qs.count()} equipos en uso que requieren calibración, todos vigentes.', '/equipos')


def documentos():
    from esynapse_sig.models import VersionDocumento
    vig = VersionDocumento.objects.filter(estado='vigente', documento__is_active=True)
    vencidos = vig.filter(fecha_proxima_revision__lt=timezone.localdate()).count()
    if vencidos:
        return _r(ALERTA, f'{vencidos} documento(s) vigentes con la revisión periódica vencida '
                          f'(de {vig.count()} vigentes).', '/documentos')
    return _r(CONFORME, f'{vig.count()} documentos vigentes con la revisión periódica al día.', '/documentos')


def procesos():
    from procesos.models import Ficha, Proceso
    principales = Proceso.objects.filter(is_active=True, padre__isnull=True)
    sin = [p.nombre for p in principales if not Ficha.objects.filter(proceso=p, estado='vigente').exists()]
    if sin:
        return _r(ALERTA, f'{len(sin)} proceso(s) sin ficha vigente: {", ".join(sin[:4])}'
                          f'{"…" if len(sin) > 4 else ""}.', '/procesos')
    return _r(CONFORME, f'Los {principales.count()} procesos principales tienen ficha vigente.', '/procesos')


def acciones_correctivas():
    from esynapse_sig.models import SolicitudAC
    abiertas = SolicitudAC.objects.filter(is_active=True).exclude(estado__in=('cerrada_conforme', 'cerrada_sin_ac'))
    cerradas = SolicitudAC.objects.filter(is_active=True, estado='cerrada_conforme', fecha_cierre__date__gte=_hace(365))
    return _r(INFO, f'{abiertas.count()} solicitudes de acción correctiva abiertas; {cerradas.count()} cerradas '
                    f'conformes en 12 meses.', '/acciones-correctivas')


def quejas():
    from quejas.models import Queja
    qs = Queja.objects.filter(is_active=True, fecha_recepcion__date__gte=_hace(365))
    return _r(INFO, f'{qs.count()} queja(s) en 12 meses; {qs.exclude(estado="cerrada").count()} abierta(s).', '/quejas')


def trabajo_no_conforme():
    from tnc.models import TrabajoNoConforme
    qs = TrabajoNoConforme.objects.filter(is_active=True, fecha_deteccion__gte=_hace(365)).exclude(estado='anulado')
    return _r(INFO, f'{qs.count()} trabajos o salidas no conformes en 12 meses; '
                    f'{qs.exclude(estado="cerrado").count()} abierto(s).', '/trabajo-no-conforme')


def cambios():
    from cambios.models import Cambio
    qs = Cambio.objects.filter(fecha_solicitud__gte=_hace(365))
    return _r(INFO, f'{qs.count()} solicitudes de cambio en 12 meses.', '/cambios')


def monitoreos():
    from sst.inspecciones import ProgramaMonitoreo
    anio = timezone.localdate().year
    if not ProgramaMonitoreo.objects.filter(anio=anio).exists():
        return _r(INFO, f'No hay programa de monitoreos ocupacionales {anio} registrado.', '/sst')
    return _r(INFO, f'Programa de monitoreos ocupacionales {anio} registrado.', '/sst')


def consumos():
    from ambiente.models import ConsumoMensual
    hoy = timezone.localdate()
    n = ConsumoMensual.objects.filter(anio=hoy.year).count()
    return _r(INFO, f'{n} registros de consumo de energía y agua en {hoy.year}.', '/medio-ambiente')


# ------------------------------------------------------------------------------------------------ correspondencia
# (clave, título, función, {norma: [cláusulas o numerales; un prefijo «8.8» cubre 8.8.1, 8.8.2…]})
ISO = ('iso_9001', 'iso_14001', 'iso_45001')
VERIFICACIONES = [
    ('auditorias', 'Programa y auditorías internas', auditorias,
     {**{n: ['9.2'] for n in ISO}, 'iso_17025': ['8.8']}),
    ('revision', 'Revisión por la dirección', revision_direccion,
     {**{n: ['9.3'] for n in ISO}, 'iso_17025': ['8.9']}),
    ('riesgos', 'Matriz de riesgos y oportunidades', riesgos,
     {**{n: ['6.1'] for n in ISO}, 'iso_17025': ['8.5']}),
    ('imparcialidad', 'Riesgos a la imparcialidad', imparcialidad, {'iso_17025': ['4.1.4', '4.1.5']}),
    ('legal', 'Evaluación del cumplimiento legal', legal,
     {'iso_14001': ['6.1', '9.1'], 'iso_45001': ['6.1', '9.1']}),
    ('iperc', 'Matriz IPERC', iperc, {'iso_45001': ['6.1']}),
    ('aspectos', 'Matriz de aspectos ambientales', aspectos, {'iso_14001': ['6.1']}),
    ('comite', 'Comité de SST', comite, {'iso_45001': ['5.4']}),
    ('ssoma', 'Programa SSOMA', programa_ssoma, {'iso_14001': ['6.2'], 'iso_45001': ['6.2']}),
    ('capacitacion', 'Programa de capacitación', capacitacion, {n: ['7.2', '7.3'] for n in ISO}),
    ('autorizaciones', 'Autorizaciones del personal técnico', autorizaciones,
     {'iso_9001': ['7.2'], 'iso_17025': ['6.2.5', '6.2.6']}),
    ('equipos', 'Calibración de equipos', equipos,
     {'iso_9001': ['7.1'], 'iso_17025': ['6.4.7', '6.4.13', '6.5.1']}),
    ('documentos', 'Lista maestra de documentos', documentos,
     {**{n: ['7.5'] for n in ISO}, 'iso_17025': ['8.3']}),
    ('procesos', 'Fichas de proceso', procesos, {**{n: ['4.4'] for n in ISO}, 'iso_17025': ['8.2']}),
    ('sac', 'Acciones correctivas', acciones_correctivas,
     {**{n: ['10.2'] for n in ISO}, 'iso_17025': ['8.7']}),
    ('quejas', 'Quejas', quejas, {'iso_9001': ['9.1'], 'iso_17025': ['7.9']}),
    ('tnc', 'Trabajo no conforme', trabajo_no_conforme, {'iso_9001': ['8.7'], 'iso_17025': ['7.10']}),
    ('cambios', 'Control de cambios', cambios, {'iso_9001': ['6.3'], 'iso_45001': ['8.1']}),
    ('monitoreos', 'Monitoreos ocupacionales', monitoreos, {'iso_45001': ['9.1']}),
    ('consumos', 'Consumos de energía y agua', consumos, {'iso_14001': ['9.1']}),
]


def _cubre(prefijos, codigo):
    return any(codigo == p or codigo.startswith(p + '.') for p in prefijos)


def claves_para(norma, codigo):
    return [clave for clave, _, _, mapa in VERIFICACIONES if _cubre(mapa.get(norma, []), codigo)]


class Evidencias:
    """Calcula cada verificación una sola vez por consulta y la reparte a los requisitos."""

    def __init__(self):
        self._cache = {}

    def resultado(self, clave):
        if clave not in self._cache:
            titulo, funcion = next((t, f) for c, t, f, _ in VERIFICACIONES if c == clave)
            try:
                r = funcion()
            except Exception as e:  # pragma: no cover - un módulo con error no debe tumbar la matriz
                r = _r(INFO, f'No se pudo consultar: {type(e).__name__}.', '')
            self._cache[clave] = {'clave': clave, 'titulo': titulo, **r}
        return self._cache[clave]

    def para(self, norma, codigo):
        return [self.resultado(c) for c in claves_para(norma, codigo)]
