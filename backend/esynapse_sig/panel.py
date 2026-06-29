"""
eSYNAPSE 360 — Endpoints agregadores transversales.

Reúnen, en un solo lugar, lo que está asignado a cada persona a lo largo de
todos los módulos (Hallazgos, Acciones Correctivas, Documentos, Auditorías):
- MisTareasView  → buzón de tareas pendientes del usuario autenticado.
- CalendarioView → pendientes con fecha, para el calendario general
  (con filtro opcional por persona).
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

        # Hallazgos asignados (no cerrados)
        for h in (Hallazgo.objects.filter(responsable=u, is_active=True)
                  .exclude(estado='cerrado')):
            tareas.append({
                'tipo': 'hallazgo', 'modulo': 'Hallazgos', 'ruta': '/hallazgos',
                'codigo': h.codigo, 'titulo': (h.descripcion or '')[:100],
                'estado': h.get_estado_display(), 'fecha': None,
            })

        # SAC donde soy responsable o verificador (abiertas)
        sacs = SolicitudAC.objects.filter(is_active=True).exclude(estado__in=CERRADAS_SAC)
        for s in sacs.filter(responsable=u):
            tareas.append({
                'tipo': 'sac', 'modulo': 'Acciones Correctivas', 'ruta': '/acciones-correctivas',
                'codigo': s.codigo, 'titulo': (s.descripcion_nc or '')[:100],
                'estado': s.get_estado_display(), 'fecha': None, 'rol': 'responsable',
            })
        for s in sacs.filter(verificador=u).exclude(responsable=u):
            tareas.append({
                'tipo': 'sac', 'modulo': 'Acciones Correctivas', 'ruta': '/acciones-correctivas',
                'codigo': s.codigo, 'titulo': (s.descripcion_nc or '')[:100],
                'estado': s.get_estado_display(), 'fecha': None, 'rol': 'verificador',
            })

        # Acciones de SAC asignadas y pendientes (con fecha propuesta)
        for a in (AccionSAC.objects.filter(responsable=u, estado='pendiente')
                  .select_related('solicitud')):
            tareas.append({
                'tipo': 'accion', 'modulo': 'Acciones Correctivas', 'ruta': '/acciones-correctivas',
                'codigo': a.solicitud.codigo, 'titulo': (a.descripcion or '')[:100],
                'estado': a.get_tipo_display(), 'fecha': _f(a.fecha_propuesta),
            })

        # Documentos que elaboré y fueron devueltos para corregir
        for v in (VersionDocumento.objects.filter(
                    elaborado_por=u, estado='borrador', requiere_recarga=True)
                  .select_related('documento')):
            tareas.append({
                'tipo': 'documento', 'modulo': 'Documentos', 'ruta': '/documentos',
                'codigo': v.documento.codigo, 'titulo': f'Corregir: {v.documento.titulo}'[:100],
                'estado': 'Devuelto', 'fecha': None,
            })

        # Auditorías donde participo (líder o equipo), no cerradas
        auds = Auditoria.objects.filter(is_active=True).exclude(estado='cerrada')
        vistos = set()
        for a in auds.filter(auditor_lider=u):
            vistos.add(a.id)
            tareas.append({
                'tipo': 'auditoria', 'modulo': 'Auditorías', 'ruta': '/auditorias',
                'codigo': a.codigo, 'titulo': (a.areas_procesos or a.objetivo or '')[:100],
                'estado': a.get_estado_display(), 'fecha': _f(a.fecha_inicio or a.fecha_programada),
                'rol': 'líder',
            })
        for a in auds.filter(equipo__usuario=u).exclude(id__in=vistos).distinct():
            tareas.append({
                'tipo': 'auditoria', 'modulo': 'Auditorías', 'ruta': '/auditorias',
                'codigo': a.codigo, 'titulo': (a.areas_procesos or a.objetivo or '')[:100],
                'estado': a.get_estado_display(), 'fecha': _f(a.fecha_inicio or a.fecha_programada),
                'rol': 'equipo',
            })

        return Response({'total': len(tareas), 'tareas': tareas})


class CalendarioView(APIView):
    """
    Pendientes con fecha para el calendario general.
    ?usuario=<id> filtra solo lo asignado a esa persona.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuario_id = request.query_params.get('usuario') or None
        eventos = []

        # Acciones correctivas con fecha (responsable)
        acc = (AccionSAC.objects.filter(estado='pendiente', fecha_propuesta__isnull=False)
               .select_related('solicitud', 'responsable'))
        if usuario_id:
            acc = acc.filter(responsable_id=usuario_id)
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
        if not usuario_id:
            from .models import Equipo
            hoy = timezone.now().date()
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
        if not usuario_id:
            for v in (VersionDocumento.objects.filter(
                        estado='vigente', fecha_proxima_revision__isnull=False)
                      .select_related('documento')):
                eventos.append({
                    'fecha': _f(v.fecha_proxima_revision), 'tipo': 'revision_doc', 'color': 'ambar',
                    'modulo': 'Documentos', 'ruta': '/documentos',
                    'titulo': f'Revisión: {v.documento.codigo}', 'persona': None,
                })

        return Response({'eventos': eventos})
