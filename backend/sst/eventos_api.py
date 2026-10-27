"""API de incidentes, accidentes, enfermedades ocupacionales y estadísticas de SST."""
import calendar
from datetime import date, datetime, time

from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular

from .eventos import (ACTOS_SUBESTANDAR, AGENTES, CONDICIONES_SUBESTANDAR, ESTADOS_EVENTO, FACTORES_PERSONALES,
                      FACTORES_TRABAJO, GRADOS_INCAPACIDAD, GRAVEDADES, METODOS_ANALISIS, PARTES_CUERPO,
                      TIPOS_ACCIDENTE, TIPOS_AMBIENTAL, TIPOS_EMERGENCIA, TIPOS_EVENTO, TIPOS_LESION, AfectadoEvento,
                      ArchivoEvento, DatosMesSST, EnfermedadOcupacional, Evento, InformeEstadisticasSST)

MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre',
         'Noviembre', 'Diciembre']
SAC_CERRADA = ('cerrada_conforme', 'cerrada_sin_ac')


def _nombre(u):
    return u.get_full_name() or u.username


def _firma(request):
    u = request.user
    return {'usuario_id': u.pk, 'nombre': _nombre(u), 'cargo': getattr(u, 'cargo', ''),
            'sigla': getattr(u, 'sigla_cargo', ''), 'fecha': timezone.localtime().isoformat(timespec='seconds'),
            'ip': get_client_ip(request)}


def _hist(obj, request, accion, **datos):
    obj.historial = list(obj.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                  'usuario': _nombre(request.user), 'accion': accion, **datos}]


def _proceso_principal(valor):
    if valor is not None and valor.padre_id:
        raise serializers.ValidationError(f'Elija el proceso principal ({valor.padre.nombre}), no el subproceso.')
    return valor


def _personas(valor, campos_extra=()):
    """Lista de personas: trabajador de Organización y personal o, si es externo, su nombre."""
    from organizacion.models import Trabajador
    if not isinstance(valor or [], list):
        raise serializers.ValidationError('Formato no válido.')
    salida = []
    for e in valor or []:
        if not isinstance(e, dict):
            raise serializers.ValidationError('Formato no válido.')
        extra = {c: (e.get(c) or '').strip() if isinstance(e.get(c), str) else e.get(c) for c in campos_extra}
        if e.get('trabajador'):
            t = Trabajador.objects.filter(pk=e['trabajador'], is_active=True).select_related('puesto').first()
            if not t:
                raise serializers.ValidationError('Trabajador no encontrado.')
            salida.append({'trabajador': t.pk, 'nombre': t.nombre_completo, 'cargo': t.puesto.nombre,
                           'empresa': t.empresa or 'Metrindust', **extra})
        elif (e.get('nombre') or '').strip():
            salida.append({'trabajador': None, 'nombre': e['nombre'].strip(), 'cargo': (e.get('cargo') or '').strip(),
                           'empresa': (e.get('empresa') or '').strip(), **extra})
    return salida


def _de_lista(valor, opciones, nombre):
    valor = valor or []
    otros = [v for v in valor if v not in opciones and not str(v).startswith('Otro:')]
    if otros:
        raise serializers.ValidationError(f'{nombre}: opción no válida ({otros[0]}).')
    return valor


# --------------------------------------------------------------------------------------------- serializers
class AfectadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AfectadoEvento
        fields = ['id', 'trabajador', 'nombre', 'documento', 'edad', 'sexo', 'area', 'puesto', 'empresa', 'antiguedad',
                  'turno', 'tipo_contrato', 'experiencia_puesto', 'horas_trabajadas', 'sctr', 'partes_cuerpo',
                  'tipos_lesion', 'dias_descanso']
        extra_kwargs = {'nombre': {'required': False, 'allow_blank': True}}

    def validate(self, data):
        t = data.get('trabajador')
        if t:
            # Datos del trabajador al momento del evento (se conservan aunque luego cambie de puesto).
            a = t.area_efectiva
            data.setdefault('nombre', t.nombre_completo)
            data['nombre'] = data.get('nombre') or t.nombre_completo
            for campo, valor in (('documento', t.documento), ('area', a.nombre if a else ''),
                                 ('puesto', t.puesto.nombre), ('empresa', t.empresa)):
                if not data.get(campo):
                    data[campo] = valor or ''
        elif not (data.get('nombre') or getattr(self.instance, 'nombre', '')).strip():
            raise serializers.ValidationError({'nombre': ['Indique el trabajador o el nombre de la persona.']})
        _de_lista(data.get('partes_cuerpo'), PARTES_CUERPO, 'Parte del cuerpo')
        _de_lista(data.get('tipos_lesion'), TIPOS_LESION, 'Tipo de lesión')
        return data


class EventoListaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    gravedad_display = serializers.CharField(source='get_gravedad_display', read_only=True)
    unidad_nombre = serializers.CharField(source='unidad.nombre', read_only=True, default=None)
    afectados_nombres = serializers.SerializerMethodField()
    reporte_tardio = serializers.BooleanField(read_only=True)
    pendiente_mtpe = serializers.SerializerMethodField()

    class Meta:
        model = Evento
        fields = ['id', 'codigo', 'tipo', 'tipo_display', 'estado', 'estado_display', 'gravedad', 'gravedad_display',
                  'fecha_hora', 'lugar', 'unidad_nombre', 'afectados_nombres', 'reporte_tardio', 'pendiente_mtpe']

    def get_afectados_nombres(self, obj):
        return [a.nombre for a in obj.afectados.all() if a.is_active]

    def get_pendiente_mtpe(self, obj):
        return obj.requiere_notificacion_mtpe and not obj.notificacion_mtpe and obj.estado != 'anulado'


class EventoSerializer(EventoListaSerializer):
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    grado_display = serializers.CharField(source='get_grado_incapacidad_display', read_only=True)
    afectados = serializers.SerializerMethodField()
    archivos = serializers.SerializerMethodField()
    filas_iperc_info = serializers.SerializerMethodField()
    reportado_por_nombre = serializers.SerializerMethodField()
    constancia_url = serializers.SerializerMethodField()
    acciones = serializers.SerializerMethodField()
    requiere_notificacion_mtpe = serializers.BooleanField(read_only=True)
    dias_perdidos = serializers.IntegerField(read_only=True)
    etapas_abiertas = serializers.SerializerMethodField()

    class Meta:
        model = Evento
        fields = EventoListaSerializer.Meta.fields + [
            'unidad', 'proceso', 'proceso_nombre', 'en_campo', 'cliente', 'actividad', 'descripcion',
            'acciones_inmediatas', 'primeros_auxilios', 'potencialmente_afectados', 'pobladores_afectados',
            'tipos_emergencia', 'tipos_ambiental', 'testigos', 'reportado_por_nombre', 'fecha_reporte',
            'notificacion_mtpe', 'constancia_url', 'requiere_notificacion_mtpe', 'grado_incapacidad', 'grado_display',
            'tipos_accidente', 'fecha_inicio_investigacion', 'equipo_investigador', 'metodo_analisis',
            'actos_subestandar', 'condiciones_subestandar', 'detalle_actos_condiciones', 'factores_trabajo',
            'detalle_factores_trabajo', 'factores_personales', 'detalle_factores_personales', 'que_sucedio', 'porques',
            'causas_inmediatas', 'causas_basicas', 'conclusiones', 'filas_iperc', 'filas_iperc_info',
            'requiere_actualizar_iperc', 'firma_elaborado', 'firma_revisado', 'acciones', 'firma_cierre',
            'fecha_cierre', 'motivo_anulacion', 'historial', 'afectados', 'archivos', 'dias_perdidos',
            'etapas_abiertas']
        # fecha_reporte la fija el sistema al registrar (plazo de 24 h): no se edita.
        read_only_fields = ['codigo', 'estado', 'notificacion_mtpe', 'firma_elaborado', 'firma_revisado',
                            'firma_cierre', 'fecha_cierre', 'motivo_anulacion', 'historial', 'fecha_reporte']

    def get_afectados(self, obj):
        return AfectadoSerializer(obj.afectados.filter(is_active=True), many=True).data if obj.pk else []

    def get_archivos(self, obj):
        return [{'id': a.id, 'descripcion': a.descripcion, 'url': a.archivo.url, 'fecha': a.created_at}
                for a in obj.archivos.filter(is_active=True)] if obj.pk else []

    def get_filas_iperc_info(self, obj):
        return [{'id': f.id, 'codigo': f.codigo, 'peligro': f.peligro, 'clasificacion': f.clasificacion}
                for f in obj.filas_iperc.all()] if obj.pk else []

    def get_reportado_por_nombre(self, obj):
        return _nombre(obj.reportado_por) if obj.reportado_por_id else None

    def get_constancia_url(self, obj):
        return obj.constancia_mtpe.url if obj.constancia_mtpe else None

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas() if obj.pk else ['reporte']

    def get_acciones(self, obj):
        return _acciones_de(obj.hallazgo)

    def validate_proceso(self, valor):
        return _proceso_principal(valor)

    def validate_testigos(self, valor):
        return _personas(valor, ('edad',))

    def validate_equipo_investigador(self, valor):
        valor = _personas(valor, ('rol',))
        for e in valor:
            e['rol'] = e.get('rol') or 'miembro'
        return valor

    def validate_tipos_accidente(self, valor):
        return _de_lista(valor, TIPOS_ACCIDENTE, 'Tipo de accidente')

    def validate_tipos_emergencia(self, valor):
        return _de_lista(valor, TIPOS_EMERGENCIA, 'Tipo de emergencia')

    def validate_tipos_ambiental(self, valor):
        return _de_lista(valor, TIPOS_AMBIENTAL, 'Tipo de accidente ambiental')

    def validate_actos_subestandar(self, valor):
        return _de_lista(valor, ACTOS_SUBESTANDAR, 'Acto subestándar')

    def validate_condiciones_subestandar(self, valor):
        return _de_lista(valor, CONDICIONES_SUBESTANDAR, 'Condición subestándar')

    def validate_factores_trabajo(self, valor):
        return _de_lista(valor, FACTORES_TRABAJO, 'Factor de trabajo')

    def validate_factores_personales(self, valor):
        return _de_lista(valor, FACTORES_PERSONALES, 'Factor personal')

    def validate_porques(self, valor):
        if not isinstance(valor or [], list) or len(valor or []) > 7:
            raise serializers.ValidationError('Hasta 7 porqués.')
        return [str(v).strip() for v in (valor or []) if str(v).strip()]

    def validate_fecha_hora(self, valor):
        if valor > timezone.now():
            raise serializers.ValidationError('La fecha y hora del evento no puede ser futura.')
        return valor


def _acciones_de(hallazgo):
    """Acciones de la solicitud de acción correctiva del hallazgo (para la pantalla y los registros)."""
    if not hallazgo:
        return None
    sac = hallazgo.sac
    return {'hallazgo': hallazgo.codigo, 'hallazgo_id': hallazgo.pk, 'hallazgo_estado': hallazgo.get_estado_display(),
            'sac': sac.codigo if sac else None, 'sac_id': sac.pk if sac else None,
            'sac_estado': sac.estado if sac else None, 'sac_estado_display': sac.get_estado_display() if sac else None,
            'acciones': [{'descripcion': a.descripcion, 'tipo': a.get_tipo_display(),
                          'responsable': _nombre(a.responsable) if a.responsable_id else '',
                          'fecha': a.fecha_propuesta, 'estado': a.get_estado_display(),
                          'fecha_completada': a.fecha_completada}
                         for a in (sac.acciones.filter(is_active=True) if sac else [])]}


class EnfermedadSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    agente_display = serializers.CharField(source='get_agente_display', read_only=True)
    unidad_nombre = serializers.CharField(source='unidad.nombre', read_only=True, default=None)
    veces_en_area = serializers.IntegerField(read_only=True)
    acciones = serializers.SerializerMethodField()
    filas_iperc_info = serializers.SerializerMethodField()

    class Meta:
        model = EnfermedadOcupacional
        fields = ['id', 'codigo', 'estado', 'estado_display', 'fecha', 'nombre', 'trabajadores_afectados', 'unidad',
                  'unidad_nombre', 'agente', 'agente_display', 'agente_detalle', 'causas', 'trabajadores_expuestos',
                  'cancer_profesional', 'filas_iperc', 'filas_iperc_info', 'veces_en_area', 'acciones',
                  'firma_registro', 'motivo_anulacion', 'historial']
        read_only_fields = ['codigo', 'estado', 'firma_registro', 'motivo_anulacion', 'historial']

    def get_acciones(self, obj):
        return _acciones_de(obj.hallazgo)

    def get_filas_iperc_info(self, obj):
        return [{'id': f.id, 'codigo': f.codigo, 'peligro': f.peligro} for f in obj.filas_iperc.all()] if obj.pk else []


class DatosMesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatosMesSST
        fields = ['id', 'anio', 'mes', 'trabajadores', 'dias_laborables', 'horas_hombre', 'propuesto',
                  'trabajadores_dm', 'dias_dm_calendario', 'dias_dm_laborales', 'observaciones']
        read_only_fields = ['propuesto']


class InformeEstadisticasSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformeEstadisticasSST
        fields = ['id', 'anio', 'periodo', 'resultados', 'causas_desviaciones', 'conclusiones', 'firma',
                  'created_at']
        read_only_fields = ['firma']


# -------------------------------------------------------------------------------------------------- base
class _Base:
    permission_classes = [PermisoModular]
    modulo = 'sst'
    pagination_class = None

    def _error(self, mensaje):
        return Response({'detail': mensaje}, status=status.HTTP_400_BAD_REQUEST)

    def _clave(self, request, que):
        password = request.data.get('password') or ''
        if not password:
            return self._error(f'Confirme con su contraseña para firmar {que}.')
        if not request.user.check_password(password):
            return self._error(f'Contraseña incorrecta. No se registró {que}.')
        return None

    def _pdf(self, contenido, nombre):
        from django.http import HttpResponse
        resp = HttpResponse(contenido, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{nombre}.pdf"'
        return resp


def _registrar_acciones(obj, request, tipo_hallazgo, descripcion, proceso, fecha, lugar=''):
    """Registra el hallazgo y su solicitud de acción correctiva (seguimiento y eficacia en Acciones correctivas)."""
    from esynapse_sig.models import Hallazgo, SolicitudAC
    u = request.user
    h = Hallazgo.objects.create(
        tipo=tipo_hallazgo, fuente='accidente', proceso=(proceso.nombre if proceso else 'Seguridad y Salud en el Trabajo'),
        proceso_catalogo=proceso, descripcion=descripcion, requisito='Ley 29783 · ISO 45001:2018 10.2',
        lugar=lugar[:150], fecha_deteccion=fecha, estado='en_tratamiento', created_by=u, updated_by=u)
    sac = SolicitudAC.objects.create(hallazgo=h, fuente='otros', fuente_detalle='Incidente / accidente de trabajo',
                                     normas_aplicables=['iso_45001'], descripcion_nc=descripcion,
                                     requisito_auditado=h.requisito, fecha_registro=timezone.localdate(),
                                     created_by=u, updated_by=u)
    h.sac = sac
    h.save(update_fields=['sac'])
    obj.hallazgo = h
    return h, sac


# ------------------------------------------------------------------------------------------------ eventos
class EventoViewSet(_Base, viewsets.ModelViewSet):
    """Incidentes, accidentes y emergencias: reporte → investigación → revisión → acciones → cierre."""
    queryset = Evento.objects.all().select_related('unidad', 'proceso', 'reportado_por', 'hallazgo', 'hallazgo__sac') \
        .prefetch_related('afectados', 'filas_iperc')

    def get_serializer_class(self):
        return EventoListaSerializer if self.action == 'list' else EventoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list':
            qs = qs.filter(is_active=True)
        for campo in ('tipo', 'estado', 'gravedad'):
            if p.get(campo):
                qs = qs.filter(**{campo: p[campo]})
        if p.get('anio'):
            qs = qs.filter(fecha_hora__year=p['anio'])
        if p.get('unidad'):
            qs = qs.filter(unidad_id=p['unidad'])
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(descripcion__icontains=b) | Q(lugar__icontains=b)
                           | Q(afectados__nombre__icontains=b)).distinct()
        return qs

    def _respuesta(self, e, codigo=status.HTTP_200_OK):
        return Response(EventoSerializer(Evento.objects.get(pk=e.pk)).data, status=codigo)

    def perform_create(self, serializer):
        e = serializer.save(created_by=self.request.user, updated_by=self.request.user,
                            reportado_por=self.request.user, fecha_reporte=timezone.now())
        _hist(e, self.request, 'Reporte', **({'tardio': 'Reportado después de 24 horas'} if e.reporte_tardio else {}))
        e.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        e = self.get_object()
        abiertas = e.etapas_abiertas()
        for campo in request.data.keys():
            etapa = e.etapa_de_campo(campo)
            if etapa and etapa not in abiertas:
                nombre = {'reporte': 'el reporte', 'investigacion': 'la investigación'}[etapa]
                return self._error(f'El evento está {e.get_estado_display().lower()}: {nombre} no se modifica '
                                   f'({Evento._meta.get_field(campo).verbose_name}).')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return self._error('Un evento no se elimina: si se registró por error, se anula con motivo.')

    # --- personas afectadas
    @action(detail=True, methods=['post'])
    def afectado(self, request, pk=None):
        """Agrega o corrige a una persona afectada (en el reporte o la investigación). Body: datos + id opcional."""
        e = self.get_object()
        if e.estado not in ('reportado', 'en_investigacion'):
            return self._error('Las personas afectadas se registran en el reporte o en la investigación.')
        inst = e.afectados.filter(pk=request.data.get('id'), is_active=True).first() if request.data.get('id') else None
        ser = AfectadoSerializer(inst, data=request.data, partial=bool(inst))
        ser.is_valid(raise_exception=True)
        if inst:
            ser.save(updated_by=request.user)
        else:
            if e.afectados.filter(is_active=True, trabajador=ser.validated_data.get('trabajador')).exclude(
                    trabajador__isnull=True).exists():
                return self._error('Ese trabajador ya figura como afectado.')
            ser.save(evento=e, created_by=request.user, updated_by=request.user)
        return self._respuesta(e)
    afectado.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_afectado(self, request, pk=None):
        e = self.get_object()
        if e.estado not in ('reportado', 'en_investigacion'):
            return self._error('Las personas afectadas se registran en el reporte o en la investigación.')
        e.afectados.filter(pk=request.data.get('id')).update(is_active=False)
        return self._respuesta(e)
    quitar_afectado.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def actualizar_descanso(self, request, pk=None):
        """El descanso médico puede prolongarse después de la investigación: se actualiza con historial."""
        e = self.get_object()
        if e.estado in ('cerrado', 'anulado'):
            return self._error('El evento está cerrado.')
        a = e.afectados.filter(pk=request.data.get('id'), is_active=True).first()
        if not a:
            return self._error('Persona afectada no encontrada.')
        try:
            dias = int(request.data.get('dias_descanso'))
        except (TypeError, ValueError):
            return self._error('Indique los días de descanso médico.')
        if dias < 0:
            return self._error('Días no válidos.')
        _hist(e, request, 'Descanso médico', motivo=f'{a.nombre}: {a.dias_descanso or 0} → {dias} días')
        a.dias_descanso = dias
        a.save(update_fields=['dias_descanso'])
        e.save(update_fields=['historial'])
        return self._respuesta(e)
    actualizar_descanso.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def archivo(self, request, pk=None):
        """Multipart: {archivo, descripcion}. Evidencias en cualquier etapa abierta."""
        e = self.get_object()
        if e.estado in ('cerrado', 'anulado'):
            return self._error('El evento está cerrado.')
        if not request.FILES.get('archivo') or not (request.data.get('descripcion') or '').strip():
            return self._error('Adjunte el archivo y describa qué es (foto, croquis, declaración…).')
        ArchivoEvento.objects.create(evento=e, archivo=request.FILES['archivo'],
                                     descripcion=request.data['descripcion'].strip()[:200],
                                     created_by=request.user, updated_by=request.user)
        return self._respuesta(e)
    archivo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def notificar_mtpe(self, request, pk=None):
        """Multipart: {fecha, constancia}. Notificación al Ministerio de Trabajo (accidente mortal o incidente peligroso)."""
        e = self.get_object()
        if e.estado == 'anulado':
            return self._error('El evento está anulado.')
        try:
            fecha = date.fromisoformat(request.data.get('fecha') or '')
        except ValueError:
            return self._error('Indique la fecha de la notificación.')
        e.notificacion_mtpe = fecha
        if request.FILES.get('constancia'):
            e.constancia_mtpe = request.FILES['constancia']
        _hist(e, request, 'Notificación al Ministerio de Trabajo', motivo=str(fecha))
        e.updated_by = request.user
        e.save()
        return self._respuesta(e)
    notificar_mtpe.operacion = 'editar'

    # --- flujo
    @action(detail=True, methods=['post'])
    def iniciar_investigacion(self, request, pk=None):
        e = self.get_object()
        if e.estado != 'reportado':
            return self._error('La investigación ya se inició.')
        if e.tipo == 'accidente' and not e.afectados.filter(is_active=True).exists():
            return self._error('Registre a la persona accidentada antes de iniciar la investigación.')
        equipo = request.data.get('equipo_investigador') or e.equipo_investigador
        try:
            equipo = EventoSerializer().validate_equipo_investigador(equipo)
        except serializers.ValidationError as exc:
            return self._error(str(exc.detail[0]))
        if not equipo:
            return self._error('Conforme el equipo investigador (al menos quien lidera, del Comité SST).')
        if not any(m.get('rol') == 'lider' for m in equipo):
            equipo[0]['rol'] = 'lider'
        fecha = request.data.get('fecha_inicio_investigacion')
        try:
            fecha = date.fromisoformat(fecha) if fecha else timezone.localdate()
        except ValueError:
            return self._error('Fecha de inicio no válida.')
        e.estado, e.equipo_investigador, e.fecha_inicio_investigacion = 'en_investigacion', equipo, fecha
        _hist(e, request, 'Inicio de la investigación')
        e.updated_by = request.user
        e.save()
        return self._respuesta(e)
    iniciar_investigacion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def concluir(self, request, pk=None):
        """El equipo investigador concluye el informe y lo firma (elaborado)."""
        e = self.get_object()
        if e.estado != 'en_investigacion':
            return self._error('El evento no está en investigación.')
        falta = []
        if e.tipo == 'accidente':
            if not e.gravedad:
                falta.append('la gravedad del accidente')
            elif e.gravedad == 'incapacitante' and not e.grado_incapacidad:
                falta.append('el grado del accidente incapacitante')
        if e.metodo_analisis == '5_porques' and (not e.que_sucedio.strip() or not e.porques):
            falta.append('el análisis de los porqués (qué sucedió y al menos un porqué)')
        for campo, nombre in (('causas_inmediatas', 'las causas inmediatas'), ('causas_basicas', 'las causas básicas'),
                              ('conclusiones', 'las conclusiones')):
            if not getattr(e, campo).strip():
                falta.append(nombre)
        if falta:
            return self._error('Para concluir la investigación registre ' + ', '.join(falta) + '.')
        error = self._clave(request, 'el informe de investigación')
        if error:
            return error
        e.estado, e.firma_elaborado = 'en_revision', _firma(request)
        _hist(e, request, 'Investigación concluida')
        e.updated_by = request.user
        e.save()
        return self._respuesta(e)
    concluir.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def devolver(self, request, pk=None):
        e = self.get_object()
        if e.estado != 'en_revision':
            return self._error('Solo se devuelve un informe en revisión.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique qué debe completarse o corregirse.')
        e.estado, e.firma_elaborado = 'en_investigacion', {}
        _hist(e, request, 'Informe devuelto', motivo=motivo)
        e.updated_by = request.user
        e.save()
        return self._respuesta(e)
    devolver.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def aprobar_informe(self, request, pk=None):
        """Revisión del informe con firma; registra el hallazgo y su solicitud de acción correctiva."""
        e = self.get_object()
        if e.estado != 'en_revision':
            return self._error('El informe no está en revisión.')
        error = self._clave(request, 'la revisión del informe')
        if error:
            return error
        grave = e.tipo == 'incidente_peligroso' or (e.tipo == 'accidente' and e.gravedad in ('incapacitante', 'mortal'))
        descripcion = (f'{e.codigo} · {e.get_tipo_display()}'
                       f'{" (" + e.get_gravedad_display().lower() + ")" if e.gravedad else ""}: {e.descripcion[:300]}\n'
                       f'Causas inmediatas: {e.causas_inmediatas[:300]}\nCausas básicas: {e.causas_basicas[:400]}')
        proceso = e.proceso or (e.unidad.proceso if e.unidad_id else None)
        h, sac = _registrar_acciones(e, request, 'nc_mayor' if grave else 'nc_menor', descripcion, proceso,
                                     timezone.localtime(e.fecha_hora).date(), e.lugar)
        e.estado, e.firma_revisado = 'en_acciones', _firma(request)
        _hist(e, request, 'Informe revisado', motivo=f'Hallazgo {h.codigo} · {sac.codigo}')
        e.updated_by = request.user
        e.save()
        return self._respuesta(e)
    aprobar_informe.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """Cierre: acciones implementadas y eficaces (solicitud cerrada), notificación y matriz IPERC al día."""
        e = self.get_object()
        if e.estado != 'en_acciones':
            return self._error('El evento no está en acciones correctivas.')
        sac = e.hallazgo.sac if e.hallazgo_id else None
        if not sac or sac.estado not in SAC_CERRADA:
            return self._error(f'La solicitud de acción correctiva {sac.codigo if sac else ""} debe cerrarse (acciones '
                               'implementadas y eficacia verificada) antes de cerrar el evento.')
        if e.requiere_notificacion_mtpe and not e.notificacion_mtpe:
            return self._error('Registre la notificación al Ministerio de Trabajo.')
        if e.requiere_actualizar_iperc and request.data.get('iperc_actualizado') not in (True, 'true', '1'):
            return self._error('La investigación pidió actualizar la matriz IPERC: confirme que se actualizó.')
        error = self._clave(request, 'el cierre del evento')
        if error:
            return error
        e.estado, e.firma_cierre, e.fecha_cierre = 'cerrado', _firma(request), timezone.now()
        _hist(e, request, 'Cierre')
        e.updated_by = request.user
        e.save()
        return self._respuesta(e)
    cerrar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        e = self.get_object()
        if e.estado not in ('reportado', 'en_investigacion'):
            return self._error('Solo se anula un evento registrado por error, antes de concluir su investigación.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo.')
        e.estado, e.motivo_anulacion = 'anulado', motivo
        _hist(e, request, 'Anulación', motivo=motivo)
        e.updated_by = request.user
        e.save()
        return self._respuesta(e)
    anular.operacion = 'eliminar'

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'tipos': TIPOS_EVENTO, 'estados': ESTADOS_EVENTO, 'gravedades': GRAVEDADES,
                         'grados': GRADOS_INCAPACIDAD, 'partes_cuerpo': PARTES_CUERPO, 'tipos_lesion': TIPOS_LESION,
                         'tipos_accidente': TIPOS_ACCIDENTE, 'tipos_emergencia': TIPOS_EMERGENCIA,
                         'tipos_ambiental': TIPOS_AMBIENTAL, 'actos': ACTOS_SUBESTANDAR,
                         'condiciones': CONDICIONES_SUBESTANDAR, 'factores_trabajo': FACTORES_TRABAJO,
                         'factores_personales': FACTORES_PERSONALES, 'metodos': METODOS_ANALISIS, 'agentes': AGENTES})
    catalogos.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def registro_pdf(self, request, pk=None):
        from .pdf_eventos import generar_registro_pdf
        e = self.get_object()
        if e.tipo == 'emergencia':
            return self._error('Las emergencias se documentan en el informe de investigación.')
        return self._pdf(generar_registro_pdf(e), f'Registro {e.codigo}')
    registro_pdf.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def informe_pdf(self, request, pk=None):
        from .pdf_eventos import generar_informe_pdf
        e = self.get_object()
        return self._pdf(generar_informe_pdf(e), f'Informe {e.codigo}')
    informe_pdf.operacion = 'leer'


# ------------------------------------------------------------------------------------ enfermedades
class EnfermedadViewSet(_Base, viewsets.ModelViewSet):
    queryset = EnfermedadOcupacional.objects.all().select_related('unidad', 'hallazgo', 'hallazgo__sac')
    serializer_class = EnfermedadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list':
            qs = qs.filter(is_active=True)
            if self.request.query_params.get('anio'):
                qs = qs.filter(fecha__year=self.request.query_params['anio'])
        return qs

    def perform_create(self, serializer):
        o = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(o, self.request, 'Registro')
        o.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        if self.get_object().estado != 'registrada':
            return self._error('El registro ya pasó a acciones correctivas: no se modifica.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return self._error('Un registro no se elimina: se anula con motivo.')

    @action(detail=True, methods=['post'])
    def registrar_acciones(self, request, pk=None):
        o = self.get_object()
        if o.estado != 'registrada':
            return self._error('El registro ya tiene sus acciones correctivas.')
        error = self._clave(request, 'el registro de la enfermedad ocupacional')
        if error:
            return error
        descripcion = (f'{o.codigo} · Enfermedad ocupacional: {o.nombre} ({o.trabajadores_afectados} trabajador(es), '
                       f'{o.unidad.nombre if o.unidad_id else "sin área"}). Agente {o.get_agente_display().lower()}'
                       f'{": " + o.agente_detalle if o.agente_detalle else ""}.\nCausas: {o.causas[:500]}')
        proceso = o.unidad.proceso if o.unidad_id else None
        h, sac = _registrar_acciones(o, request, 'nc_mayor', descripcion, proceso, o.fecha)
        o.estado, o.firma_registro = 'en_acciones', _firma(request)
        _hist(o, request, 'Registro firmado', motivo=f'Hallazgo {h.codigo} · {sac.codigo}')
        o.updated_by = request.user
        o.save()
        return Response(EnfermedadSerializer(o).data)
    registrar_acciones.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        o = self.get_object()
        sac = o.hallazgo.sac if o.hallazgo_id else None
        if o.estado != 'en_acciones':
            return self._error('El registro no está en acciones correctivas.')
        if not sac or sac.estado not in SAC_CERRADA:
            return self._error('La solicitud de acción correctiva debe cerrarse antes.')
        o.estado = 'cerrada'
        _hist(o, request, 'Cierre')
        o.save(update_fields=['estado', 'historial'])
        return Response(EnfermedadSerializer(o).data)
    cerrar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        o = self.get_object()
        if o.estado != 'registrada':
            return self._error('Solo se anula un registro antes de pasar a acciones correctivas.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo.')
        o.estado, o.motivo_anulacion = 'anulada', motivo
        _hist(o, request, 'Anulación', motivo=motivo)
        o.save(update_fields=['estado', 'motivo_anulacion', 'historial'])
        return Response(EnfermedadSerializer(o).data)
    anular.operacion = 'eliminar'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf_eventos import generar_enfermedad_pdf
        o = self.get_object()
        return self._pdf(generar_enfermedad_pdf(o), f'Registro {o.codigo}')
    pdf.operacion = 'leer'


# ----------------------------------------------------------------------------------------- estadísticas
def trabajadores_en_mes(anio, mes):
    """Personal propio activo en algún día del mes (Organización y personal)."""
    from organizacion.models import Trabajador
    inicio, fin = date(anio, mes, 1), date(anio, mes, calendar.monthrange(anio, mes)[1])
    return Trabajador.objects.filter(is_active=True, puesto__tipo='propio').filter(
        Q(fecha_ingreso__isnull=True) | Q(fecha_ingreso__lte=fin)).filter(
        Q(fecha_cese__isnull=True) | Q(fecha_cese__gte=inicio)).count()


def estadisticas_anio(anio):
    """Estadística mensual (índices según la R.M. 050-2013-TR)."""
    datos = {d.mes: d for d in DatosMesSST.objects.filter(anio=anio)}
    eventos = list(Evento.objects.filter(is_active=True, fecha_hora__year=anio).exclude(estado='anulado')
                   .select_related('unidad').prefetch_related('afectados'))
    enfermedades = list(EnfermedadOcupacional.objects.filter(is_active=True, fecha__year=anio)
                        .exclude(estado='anulada').select_related('unidad'))
    hoy = timezone.localdate()
    meses = []
    for m in range(1, 13):
        d = datos.get(m)
        if d:
            trab, hh, dias_lab = d.trabajadores, d.horas_hombre, d.dias_laborables
        else:
            trab, dias_lab = trabajadores_en_mes(anio, m), 22
            hh = trab * dias_lab * 8
        ev = [e for e in eventos if timezone.localtime(e.fecha_hora).month == m]

        def grupo(cond):
            sel = [e for e in ev if cond(e)]
            return len(sel), sorted({e.unidad.nombre for e in sel if e.unidad_id})

        mortales, a_mort = grupo(lambda e: e.tipo == 'accidente' and e.gravedad == 'mortal')
        leves, a_lev = grupo(lambda e: e.tipo == 'accidente' and e.gravedad == 'leve')
        incap, a_inc = grupo(lambda e: e.tipo == 'accidente' and e.gravedad == 'incapacitante')
        incid, a_incid = grupo(lambda e: e.tipo == 'incidente')
        pelig, a_pel = grupo(lambda e: e.tipo == 'incidente_peligroso')
        dias = sum(e.dias_perdidos for e in ev if e.tipo == 'accidente' and e.gravedad in ('incapacitante', 'mortal'))
        indice_f = round(incap * 1_000_000 / hh, 2) if hh else None
        indice_g = round(dias * 1_000_000 / hh, 2) if hh else None
        indice_a = round(indice_f * indice_g / 1000, 2) if hh else None
        enf = [o for o in enfermedades if o.fecha.month == m]
        n_enf = len(enf)
        expuestos = sum(o.trabajadores_expuestos or 0 for o in enf)
        meses.append({
            'mes': m, 'nombre': MESES[m - 1], 'futuro': date(anio, m, 1) > hoy, 'propuesto': not d or d.propuesto,
            'datos_id': d.id if d else None, 'trabajadores': trab, 'dias_laborables': dias_lab, 'horas_hombre': hh,
            'mortales': mortales, 'areas_mortales': a_mort, 'leves': leves, 'areas_leves': a_lev,
            'incapacitantes': incap, 'areas_incapacitantes': a_inc, 'dias_perdidos': dias,
            'indice_frecuencia': indice_f, 'indice_gravedad': indice_g, 'indice_accidentabilidad': indice_a,
            'incidentes': incid, 'areas_incidentes': a_incid, 'incidentes_peligrosos': pelig,
            'areas_peligrosos': a_pel, 'emergencias': len([e for e in ev if e.tipo == 'emergencia']),
            'enfermedades': n_enf, 'areas_enfermedades': sorted({o.unidad.nombre for o in enf if o.unidad_id}),
            'expuestos': expuestos, 'tasa_incidencia': round(n_enf * 1_000_000 / expuestos, 2) if expuestos else None,
            'cancer': len([o for o in enf if o.cancer_profesional]),
            'trabajadores_dm': d.trabajadores_dm if d else 0, 'dias_dm_calendario': d.dias_dm_calendario if d else 0,
            'dias_dm_laborales': d.dias_dm_laborales if d else 0,
            'hh_dm': (d.dias_dm_laborales * 8) if d else 0,
        })
    return meses


class EstadisticasViewSet(_Base, viewsets.ViewSet):
    """Estadísticas mensuales de SST, datos del mes (trabajadores y horas-hombre) y análisis firmado."""

    @action(detail=False, methods=['get'])
    def anio(self, request):
        try:
            anio = int(request.query_params.get('anio') or timezone.localdate().year)
        except ValueError:
            return self._error('Año no válido.')
        pendientes_mtpe = [e.codigo for e in Evento.objects.filter(is_active=True).exclude(estado='anulado')
                           if e.requiere_notificacion_mtpe and not e.notificacion_mtpe]
        return Response({'anio': anio, 'meses': estadisticas_anio(anio), 'pendientes_mtpe': pendientes_mtpe,
                         'informes': InformeEstadisticasSerializer(
                             InformeEstadisticasSST.objects.filter(anio=anio, is_active=True), many=True).data})
    anio.operacion = 'leer'

    @action(detail=False, methods=['post'])
    def datos_mes(self, request):
        """Ajusta los datos de un mes (horas extra, ausencias, descansos médicos). Body: anio, mes y campos."""
        try:
            anio, mes = int(request.data.get('anio')), int(request.data.get('mes'))
        except (TypeError, ValueError):
            return self._error('Indique año y mes.')
        if not 1 <= mes <= 12:
            return self._error('Mes no válido.')
        d = DatosMesSST.objects.filter(anio=anio, mes=mes).first()
        base = {'anio': anio, 'mes': mes, 'trabajadores': trabajadores_en_mes(anio, mes), 'dias_laborables': 22}
        base['horas_hombre'] = base['trabajadores'] * 22 * 8
        enviados = {k: v for k, v in request.data.items() if k in DatosMesSerializer.Meta.fields}
        # La propuesta del sistema (trabajadores, horas-hombre) solo completa un mes nuevo: corregir un dato de un mes
        # existente no pisa los valores ajustados.
        datos = {**base, **enviados} if d is None else {**enviados, 'anio': anio, 'mes': mes}
        ser = DatosMesSerializer(d, data=datos, partial=bool(d))
        ser.is_valid(raise_exception=True)
        ser.save(propuesto=False, updated_by=request.user, **({} if d else {'created_by': request.user}))
        return Response(estadisticas_anio(anio)[mes - 1])
    datos_mes.operacion = 'editar'

    @action(detail=False, methods=['post'])
    def informe(self, request):
        """Análisis del periodo con firma del responsable del registro."""
        ser = InformeEstadisticasSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        error = self._clave(request, 'el registro de estadísticas')
        if error:
            return error
        o = ser.save(firma=_firma(request), created_by=request.user, updated_by=request.user)
        return Response(InformeEstadisticasSerializer(o).data, status=status.HTTP_201_CREATED)
    informe.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def registro_pdf(self, request):
        from .pdf_eventos import generar_estadisticas_pdf
        anio = int(request.query_params.get('anio') or timezone.localdate().year)
        inf = InformeEstadisticasSST.objects.filter(pk=request.query_params.get('informe'), anio=anio).first() or \
            InformeEstadisticasSST.objects.filter(anio=anio, is_active=True).first()
        return self._pdf(generar_estadisticas_pdf(anio, estadisticas_anio(anio), inf), f'Estadísticas SST {anio}')
    registro_pdf.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def datos_pdf(self, request):
        from .pdf_eventos import generar_datos_estadisticas_pdf
        anio = int(request.query_params.get('anio') or timezone.localdate().year)
        return self._pdf(generar_datos_estadisticas_pdf(anio, estadisticas_anio(anio)), f'Datos estadísticas SST {anio}')
    datos_pdf.operacion = 'leer'
