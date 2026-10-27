"""
eSYNAPSE 360 — Endpoints agregadores transversales.

Reúnen, en un solo lugar, lo que está asignado a cada persona a lo largo de
todos los módulos (Hallazgos, Acciones Correctivas, Documentos, Auditorías):
- MisTareasView  → buzón de tareas pendientes del usuario autenticado.
- CalendarioView → pendientes con fecha, para el calendario general
  (con filtro opcional por persona).
- BuscarView     → búsqueda global (Ctrl + K) por código o texto en los registros
  que el usuario puede leer.
"""
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AccionSAC, Auditoria, Hallazgo, SolicitudAC, VersionDocumento

CERRADAS_SAC = ['cerrada_conforme', 'cerrada_sin_ac']


def _nombre(u):
    return (u.get_full_name() or u.username) if u else None


def _f(fecha):
    return fecha.isoformat() if fecha else None


class MisTareasView(APIView):
    """Tareas pendientes asignadas al usuario autenticado (buzón)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        tareas = []

        # No conformidades asignadas que aún no se derivan a una solicitud de
        # acción correctiva (su tratamiento sigue en la solicitud).
        for h in Hallazgo.objects.filter(responsable=u, is_active=True, estado='registrado',
                                         tipo__in=('nc_mayor', 'nc_menor'), sac__isnull=True):
            tareas.append({
                'tipo': 'hallazgo', 'modulo': 'Hallazgos', 'ruta': '/hallazgos',
                'id': h.id, 'codigo': h.codigo, 'titulo': (h.descripcion or '')[:100],
                'estado': h.get_estado_display(), 'fecha': None,
            })

        # SAC donde soy responsable o verificador (abiertas)
        sacs = SolicitudAC.objects.filter(is_active=True).exclude(estado__in=CERRADAS_SAC)
        for s in sacs.filter(responsable=u):
            tareas.append({
                'tipo': 'sac', 'modulo': 'Acciones Correctivas', 'ruta': '/acciones-correctivas',
                'id': s.id, 'codigo': s.codigo, 'titulo': (s.descripcion_nc or '')[:100],
                'estado': s.get_estado_display(), 'fecha': None, 'rol': 'responsable',
            })
        for s in sacs.filter(verificador=u).exclude(responsable=u):
            tareas.append({
                'tipo': 'sac', 'modulo': 'Acciones Correctivas', 'ruta': '/acciones-correctivas',
                'id': s.id, 'codigo': s.codigo, 'titulo': (s.descripcion_nc or '')[:100],
                'estado': s.get_estado_display(), 'fecha': None, 'rol': 'verificador',
            })

        # Acciones de SAC asignadas y pendientes (con fecha propuesta)
        for a in (AccionSAC.objects.filter(responsable=u, estado='pendiente')
                  .select_related('solicitud')):
            tareas.append({
                'tipo': 'accion', 'modulo': 'Acciones Correctivas', 'ruta': '/acciones-correctivas',
                'id': a.solicitud_id, 'codigo': a.solicitud.codigo, 'titulo': (a.descripcion or '')[:100],
                'estado': a.get_tipo_display(), 'fecha': _f(a.fecha_propuesta),
            })

        # Documentos que elaboré y fueron devueltos para corregir
        for v in (VersionDocumento.objects.filter(
                    elaborado_por=u, estado='borrador', requiere_recarga=True)
                  .select_related('documento')):
            tareas.append({
                'tipo': 'documento', 'modulo': 'Documentos', 'ruta': '/documentos',
                'id': v.documento_id, 'codigo': v.documento.codigo, 'titulo': f'Corregir: {v.documento.titulo}'[:100],
                'estado': 'Devuelto', 'fecha': None,
            })

        # Auditorías donde participo (líder o equipo), no cerradas
        auds = Auditoria.objects.filter(is_active=True).exclude(estado='cerrada')
        vistos = set()
        for a in auds.filter(auditor_lider=u):
            vistos.add(a.id)
            tareas.append({
                'tipo': 'auditoria', 'modulo': 'Auditorías', 'ruta': '/auditorias',
                'id': a.id, 'codigo': a.codigo, 'titulo': (a.areas_procesos or a.objetivo or '')[:100],
                'estado': a.get_estado_display(), 'fecha': _f(a.fecha_inicio or a.fecha_programada),
                'rol': 'líder',
            })
        for a in auds.filter(equipo__usuario=u).exclude(id__in=vistos).distinct():
            tareas.append({
                'tipo': 'auditoria', 'modulo': 'Auditorías', 'ruta': '/auditorias',
                'id': a.id, 'codigo': a.codigo, 'titulo': (a.areas_procesos or a.objetivo or '')[:100],
                'estado': a.get_estado_display(), 'fecha': _f(a.fecha_inicio or a.fecha_programada),
                'rol': 'equipo',
            })

        # Seguimiento de competencia técnica (mis autorizaciones por vencer / vencidas)
        from .models import Autorizacion
        for a in (Autorizacion.objects.filter(usuario=u, estado='vigente', is_active=True)
                  .select_related('metodo')):
            es = a.estado_seguimiento
            if es in ('por_vencer', 'vencido'):
                tareas.append({
                    'tipo': 'competencia', 'modulo': 'Competencia Técnica', 'ruta': '/competencia',
                    'codigo': (a.metodo.codigo if a.metodo else '') or '',
                    'titulo': (f'Seguimiento de competencia: {a.metodo.nombre}' if a.metodo
                               else 'Seguimiento de competencia')[:100],
                    'estado': 'Vencido' if es == 'vencido' else 'Por vencer',
                    'fecha': _f(a.fecha_proximo_seguimiento),
                })

        # Registro mensual del consumo de los suministros a cargo de mi puesto (Medio ambiente)
        from ambiente.tareas import lecturas_pendientes
        tareas += lecturas_pendientes(u)

        # Acuerdos de la revisión por la dirección a mi cargo, sin cerrar
        from revision.tareas import acuerdos_pendientes
        tareas += acuerdos_pendientes(u)

        # Trabajos y salidas no conformes por tratar, autorizar, evaluar o cerrar
        from tnc.tareas import pendientes_tnc
        tareas += pendientes_tnc(u)

        return Response({'total': len(tareas), 'tareas': tareas})


class CalendarioView(APIView):
    """
    Pendientes con fecha para el calendario general.
    ?usuario=<id> filtra solo lo asignado a esa persona.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuario_id = request.query_params.get('usuario') or None
        if usuario_id and not str(usuario_id).isdigit():
            usuario_id = None
        eventos = []
        # Cada bloque se muestra solo si el módulo está habilitado y el usuario puede leerlo.
        from core.models import ModuloHabilitado
        habilitados = ModuloHabilitado.claves_habilitadas()

        def ve(modulo):
            return modulo in habilitados and request.user.tiene_permiso(modulo, 'leer')

        # Acciones correctivas con fecha (responsable)
        acc = (AccionSAC.objects.filter(estado='pendiente', fecha_propuesta__isnull=False)
               .select_related('solicitud', 'responsable'))
        if usuario_id:
            acc = acc.filter(responsable_id=usuario_id)
        if not ve('acciones_correctivas'):
            acc = acc.none()
        for a in acc:
            eventos.append({
                'fecha': _f(a.fecha_propuesta), 'tipo': 'accion', 'color': 'verde',
                'modulo': 'Acciones Correctivas', 'ruta': '/acciones-correctivas',
                'titulo': f'{a.solicitud.codigo}: {(a.descripcion or "")[:60]}',
                'persona': _nombre(a.responsable),
            })

        # Auditorías programadas (auditor líder)
        au = (Auditoria.objects.filter(is_active=True).exclude(estado='cerrada')
              .select_related('auditor_lider'))
        if usuario_id:
            au = au.filter(auditor_lider_id=usuario_id)
        if not ve('auditorias'):
            au = au.none()
        for a in au:
            f = a.fecha_inicio or a.fecha_programada
            if not f:
                continue
            eventos.append({
                'fecha': _f(f), 'tipo': 'auditoria', 'color': 'azul',
                'modulo': 'Auditorías', 'ruta': '/auditorias',
                'titulo': f'{a.codigo}: {(a.areas_procesos or "")[:60]}',
                'persona': _nombre(a.auditor_lider),
            })

        # Calibración de equipos (no atribuible a persona; vista general)
        if not usuario_id and ve('equipos'):
            from .models import Equipo
            hoy = timezone.localdate()
            for e in Equipo.objects.filter(is_active=True, requiere_calibracion=True,
                                           fecha_proxima_calibracion__isnull=False):
                vencido = e.fecha_proxima_calibracion < hoy
                eventos.append({
                    'fecha': _f(e.fecha_proxima_calibracion), 'tipo': 'calibracion',
                    'color': 'rojo' if vencido else 'ambar',
                    'modulo': 'Equipos', 'ruta': '/equipos',
                    'titulo': f'Calibración: {e.codigo} {(e.nombre or "")[:40]}', 'persona': None,
                })

        # Próxima revisión de documentos vigentes (no atribuible a persona;
        # solo en la vista general, sin filtro por persona)
        if not usuario_id and ve('documentos'):
            for v in (VersionDocumento.objects.filter(
                        estado='vigente', fecha_proxima_revision__isnull=False,
                        documento__is_active=True, documento__archivado=False)
                      .select_related('documento')):
                eventos.append({
                    'fecha': _f(v.fecha_proxima_revision), 'tipo': 'revision_doc', 'color': 'ambar',
                    'modulo': 'Documentos', 'ruta': '/documentos',
                    'titulo': f'Revisión: {v.documento.codigo}', 'persona': None,
                })

        # Seguimiento de competencia técnica (atribuible a la persona)
        from .models import Autorizacion
        aut = Autorizacion.objects.filter(estado='vigente', is_active=True).select_related('usuario', 'metodo')
        if usuario_id:
            aut = aut.filter(usuario_id=usuario_id)
        if not ve('competencia_tecnica'):
            aut = aut.none()
        for a in aut:
            prox = a.fecha_proximo_seguimiento
            if not prox:
                continue
            vencido = a.estado_seguimiento == 'vencido'
            eventos.append({
                'fecha': _f(prox), 'tipo': 'seguimiento', 'color': 'rojo' if vencido else 'ambar',
                'modulo': 'Competencia Técnica', 'ruta': '/competencia',
                'titulo': (f'Seguimiento: {_nombre(a.usuario)}'
                           + (f' · {a.metodo.nombre}' if a.metodo else ''))[:70],
                'persona': _nombre(a.usuario),
            })

        return Response({'eventos': eventos})


# ---------------------------------------------------------------------------
# Búsqueda global (Ctrl + K). Por cada módulo: modelo, campos donde buscar, cómo
# titular el resultado y la ruta de su pantalla. Solo se consulta un módulo si está
# habilitado (licencia) y el usuario puede leerlo; los registros dados de baja no salen.
# ---------------------------------------------------------------------------
def _fuentes_busqueda():
    from cambios.models import Cambio
    from quejas.models import Queja
    from revision.models import Revision
    from riesgos.models import RiesgoOportunidad
    from tnc.models import TrabajoNoConforme
    from .models import Documento, Equipo
    return [
        ('hallazgos', 'Hallazgos', '/hallazgos', Hallazgo, ('codigo', 'descripcion'),
         lambda o: o.descripcion),
        ('acciones_correctivas', 'Acciones correctivas', '/acciones-correctivas', SolicitudAC,
         ('codigo', 'descripcion_nc'), lambda o: o.descripcion_nc),
        ('quejas', 'Quejas', '/quejas', Queja, ('codigo', 'empresa', 'motivo', 'descripcion'),
         lambda o: f'{o.empresa} · {o.motivo}'),
        ('cambios', 'Cambios', '/cambios', Cambio, ('codigo', 'descripcion'), lambda o: o.descripcion),
        ('auditorias', 'Auditorías', '/auditorias', Auditoria, ('codigo', 'areas_procesos', 'objetivo'),
         lambda o: o.areas_procesos or o.objetivo),
        ('documentos', 'Documentos', '/documentos', Documento, ('codigo', 'titulo'), lambda o: o.titulo),
        ('equipos', 'Equipos', '/equipos', Equipo, ('codigo', 'nombre', 'serie', 'marca', 'modelo'),
         lambda o: ' · '.join(x for x in (o.nombre, o.marca, o.serie) if x)),
        ('riesgos', 'Riesgos y oportunidades', '/riesgos', RiesgoOportunidad, ('codigo', 'descripcion'),
         lambda o: o.descripcion),
        ('trabajo_no_conforme', 'Trabajo no conforme', '/trabajo-no-conforme', TrabajoNoConforme,
         ('codigo', 'descripcion', 'referencias'), lambda o: o.descripcion),
        ('revision_direccion', 'Revisión por la dirección', '/revision-direccion', Revision,
         ('codigo', 'conclusiones'), lambda o: f'Revisión {o.get_tipo_display().lower()}'),
    ]


_VOCALES = {'a': '[aáàä]', 'e': '[eéèë]', 'i': '[iíìï]', 'o': '[oóòö]', 'u': '[uúùü]', 'n': '[nñ]', 'c': '[cç]'}


def _patron_sin_tildes(texto):
    """Expresión regular que encuentra el texto con o sin tildes («manometro» → «Manómetro»)."""
    import re
    import unicodedata
    partes = []
    for ch in texto:
        base = unicodedata.normalize('NFD', ch.lower())[0]
        partes.append(_VOCALES.get(base, re.escape(ch)))
    return ''.join(partes)


def _tiene_campo(modelo, campo):
    try:
        modelo._meta.get_field(campo)
        return True
    except Exception:  # noqa: BLE001 — campo inexistente en ese modelo
        return False


class BuscarView(APIView):
    """GET ?q=texto → hasta 6 resultados por módulo, primero los de código exacto o que empiezan igual."""
    permission_classes = [IsAuthenticated]
    POR_MODULO = 6

    def get(self, request):
        from django.db.models import Q
        from core.models import ModuloHabilitado
        q = (request.query_params.get('q') or '').strip()
        if len(q) < 2:
            return Response({'q': q, 'resultados': []})
        u = request.user
        habilitados = ModuloHabilitado.claves_habilitadas()
        patron = _patron_sin_tildes(q[:60])
        resultados = []
        for modulo, nombre_modulo, ruta, modelo, campos, titular in _fuentes_busqueda():
            if modulo not in habilitados or not (u.is_superuser or u.tiene_permiso(modulo, 'leer')):
                continue
            filtro = Q()
            for c in campos:
                if _tiene_campo(modelo, c):
                    filtro |= Q(**{f'{c}__iregex': patron})
            qs = modelo.objects.filter(filtro)
            if _tiene_campo(modelo, 'is_active'):
                qs = qs.filter(is_active=True)
            filas = list(qs.order_by('-id')[:40])
            ql = q.lower()
            filas.sort(key=lambda o: (0 if (o.codigo or '').lower() == ql else 1 if (o.codigo or '').lower().startswith(ql) else 2))
            for o in filas[:self.POR_MODULO]:
                estado = o.get_estado_display() if hasattr(o, 'get_estado_display') else ''
                resultados.append({
                    'modulo': modulo, 'modulo_nombre': nombre_modulo, 'ruta': ruta, 'id': o.id,
                    'codigo': o.codigo, 'titulo': ' '.join(str(titular(o) or '').split())[:140], 'estado': estado,
                })
        return Response({'q': q, 'resultados': resultados})
