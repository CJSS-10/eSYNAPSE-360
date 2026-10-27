from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular

from .models import (CLASIFICACIONES, CRITERIOS_EFICACIA, DESTINATARIOS, ESTADOS_CAMBIO, FUENTES_PLANIFICACION,
                     IMPACTOS, MEDIOS,
                     MOMENTOS_FOTO, MOTIVOS_ORIGEN, ORIGENES, PREVISION, PRIORIDADES, REVERSIONES, TEMPORALIDAD,
                     ActividadCambio, Cambio, ComunicacionCambio, FotoCambio)
from .serializers import CambioListaSerializer, CambioSerializer

ETAPAS_PLAN = ('en_evaluacion', 'en_planificacion')
ETAPAS_COMUNICACION = ('en_planificacion', 'en_implementacion', 'en_verificacion', 'temporal_vigente')
ETAPAS_PRORROGA = ('en_implementacion', 'en_verificacion', 'temporal_vigente')


def _si(valor):
    if valor is None or valor == '':
        return None
    return str(valor).strip().lower() in ('1', 'true', 'si', 'sí', 'yes', 'on')


def _vacio(texto):
    return not (texto or '').strip()


class CambioViewSet(viewsets.ModelViewSet):
    """
    M17 — Cambios: solicitud → evaluación → resolución del Gerente General →
    planificación → implementación (con comunicación) → verificación de la
    eficacia (reversión si no fue eficaz) → cierre. Un cambio temporal eficaz
    pasa a «temporal en vigor» hasta registrar su fin. Etapa cerrada = solo lectura.
    """
    queryset = Cambio.objects.all().select_related('solicitante', 'proceso_solicitante', 'responsable_evaluador',
                                                   'resuelto_por', 'responsable_implementacion', 'verificado_por',
                                                   'cerrado_por', 'sac_origen', 'sac_derivada', 'fin_temporal_por',
                                                   'cambio_origen')
    permission_classes = [PermisoModular]
    modulo = 'cambios'
    parser_classes = [JSONParser, MultiPartParser, FormParser]


    def get_object(self):
        """Un registro anulado se consulta, pero no avanza en el flujo ni se modifica."""
        obj = super().get_object()
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS') and not getattr(obj, 'is_active', True):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': f'{obj.codigo} está anulado: no se modifica.'})
        return obj
    def get_serializer_class(self):
        return CambioListaSerializer if self.action in ('list',) else CambioSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action in ('list', 'seguimiento_pdf'):
            qs = qs.filter(is_active=True)
        if p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        if p.get('abiertos') == '1':
            qs = qs.exclude(estado__in=['cerrado', 'archivado'])
        if p.get('anio'):
            qs = qs.filter(fecha_solicitud__year=p['anio'])
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(descripcion__icontains=b) | Q(justificacion__icontains=b))
        return qs

    def _error(self, mensaje, codigo=status.HTTP_400_BAD_REQUEST):
        return Response({'detail': mensaje}, status=codigo)

    def _respuesta(self, c, codigo=status.HTTP_200_OK):
        c = Cambio.objects.get(pk=c.pk)
        return Response(CambioSerializer(c, context={'request': self.request}).data, status=codigo)

    def _guardar(self, c, request, campos=None):
        c.updated_by = request.user
        c.save(update_fields=(list(campos) + ['updated_by', 'updated_at']) if campos else None)

    def perform_create(self, serializer):
        u = self.request.user
        datos = {'created_by': u, 'updated_by': u}
        if not serializer.validated_data.get('solicitante'):
            datos['solicitante'] = u
        serializer.save(**datos)

    def update(self, request, *args, **kwargs):
        """Solo se modifican los campos de las etapas abiertas."""
        c = self.get_object()
        if not c.is_active:
            return self._error('La solicitud está anulada.')
        abiertas = c.etapas_abiertas()
        for campo in request.data.keys():
            etapa = Cambio.etapa_de_campo(campo)
            if etapa and etapa not in abiertas:
                nombre = Cambio._meta.get_field(campo).verbose_name
                orden = [e for e, _ in ESTADOS_CAMBIO]
                inicio = next(est[0] for n, est, _ in Cambio.ETAPAS if n == etapa)
                situacion = ('aún no se abre' if orden.index(inicio) > orden.index(c.estado) else 'está cerrada')
                return self._error(f'La etapa de {Cambio.NOMBRES_ETAPA[etapa]} {situacion} '
                                   f'({c.get_estado_display().lower()}): no se modifica «{nombre}».')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Anula (baja lógica) una solicitud registrada por error, antes de evaluarla."""
        c = self.get_object()
        if c.estado != 'solicitado':
            return self._error('Solo se anula una solicitud aún no evaluada.')
        c.is_active = False
        self._guardar(c, request, ['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({
            'prioridades': PRIORIDADES, 'origenes': ORIGENES, 'motivos_origen': MOTIVOS_ORIGEN, 'impactos': IMPACTOS,
            'clasificaciones': CLASIFICACIONES, 'prevision': PREVISION, 'temporalidad': TEMPORALIDAD,
            'fuentes': FUENTES_PLANIFICACION, 'criterios_eficacia': CRITERIOS_EFICACIA, 'reversiones': REVERSIONES,
            'destinatarios': DESTINATARIOS, 'medios': MEDIOS, 'momentos_foto': MOMENTOS_FOTO,
        })
    catalogos.operacion = 'leer'

    # --- 1 → 2 ---
    @action(detail=True, methods=['post'])
    def enviar_evaluacion(self, request, pk=None):
        c = self.get_object()
        if c.estado != 'solicitado':
            return self._error('La solicitud ya fue enviada a evaluación.')
        falta = []
        if not c.proceso_solicitante_id:
            falta.append('el proceso solicitante')
        if _vacio(c.motivo_origen):
            falta.append('el origen del cambio')
        if _vacio(c.descripcion):
            falta.append('la descripción')
        if _vacio(c.justificacion):
            falta.append('la justificación')
        if falta:
            return self._error('Para enviar a evaluación registre ' + ', '.join(falta) + '.')
        c.estado = 'en_evaluacion'
        self._guardar(c, request, ['estado'])
        return self._respuesta(c)
    enviar_evaluacion.operacion = 'editar'

    # --- 2 → 3 ---
    @action(detail=True, methods=['post'])
    def enviar_aprobacion(self, request, pk=None):
        c = self.get_object()
        if c.estado != 'en_evaluacion':
            return self._error('La solicitud no está en evaluación.')
        falta = []
        for campo, nombre in (('factibilidad_tecnica', 'la factibilidad técnica'),
                              ('aspectos_operativos', 'los aspectos operativos'),
                              ('aspectos_financieros', 'los aspectos financieros'), ('beneficios', 'los beneficios'),
                              ('riesgos', 'los riesgos e impactos'), ('controles', 'los controles'),
                              ('consecuencias', 'las consecuencias de no realizarlo')):
            if _vacio(getattr(c, campo)):
                falta.append(nombre)
        if not c.procesos_afectados.exists():
            falta.append('los procesos afectados')
        if not c.clasificacion:
            falta.append('la clasificación (mayor o menor)')
        if not c.responsable_evaluador_id:
            falta.append('el responsable del equipo evaluador')
        if not c.actividades.filter(is_active=True).exists():
            falta.append('al menos una actividad del plan de ejecución')
        if falta:
            return self._error('Para enviar a aprobación registre ' + ', '.join(falta) + '.')
        c.estado = 'en_aprobacion'
        self._guardar(c, request, ['estado'])
        return self._respuesta(c)
    enviar_aprobacion.operacion = 'editar'

    # --- 3. Resolución del Gerente General ---
    @action(detail=True, methods=['post'])
    def resolver(self, request, pk=None):
        """Aprueba o rechaza, con firma (contraseña). Body: {aprobado: bool, comentarios, password}"""
        from procesos.models import avisar_ficha_por_revisar
        c = self.get_object()
        if c.estado != 'en_aprobacion':
            return self._error('La solicitud no está en aprobación.')
        aprobado = _si(request.data.get('aprobado'))
        if aprobado is None:
            return self._error('Indique si el cambio se aprueba o se rechaza.')
        comentarios = (request.data.get('comentarios') or '').strip()
        if not aprobado and not comentarios:
            return self._error('Indique el motivo del rechazo.')
        password = request.data.get('password') or ''
        if not password:
            return self._error('Confirme con su contraseña para firmar la resolución.')
        if not request.user.check_password(password):
            return self._error('Contraseña incorrecta. La resolución no se registró.')
        u, ahora = request.user, timezone.localtime()
        c.resultado = 'aprobado' if aprobado else 'rechazado'
        c.resuelto_por = u
        c.fecha_resolucion = ahora
        c.motivo_resolucion = comentarios
        c.firma_resolucion = {'usuario_id': u.pk, 'nombre': u.get_full_name() or u.username, 'cargo': u.cargo,
                              'sigla': u.sigla_cargo, 'fecha': ahora.isoformat(timespec='seconds'),
                              'ip': get_client_ip(request)}
        c.historial = list(c.historial or []) + [{
            'fecha': ahora.isoformat(timespec='minutes'), 'usuario': u.get_full_name() or u.username,
            'accion': c.get_resultado_display(), 'motivo': comentarios}]
        if aprobado:
            c.estado = 'en_planificacion'
            c.fecha_planificacion = c.fecha_planificacion or timezone.localdate()
        else:
            c.estado = 'rechazado'
        self._guardar(c, request)
        if aprobado:
            for p in c.procesos_afectados.all():
                avisar_ficha_por_revisar(p, f'Se aprobó el cambio {c.codigo}: {c.descripcion[:150]}',
                                         origen='cambio', usuario=u)
        return self._respuesta(c)
    resolver.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def reevaluar(self, request, pk=None):
        """Un cambio rechazado vuelve a evaluación con la propuesta ajustada. Body: {motivo}"""
        c = self.get_object()
        if c.estado != 'rechazado':
            return self._error('Solo se reevalúa un cambio rechazado.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique qué se ajusta para la reevaluación.')
        c.historial = list(c.historial or []) + [{
            'fecha': timezone.localtime().isoformat(timespec='minutes'),
            'usuario': request.user.get_full_name() or request.user.username, 'accion': 'Reevaluación',
            'motivo': motivo}]
        c.estado, c.resultado = 'en_evaluacion', ''
        c.resuelto_por, c.fecha_resolucion, c.motivo_resolucion, c.firma_resolucion = None, None, '', {}
        self._guardar(c, request)
        return self._respuesta(c)
    reevaluar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def archivar(self, request, pk=None):
        """Un cambio rechazado que no se reevalúa se archiva. Body: {motivo}"""
        c = self.get_object()
        if c.estado != 'rechazado':
            return self._error('Solo se archiva un cambio rechazado.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo del archivo.')
        c.historial = list(c.historial or []) + [{
            'fecha': timezone.localtime().isoformat(timespec='minutes'),
            'usuario': request.user.get_full_name() or request.user.username, 'accion': 'Archivado',
            'motivo': motivo}]
        c.estado = 'archivado'
        self._guardar(c, request, ['estado', 'historial'])
        return self._respuesta(c)
    archivar.operacion = 'editar'

    # --- Plan de ejecución / actividades ---
    def _datos_actividad(self, request, a=None):
        from core.models import Usuario
        datos = {}
        if 'actividad' in request.data:
            datos['actividad'] = (request.data.get('actividad') or '').strip()
        if 'responsable' in request.data:
            rid = request.data.get('responsable')
            datos['responsable'] = Usuario.objects.filter(pk=rid, is_active=True).first() if rid else None
        if 'recursos' in request.data:
            datos['recursos'] = (request.data.get('recursos') or '').strip()
        if 'plazo' in request.data:
            datos['plazo'] = parse_date(request.data.get('plazo') or '') if request.data.get('plazo') else None
        return datos

    @action(detail=True, methods=['post'])
    def agregar_actividad(self, request, pk=None):
        c = self.get_object()
        if c.estado not in ETAPAS_PLAN:
            return self._error('Las actividades se definen en la evaluación o en la planificación.')
        datos = self._datos_actividad(request)
        if not datos.get('actividad'):
            return self._error('Describa la actividad.')
        orden = c.actividades.count() + 1
        ActividadCambio.objects.create(cambio=c, orden=orden, created_by=request.user, updated_by=request.user, **datos)
        return self._respuesta(c, status.HTTP_201_CREATED)
    agregar_actividad.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def editar_actividad(self, request, pk=None):
        c = self.get_object()
        if c.estado not in ETAPAS_PLAN:
            return self._error('Las actividades se corrigen en la evaluación o en la planificación.')
        a = c.actividades.filter(pk=request.data.get('actividad_id'), is_active=True).first()
        if not a:
            return self._error('Actividad no encontrada.')
        datos = self._datos_actividad(request, a)
        if 'actividad' in datos and not datos['actividad']:
            return self._error('Describa la actividad.')
        for k, v in datos.items():
            setattr(a, k, v)
        a.updated_by = request.user
        a.save()
        return self._respuesta(c)
    editar_actividad.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_actividad(self, request, pk=None):
        c = self.get_object()
        if c.estado not in ETAPAS_PLAN:
            return self._error('Las actividades se quitan en la evaluación o en la planificación.')
        a = c.actividades.filter(pk=request.data.get('actividad_id'), is_active=True).first()
        if not a:
            return self._error('Actividad no encontrada.')
        a.is_active = False
        a.updated_by = request.user
        a.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return self._respuesta(c)
    quitar_actividad.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def completar_actividad(self, request, pk=None):
        """Multipart: {actividad_id, seguimiento, evidencia}"""
        c = self.get_object()
        if c.estado != 'en_implementacion':
            return self._error('Las actividades se completan durante la implementación.')
        a = c.actividades.filter(pk=request.data.get('actividad_id'), is_active=True).first()
        if not a:
            return self._error('Actividad no encontrada.')
        if a.completada:
            return self._error('La actividad ya está completada.')
        seguimiento = (request.data.get('seguimiento') or '').strip()
        if not seguimiento:
            return self._error('Describa lo realizado (seguimiento).')
        a.seguimiento = seguimiento
        a.completada = True
        a.fecha_completada = timezone.now()
        if request.FILES.get('evidencia'):
            a.evidencia = request.FILES['evidencia']
        a.updated_by = request.user
        a.save()
        return self._respuesta(c)
    completar_actividad.operacion = 'editar'

    # --- 4 → 5 ---
    @action(detail=True, methods=['post'])
    def iniciar_implementacion(self, request, pk=None):
        c = self.get_object()
        if c.estado != 'en_planificacion':
            return self._error('El cambio no está en planificación.')
        falta = []
        acts = list(c.actividades.filter(is_active=True))
        if not acts:
            falta.append('al menos una actividad')
        elif any(not a.responsable_id or not a.plazo for a in acts):
            falta.append('el responsable y el plazo de cada actividad')
        if c.requiere_planificacion:
            if not c.responsable_implementacion_id:
                falta.append('el responsable de la implementación')
            if not c.plazo_implementacion:
                falta.append('el plazo de implementación')
            if not c.prevision:
                falta.append('si el cambio es previsto o no previsto')
            if not c.temporalidad:
                falta.append('si el cambio es temporal o permanente')
            if not c.fuentes and _vacio(c.fuente_otro):
                falta.append('la fuente u origen del cambio')
        if c.temporalidad == 'temporal' and not c.fecha_reversion:
            falta.append('la fecha prevista de reversión del cambio temporal')
        if falta:
            pref = 'Cambio mayor o técnico: la planificación es obligatoria. ' if c.requiere_planificacion else ''
            return self._error(pref + 'Para iniciar la implementación registre ' + ', '.join(falta) + '.')
        if c.afecta_clientes and not c.comunicaciones.filter(is_active=True, destinatario='clientes').exists():
            return self._error('El cambio afecta requisitos acordados con clientes o actividades acreditadas: '
                               'regístrese la comunicación a los clientes antes de implementarlo.')
        # Cambio menor: basta el plan de ejecución; responsable y plazo se toman de sus actividades.
        if not c.responsable_implementacion_id:
            c.responsable_implementacion_id = acts[0].responsable_id
        if not c.plazo_implementacion:
            c.plazo_implementacion = max(a.plazo for a in acts)
        c.estado = 'en_implementacion'
        c.fecha_inicio_implementacion = timezone.now()
        self._guardar(c, request, ['estado', 'fecha_inicio_implementacion', 'responsable_implementacion',
                                   'plazo_implementacion'])
        return self._respuesta(c)
    iniciar_implementacion.operacion = 'editar'

    # --- 5 → 7 ---
    @action(detail=True, methods=['post'])
    def pasar_a_verificacion(self, request, pk=None):
        c = self.get_object()
        if c.estado != 'en_implementacion':
            return self._error('El cambio no está en implementación.')
        pendientes = c.actividades.filter(is_active=True, completada=False).count()
        if pendientes:
            return self._error(f'Faltan completar {pendientes} actividad(es).')
        if not c.comunicaciones.filter(is_active=True).exists():
            return self._error('Registre la comunicación del cambio al personal involucrado y demás partes.')
        c.estado = 'en_verificacion'
        self._guardar(c, request, ['estado'])
        return self._respuesta(c)
    pasar_a_verificacion.operacion = 'editar'

    # --- 8. Cierre ---
    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        c = self.get_object()
        if c.estado != 'en_verificacion':
            return self._error('El cambio no está en verificación de la eficacia.')
        falta = []
        if c.se_implemento is None:
            falta.append('si se implementó')
        if c.fue_eficaz is None:
            falta.append('si fue eficaz')
        if _vacio(c.verificacion):
            falta.append('la verificación de la eficacia')
        if c.fue_eficaz is False and c.reversion == 'ninguna' and not c.sac_derivada_id:
            falta.append('la reversión o la acción correctiva del cambio no eficaz')
        if c.reversion != 'ninguna' and (_vacio(c.detalle_reversion) or not c.fecha_reversion_real):
            falta.append('el detalle y la fecha de la reversión')
        if falta:
            return self._error('Para cerrar registre ' + ', '.join(falta) + '.')
        sin_vigente = [d.codigo for d in c.documentos_actualizados.all() if d.version_en_proceso or not d.version_vigente]
        if sin_vigente:
            return self._error('Documentos aún no aprobados: ' + ', '.join(sin_vigente)
                               + '. La versión anterior rige hasta que se apruebe la nueva.')
        if c.sac_derivada_id and not (c.sac_derivada.estado or '').startswith('cerrada'):
            return self._error(f'La acción correctiva derivada {c.sac_derivada.codigo} aún no está cerrada.')
        u, ahora = request.user, timezone.localtime()
        c.verificado_por = c.verificado_por or u
        c.fecha_verificacion = c.fecha_verificacion or ahora
        if c.queda_en_vigor:
            # La eficacia queda confirmada (solo lectura); el cambio sigue en vigor hasta su fin.
            c.estado = 'temporal_vigente'
        else:
            c.cerrado_por, c.fecha_cierre, c.estado = u, ahora, 'cerrado'
        self._guardar(c, request)
        return self._respuesta(c)
    cerrar.operacion = 'editar'

    # --- Cambio temporal en vigor ---
    @action(detail=True, methods=['post'])
    def prorrogar(self, request, pk=None):
        """Amplía la fecha prevista de fin de un cambio temporal, con firma. Body: {fecha_nueva, motivo, password}"""
        c = self.get_object()
        if c.temporalidad != 'temporal' or c.estado not in ETAPAS_PRORROGA:
            return self._error('Solo se prorroga un cambio temporal en implementación, verificación o en vigor.')
        nueva = parse_date(request.data.get('fecha_nueva') or '')
        if not nueva:
            return self._error('Indique la nueva fecha prevista de fin.')
        if c.fecha_reversion and nueva <= c.fecha_reversion:
            return self._error('La nueva fecha debe ser posterior a la fecha prevista actual '
                               f'({c.fecha_reversion.isoformat()}).')
        if nueva < timezone.localdate():
            return self._error('La nueva fecha no puede ser pasada.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la prórroga.')
        password = request.data.get('password') or ''
        if not password:
            return self._error('Confirme con su contraseña para firmar la prórroga.')
        if not request.user.check_password(password):
            return self._error('Contraseña incorrecta. La prórroga no se registró.')
        u, ahora = request.user, timezone.localtime()
        c.prorrogas = list(c.prorrogas or []) + [{
            'fecha': ahora.isoformat(timespec='seconds'), 'usuario_id': u.pk,
            'usuario': u.get_full_name() or u.username, 'sigla': u.sigla_cargo, 'ip': get_client_ip(request),
            'fecha_anterior': c.fecha_reversion.isoformat() if c.fecha_reversion else '',
            'fecha_nueva': nueva.isoformat(), 'motivo': motivo}]
        c.fecha_reversion = nueva
        self._guardar(c, request, ['prorrogas', 'fecha_reversion'])
        return self._respuesta(c)
    prorrogar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def registrar_fin_temporal(self, request, pk=None):
        """Registra el fin previsto del cambio temporal y lo cierra. Multipart: {fecha, detalle, evidencia}"""
        c = self.get_object()
        if c.estado != 'temporal_vigente':
            return self._error('Solo se registra el fin de un cambio temporal en vigor.')
        fecha = parse_date(request.data.get('fecha') or '')
        if not fecha:
            return self._error('Indique la fecha en que terminó el cambio temporal.')
        if fecha > timezone.localdate():
            return self._error('La fecha de fin no puede ser futura.')
        inicio = timezone.localtime(c.fecha_inicio_implementacion).date() if c.fecha_inicio_implementacion else None
        if inicio and fecha < inicio:
            return self._error('La fecha de fin no puede ser anterior al inicio de la implementación.')
        detalle = (request.data.get('detalle') or '').strip()
        if not detalle:
            return self._error('Describa qué se restituyó al terminar el cambio temporal.')
        u, ahora = request.user, timezone.localtime()
        c.fin_temporal_fecha, c.fin_temporal_detalle, c.fin_temporal_por = fecha, detalle, u
        if request.FILES.get('evidencia'):
            c.fin_temporal_evidencia = request.FILES['evidencia']
        c.cerrado_por, c.fecha_cierre, c.estado = u, ahora, 'cerrado'
        self._guardar(c, request)
        return self._respuesta(c)
    registrar_fin_temporal.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def nuevo_cambio_permanente(self, request, pk=None):
        """Abre una nueva solicitud para volver permanente un cambio temporal en vigor."""
        c = self.get_object()
        if c.estado != 'temporal_vigente':
            return self._error('Solo se propone volver permanente un cambio temporal en vigor.')
        abierta = c.cambios_permanentes.filter(is_active=True).exclude(estado__in=['archivado']).first()
        if abierta:
            return self._error(f'Ya existe la solicitud {abierta.codigo} para volverlo permanente.')
        u = request.user
        nuevo = Cambio.objects.create(
            solicitante=u, proceso_solicitante=c.proceso_solicitante, prioridad=c.prioridad, origen=c.origen,
            motivo_origen=c.motivo_origen, cambio_origen=c,
            descripcion=f'Volver permanente el cambio temporal {c.codigo}: {c.descripcion}',
            justificacion='', created_by=u, updated_by=u)
        return self._respuesta(nuevo, status.HTTP_201_CREATED)
    nuevo_cambio_permanente.operacion = 'crear'

    @action(detail=True, methods=['post'])
    def reabrir(self, request, pk=None):
        """Reabre un cambio cerrado (vuelve a verificación), con motivo."""
        c = self.get_object()
        if c.estado != 'cerrado':
            return self._error('Solo se reabre un cambio cerrado.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la reapertura.')
        c.reaperturas = list(c.reaperturas or []) + [{
            'fecha': timezone.localtime().isoformat(timespec='minutes'),
            'usuario': request.user.get_full_name() or request.user.username, 'motivo': motivo,
            'cerrado_por': c.cerrado_por.get_full_name() if c.cerrado_por_id else '',
            'fecha_cierre': c.fecha_cierre.isoformat(timespec='minutes') if c.fecha_cierre else '',
            'fin_temporal': ({'fecha': c.fin_temporal_fecha.isoformat(), 'detalle': c.fin_temporal_detalle}
                             if c.fin_temporal_fecha else None)}]
        # El fin del cambio temporal se vuelve a registrar al confirmar de nuevo la eficacia.
        c.fin_temporal_fecha, c.fin_temporal_detalle, c.fin_temporal_por = None, '', None
        c.estado, c.cerrado_por, c.fecha_cierre = 'en_verificacion', None, None
        self._guardar(c, request)
        return self._respuesta(c)
    reabrir.operacion = 'aprobar'

    # --- Comunicaciones y fotos ---
    @action(detail=True, methods=['post'])
    def comunicar(self, request, pk=None):
        """Multipart: {destinatario, fecha, medio, resumen, evidencia}"""
        c = self.get_object()
        if c.estado not in ETAPAS_COMUNICACION:
            return self._error('La comunicación se registra desde la planificación hasta la verificación.')
        destinatario, medio = request.data.get('destinatario'), request.data.get('medio')
        if destinatario not in dict(DESTINATARIOS):
            return self._error('Indique a quién se comunicó.')
        if medio not in dict(MEDIOS):
            return self._error('Indique el medio.')
        resumen = (request.data.get('resumen') or '').strip()
        if not resumen:
            return self._error('Resuma lo comunicado (descripción, impactos, fecha de implementación, controles).')
        fecha = parse_date(request.data.get('fecha') or '') or timezone.localdate()
        if fecha > timezone.localdate():
            return self._error('La fecha de la comunicación no puede ser futura.')
        ComunicacionCambio.objects.create(cambio=c, destinatario=destinatario, medio=medio, resumen=resumen,
                                          fecha=fecha, evidencia=request.FILES.get('evidencia'),
                                          created_by=request.user, updated_by=request.user)
        return self._respuesta(c, status.HTTP_201_CREATED)
    comunicar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def agregar_foto(self, request, pk=None):
        """Multipart: {momento, archivo, descripcion}"""
        c = self.get_object()
        if c.estado not in ETAPAS_COMUNICACION:
            return self._error('El registro fotográfico se carga desde la planificación hasta la verificación.')
        momento = request.data.get('momento')
        if momento not in dict(MOMENTOS_FOTO):
            return self._error('Indique si la foto es de antes, durante o después del cambio.')
        if not request.FILES.get('archivo'):
            return self._error('Falta la foto.')
        FotoCambio.objects.create(cambio=c, momento=momento, archivo=request.FILES['archivo'],
                                  descripcion=(request.data.get('descripcion') or '').strip(),
                                  created_by=request.user, updated_by=request.user)
        return self._respuesta(c, status.HTTP_201_CREATED)
    agregar_foto.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_foto(self, request, pk=None):
        c = self.get_object()
        if c.estado not in ETAPAS_COMUNICACION:
            return self._error('El registro fotográfico ya no se modifica.')
        f = c.fotos.filter(pk=request.data.get('foto_id'), is_active=True).first()
        if not f:
            return self._error('Foto no encontrada.')
        f.is_active = False
        f.updated_by = request.user
        f.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return self._respuesta(c)
    quitar_foto.operacion = 'editar'

    # --- Formatos impresos ---
    def _pdf(self, contenido, nombre):
        resp = HttpResponse(contenido, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{nombre}.pdf"'
        return resp

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Solicitud de Cambios."""
        from .pdf import generar_solicitud_pdf
        c = self.get_object()
        return self._pdf(generar_solicitud_pdf(c), f'Solicitud de cambio {c.codigo}')
    pdf.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def planificacion_pdf(self, request, pk=None):
        """Planificación de Cambios."""
        from .pdf import generar_planificacion_pdf
        c = self.get_object()
        return self._pdf(generar_planificacion_pdf(c), f'Planificacion de cambio {c.codigo}')
    planificacion_pdf.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def seguimiento_pdf(self, request):
        """Seguimiento de Cambios (con los filtros del listado)."""
        from .pdf import generar_seguimiento_pdf
        cambios = list(self.filter_queryset(self.get_queryset()).order_by('fecha_solicitud', 'id'))
        return self._pdf(generar_seguimiento_pdf(cambios), 'Seguimiento de cambios')
    seguimiento_pdf.operacion = 'leer'
