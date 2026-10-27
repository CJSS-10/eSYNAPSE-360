"""API de Capacitación e inducción: programa anual, sesiones (lista de asistencia), inducción y situación por
trabajador."""
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular

from .models import (ALCANCES, ESTADOS_SESION, NOTA_APROBATORIA, PARTES_INDUCCION, RESULTADOS_EFICACIA,
                     TEMAS_ASISTENCIA, TIPOS_ACTIVIDAD, TIPOS_CAPACITACION, TIPOS_INDUCCION, ArchivoSesion, Asistente,
                     Induccion, ItemPrograma, ParteInduccion, PlantillaInduccion, ProgramaCapacitacion, Sesion)


def _nombre(u):
    return (u.get_full_name() or u.username) if u else ''


def _firma(request):
    u = request.user
    return {'usuario_id': u.pk, 'nombre': _nombre(u), 'cargo': getattr(u, 'cargo', ''),
            'sigla': getattr(u, 'sigla_cargo', ''), 'fecha': timezone.localtime().isoformat(timespec='seconds'),
            'ip': get_client_ip(request)}


def _hist(obj, request, accion, **datos):
    obj.historial = list(obj.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                  'usuario': _nombre(request.user), 'accion': accion, **datos}]


def _url(f):
    return f.url if f else None


class _Base:
    permission_classes = [PermisoModular]
    modulo = 'capacitacion'
    pagination_class = None

    def _error(self, mensaje, **extra):
        return Response({'detail': mensaje, **extra}, status=status.HTTP_400_BAD_REQUEST)

    def _clave(self, request, que):
        password = request.data.get('password') or ''
        if not password:
            return self._error(f'Confirme con su contraseña para firmar {que}.')
        if not request.user.check_password(password):
            return self._error(f'Contraseña incorrecta. No se registró {que}.')
        return None

    def _pdf(self, contenido, nombre):
        resp = HttpResponse(contenido, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{nombre}.pdf"'
        return resp


def _decimal(v):
    try:
        return Decimal(str(v)) if v not in (None, '') else None
    except InvalidOperation:
        return None


# =================================================================================== programa anual
class ItemSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    alcance_display = serializers.CharField(source='get_alcance_display', read_only=True)
    estado = serializers.CharField(read_only=True)
    fecha_vigente = serializers.DateField(read_only=True)
    dirigido = serializers.SerializerMethodField()
    sesiones = serializers.SerializerMethodField()

    class Meta:
        model = ItemPrograma
        fields = ['id', 'orden', 'tema', 'tipo', 'tipo_display', 'responsable', 'responsable_trabajador', 'externo',
                  'alcance', 'alcance_display', 'areas', 'puestos', 'dirigido_texto', 'dirigido', 'fecha_programada',
                  'fecha_vigente', 'horas', 'fecha_realizada', 'reprogramaciones', 'cancelado', 'motivo_cancelacion',
                  'vb', 'origen', 'estado', 'sesiones']
        read_only_fields = ['fecha_realizada', 'reprogramaciones', 'cancelado', 'motivo_cancelacion', 'vb', 'origen']

    def get_dirigido(self, obj):
        if obj.dirigido_texto:
            return obj.dirigido_texto
        if obj.alcance == 'areas':
            return ', '.join(a.nombre for a in obj.areas.all()) or '—'
        if obj.alcance == 'puestos':
            return ', '.join(p.nombre for p in obj.puestos.all()) or '—'
        return obj.get_alcance_display()

    def get_sesiones(self, obj):
        return [{'id': s.pk, 'codigo': s.codigo, 'fecha': s.fecha, 'estado': s.estado}
                for s in obj.sesiones.filter(is_active=True)]

    def validate(self, data):
        alcance = data.get('alcance', getattr(self.instance, 'alcance', 'todos'))
        if alcance == 'otros' and not (data.get('dirigido_texto') or getattr(self.instance, 'dirigido_texto', '')):
            raise serializers.ValidationError({'dirigido_texto': ['Describa a quién está dirigida.']})
        return data


def _anio(request):
    """Año de la consulta; uno no numérico se trata como el actual (no da error del servidor)."""
    v = str(request.query_params.get('anio') or '')
    return int(v) if v.isdigit() else timezone.localdate().year


def _indicadores(p):
    items = [i for i in p.items.filter(is_active=True) if not i.cancelado]
    hoy = timezone.localdate()
    realizadas = [i for i in items if i.fecha_realizada]
    a_la_fecha = [i for i in items if i.fecha_vigente <= hoy]  # reprogramadas: cuenta la fecha vigente
    return {'programadas': len(items), 'realizadas': len(realizadas),
            'avance': round(100 * len(realizadas) / len(items)) if items else None,
            'programadas_a_la_fecha': len(a_la_fecha),
            'realizadas_a_la_fecha': len([i for i in a_la_fecha if i.fecha_realizada]),
            'avance_a_la_fecha': round(100 * len([i for i in a_la_fecha if i.fecha_realizada]) / len(a_la_fecha))
            if a_la_fecha else None,
            'atrasadas': len([i for i in items if i.estado in ('atrasado', 'reprogramado') and i.fecha_vigente < hoy]),
            'sst_realizadas': len([i for i in realizadas if i.tipo == 'sst']),
            'horas_programadas': float(sum(i.horas for i in items)),
            'horas_realizadas': float(sum(i.horas for i in realizadas))}


class ProgramaSerializer(serializers.ModelSerializer):
    estado_aprobacion = serializers.CharField(read_only=True)
    items = serializers.SerializerMethodField()
    indicadores = serializers.SerializerMethodField()
    archivo_aprobacion_url = serializers.SerializerMethodField()

    class Meta:
        model = ProgramaCapacitacion
        fields = ['id', 'anio', 'historico', 'elaborado', 'aprobacion', 'aprobado_en', 'modificado_en',
                  'estado_aprobacion', 'archivo_aprobacion_url', 'aprobaciones_anteriores', 'items', 'indicadores',
                  'historial']
        read_only_fields = ['historico', 'elaborado', 'aprobacion', 'aprobado_en', 'modificado_en',
                            'aprobaciones_anteriores', 'historial']

    def get_items(self, obj):
        return ItemSerializer(obj.items.filter(is_active=True).prefetch_related('areas', 'puestos', 'sesiones'),
                              many=True).data

    def get_indicadores(self, obj):
        return _indicadores(obj)

    def get_archivo_aprobacion_url(self, obj):
        return _url(obj.archivo_aprobacion)


class ProgramaViewSet(_Base, viewsets.ModelViewSet):
    queryset = ProgramaCapacitacion.objects.all()
    serializer_class = ProgramaSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def _respuesta(self, p, codigo=status.HTTP_200_OK):
        return Response(ProgramaSerializer(ProgramaCapacitacion.objects.get(pk=p.pk)).data, status=codigo)

    def create(self, request, *args, **kwargs):
        try:
            anio = int(request.data.get('anio'))
        except (TypeError, ValueError):
            return self._error('Indique el año del programa.')
        if ProgramaCapacitacion.objects.filter(anio=anio).exists():
            return self._error(f'El programa {anio} ya existe.')
        p = ProgramaCapacitacion.objects.create(anio=anio, elaborado=_firma(request), created_by=request.user,
                                                updated_by=request.user)
        _hist(p, request, 'Creación')
        p.save(update_fields=['historial'])
        return self._respuesta(p, status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def anio(self, request):
        a = _anio(request)
        p = ProgramaCapacitacion.objects.filter(anio=a).first()
        return Response(ProgramaSerializer(p).data if p else None)
    anio.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'tipos': TIPOS_CAPACITACION, 'alcances': ALCANCES, 'tipos_actividad': TIPOS_ACTIVIDAD,
                         'temas': TEMAS_ASISTENCIA, 'estados_sesion': ESTADOS_SESION,
                         'resultados_eficacia': RESULTADOS_EFICACIA, 'partes': PARTES_INDUCCION,
                         'tipos_induccion': TIPOS_INDUCCION, 'nota_aprobatoria': float(NOTA_APROBATORIA),
                         'anios': list(ProgramaCapacitacion.objects.values_list('anio', flat=True))})
    catalogos.operacion = 'leer'

    def _editable(self, p):
        if p.historico:
            return self._error('El programa es histórico: solo consulta.')
        return None

    def _tocar(self, p, request, accion, **datos):
        p.modificado_en = timezone.now()
        _hist(p, request, accion, **datos)
        p.updated_by = request.user
        p.save(update_fields=['modificado_en', 'historial', 'updated_by', 'updated_at'])

    @action(detail=True, methods=['post'])
    def item(self, request, pk=None):
        """Agrega o corrige una capacitación. Body: campos del ítem (+ id para corregir)."""
        p = self.get_object()
        error = self._editable(p)
        if error:
            return error
        i = p.items.filter(pk=request.data.get('id'), is_active=True).first() if request.data.get('id') else None
        if request.data.get('id') and not i:
            return self._error('Capacitación no encontrada en el programa.')
        if i and i.fecha_realizada:
            return self._error('La capacitación ya se realizó: no se modifica.')
        datos = {k: v for k, v in request.data.items() if k not in ('id', 'programa')}
        if not i and 'orden' not in datos:
            datos['orden'] = p.items.count() + 1
        ser = ItemSerializer(i, data=datos, partial=bool(i))
        ser.is_valid(raise_exception=True)
        fp = ser.validated_data.get('fecha_programada')
        if fp and fp.year != p.anio:
            return self._error(f'La fecha programada debe estar en {p.anio}.')
        if i:
            i = ser.save(updated_by=request.user)
        else:
            i = ser.save(programa=p, created_by=request.user, updated_by=request.user)
        self._tocar(p, request, 'Capacitación corregida' if request.data.get('id') else 'Capacitación agregada',
                    capacitacion=i.tema[:100])
        return self._respuesta(p)
    item.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def reprogramar(self, request, pk=None):
        """Reprograma la fecha de una capacitación (RP). Body: {id, fecha, motivo}"""
        p = self.get_object()
        error = self._editable(p)
        if error:
            return error
        i = p.items.filter(pk=request.data.get('id'), is_active=True).first()
        if not i:
            return self._error('Capacitación no encontrada.')
        if i.fecha_realizada or i.cancelado:
            return self._error('Solo se reprograma una capacitación pendiente.')
        f = parse_date(str(request.data.get('fecha') or '')[:10])
        motivo = (request.data.get('motivo') or '').strip()
        if not f or not motivo:
            return self._error('Indique la nueva fecha y el motivo.')
        if f.year != p.anio:
            return self._error(f'La nueva fecha debe estar en {p.anio}; si pasa al año siguiente, cancélela aquí y '
                               'prográmela en el nuevo programa.')
        i.reprogramaciones = list(i.reprogramaciones or []) + [{
            'fecha': timezone.localtime().isoformat(timespec='minutes'), 'usuario': _nombre(request.user),
            'de': i.fecha_vigente.isoformat(), 'a': f.isoformat(), 'motivo': motivo}]
        i.updated_by = request.user
        i.save(update_fields=['reprogramaciones', 'updated_by', 'updated_at'])
        _hist(p, request, 'Reprogramación', capacitacion=i.tema[:100], fecha=f.isoformat(), motivo=motivo)
        p.save(update_fields=['historial'])
        return self._respuesta(p)
    reprogramar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancela una capacitación programada (queda en el programa como cancelada). Body: {id, motivo}"""
        p = self.get_object()
        error = self._editable(p)
        if error:
            return error
        i = p.items.filter(pk=request.data.get('id'), is_active=True).first()
        if not i or i.fecha_realizada:
            return self._error('Solo se cancela una capacitación pendiente.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la cancelación.')
        i.cancelado, i.motivo_cancelacion, i.updated_by = True, motivo, request.user
        i.save(update_fields=['cancelado', 'motivo_cancelacion', 'updated_by', 'updated_at'])
        self._tocar(p, request, 'Cancelación', capacitacion=i.tema[:100], motivo=motivo)
        return self._respuesta(p)
    cancelar.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def firmantes(self, request):
        from sst.comite_firmas import titulares_para_firmar
        c, titulares = titulares_para_firmar()
        return Response({'comite': c.periodo if c else None, 'titulares': titulares,
                         'quorum': len(titulares)})
    firmantes.operacion = 'leer'

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        """Aprobación del programa por el Comité de SST (firmas en pantalla o acta en papel)."""
        from sst.comite_firmas import firmas_del_comite
        p = self.get_object()
        error = self._editable(p)
        if error:
            return error
        if not p.items.filter(is_active=True).exists():
            return self._error('Registre al menos una capacitación.')
        fecha = parse_date(str(request.data.get('fecha') or '')[:10]) or timezone.localdate()
        if p.modificado_en and fecha < timezone.localtime(p.modificado_en).date():
            return self._error('La fecha de aprobación es anterior al último cambio del programa: el Comité debe '
                               'aprobar la versión vigente.')
        datos, error = firmas_del_comite(request, fecha)
        if error:
            return error
        if p.aprobacion:
            p.aprobaciones_anteriores = list(p.aprobaciones_anteriores or []) + [p.aprobacion]
        p.aprobacion = {'fecha': fecha.isoformat(), 'firmas': datos['firmas'], 'registro': _firma(request),
                        'reunion': datos['reunion'].codigo if datos['reunion'] else None,
                        'observaciones': (request.data.get('observaciones') or '').strip()}
        if datos['papel']:
            p.archivo_aprobacion = request.FILES['archivo']
        p.aprobado_en = timezone.now()
        _hist(p, request, 'Aprobación del Comité de SST', fecha=fecha.isoformat())
        p.updated_by = request.user
        p.save()
        return self._respuesta(p)
    aprobar.operacion = 'aprobar'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf import generar_programa_pdf
        p = self.get_object()
        return self._pdf(generar_programa_pdf(p), f'Programa anual de capacitación {p.anio}')
    pdf.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Alertas del módulo: avance del programa, atrasadas, sesiones abiertas, eficacias e inducciones."""
        from organizacion.models import Trabajador
        anio = _anio(request)
        p = ProgramaCapacitacion.objects.filter(anio=anio).first()
        hoy = timezone.localdate()
        atrasadas = [{'id': i.pk, 'tema': i.tema, 'fecha': i.fecha_vigente}
                     for i in (p.items.filter(is_active=True, cancelado=False, fecha_realizada__isnull=True) if p else [])
                     if i.fecha_vigente < hoy]
        cerradas = Sesion.objects.filter(is_active=True, estado='cerrada')
        eficacia = [{'id': s.pk, 'codigo': s.codigo, 'tema': s.tema_tratado[:80], 'vence': s.eficacia_vence,
                     'estado': s.estado_eficacia} for s in cerradas if s.estado_eficacia in ('vencida', 'por_vencer')]
        sin_induccion = []
        for t in Trabajador.objects.filter(is_active=True, estado='activo').select_related('puesto'):
            ind = t.inducciones.filter(is_active=True).first()
            if not ind or ind.estado != 'completa':
                sin_induccion.append({'id': t.pk, 'nombre': t.nombre_completo,
                                      'estado': ind.estado if ind else 'sin_induccion'})
        return Response({'anio': anio, 'programa': p.pk if p else None,
                         'estado_aprobacion': p.estado_aprobacion if p else None,
                         'indicadores': _indicadores(p) if p else None, 'atrasadas': atrasadas,
                         'sesiones_abiertas': Sesion.objects.filter(is_active=True, estado='en_registro').count(),
                         'eficacia': eficacia, 'sin_induccion': sin_induccion})
    resumen.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def situacion(self, request):
        """Por trabajador: inducción, capacitaciones que le corresponden en el año, asistidas y horas."""
        from organizacion.models import Trabajador
        anio = _anio(request)
        p = ProgramaCapacitacion.objects.filter(anio=anio).first()
        items = list(p.items.filter(is_active=True, cancelado=False).prefetch_related('areas', 'puestos')) if p else []
        filtro = request.query_params.get('trabajador')
        qs = Trabajador.objects.filter(is_active=True, estado='activo').select_related('puesto', 'area')
        if filtro:
            qs = qs.filter(pk=filtro)
        filas = []
        for t in qs:
            asistencias = Asistente.objects.filter(trabajador=t, is_active=True, sesion__is_active=True,
                                                   sesion__estado='cerrada', sesion__fecha__year=anio) \
                .select_related('sesion__item')
            asistidos = {a.sesion.item_id for a in asistencias if a.sesion.item_id}
            aplicables = [i for i in items if i.aplica_a(t)]
            faltan = [i for i in aplicables if i.fecha_realizada and i.pk not in asistidos]
            ind = t.inducciones.filter(is_active=True).first()
            fila = {'trabajador': t.pk, 'nombre': t.nombre_completo, 'puesto': t.puesto.nombre,
                    'area': t.area_efectiva.nombre if t.area_efectiva else '',
                    'induccion': ind.estado if ind else 'sin_induccion', 'induccion_id': ind.pk if ind else None,
                    'aplicables': len(aplicables), 'realizadas': len([i for i in aplicables if i.fecha_realizada]),
                    'asistidas': len([i for i in aplicables if i.pk in asistidos]), 'no_asistio': len(faltan),
                    'horas': float(sum(a.sesion.duracion_horas for a in asistencias))}
            if filtro:
                fila['detalle'] = [{'id': i.pk, 'tema': i.tema, 'tipo': i.get_tipo_display(), 'fecha': i.fecha_vigente,
                                    'estado': i.estado, 'asistio': i.pk in asistidos} for i in aplicables]
                fila['sesiones'] = [{'id': a.sesion_id, 'codigo': a.sesion.codigo, 'fecha': a.sesion.fecha,
                                     'tema': a.sesion.tema_tratado[:100], 'horas': float(a.sesion.duracion_horas),
                                     'nota': float(a.nota) if a.nota is not None else None,
                                     'certificado': a.certificado} for a in asistencias]
            filas.append(fila)
        return Response(filas)
    situacion.operacion = 'leer'


# ======================================================================= sesiones (lista de asistencia)
class AsistenteSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='trabajador.nombre_completo', read_only=True)
    documento = serializers.CharField(source='trabajador.documento', read_only=True)
    cargo = serializers.CharField(source='trabajador.puesto.nombre', read_only=True)
    certificado = serializers.CharField(read_only=True)
    constancia_url = serializers.SerializerMethodField()
    forma_firma = serializers.SerializerMethodField()

    class Meta:
        model = Asistente
        fields = ['id', 'trabajador', 'nombre', 'documento', 'cargo', 'firma', 'nota', 'certificado',
                  'constancia_url', 'forma_firma']

    def get_constancia_url(self, obj):
        return _url(obj.constancia)

    def get_forma_firma(self, obj):
        from sst.epp_api import _estado_pin
        return _estado_pin(obj.trabajador)


class SesionSerializer(serializers.ModelSerializer):
    tipo_actividad_display = serializers.CharField(source='get_tipo_actividad_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    item_tema = serializers.CharField(source='item.tema', read_only=True, default=None)
    item_tipo = serializers.CharField(source='item.tipo', read_only=True, default=None)
    asistentes = serializers.SerializerMethodField()
    archivos = serializers.SerializerMethodField()
    lista_papel_url = serializers.SerializerMethodField()
    eficacia_vence = serializers.DateField(read_only=True)
    estado_eficacia = serializers.CharField(read_only=True)
    etapas_abiertas = serializers.SerializerMethodField()

    class Meta:
        model = Sesion
        fields = ['id', 'codigo', 'item', 'item_tema', 'item_tipo', 'tipo_actividad', 'tipo_actividad_display',
                  'temas', 'otros_temas', 'tema_tratado', 'capacitador', 'capacitador_trabajador', 'externo', 'entidad',
                  'fecha', 'hora_desde', 'hora_hasta', 'duracion_horas', 'material_entregado', 'con_evaluacion',
                  'observaciones', 'estado', 'estado_display', 'firma_registro', 'lista_papel_url', 'eficacia',
                  'eficacia_vence', 'estado_eficacia', 'asistentes', 'archivos', 'motivo_anulacion', 'historial',
                  'etapas_abiertas']
        read_only_fields = ['codigo', 'estado', 'firma_registro', 'eficacia', 'motivo_anulacion', 'historial']

    def get_asistentes(self, obj):
        return AsistenteSerializer(obj.asistentes.filter(is_active=True).select_related('trabajador__puesto',
                                                                                       'trabajador__usuario'),
                                   many=True).data

    def get_archivos(self, obj):
        return [{'id': a.pk, 'tipo': a.get_tipo_display(), 'descripcion': a.descripcion, 'url': _url(a.archivo)}
                for a in obj.archivos.filter(is_active=True)]

    def get_lista_papel_url(self, obj):
        return _url(obj.lista_papel)

    def get_etapas_abiertas(self, obj):
        return ['registro'] if obj.estado == 'en_registro' else (['eficacia'] if obj.estado == 'cerrada' else [])

    def validate_temas(self, v):
        validos = dict(TEMAS_ASISTENCIA)
        return [t for t in v or [] if t in validos]

    def validate(self, data):
        item = data.get('item')
        if item and (item.cancelado or not item.is_active):
            raise serializers.ValidationError({'item': ['La capacitación está cancelada.']})
        if item and item.programa.historico:
            raise serializers.ValidationError({'item': ['El programa es histórico.']})
        desde = data.get('hora_desde', getattr(self.instance, 'hora_desde', None))
        hasta = data.get('hora_hasta', getattr(self.instance, 'hora_hasta', None))
        if desde and hasta and hasta <= desde:
            raise serializers.ValidationError({'hora_hasta': ['La hora de término debe ser posterior a la de inicio.']})
        return data


class SesionViewSet(_Base, viewsets.ModelViewSet):
    queryset = Sesion.objects.all().select_related('item')
    serializer_class = SesionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list' and p.get('anulados') != '1':
            qs = qs.filter(is_active=True)
        if p.get('anio'):
            qs = qs.filter(fecha__year=p['anio'])
        if p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        if p.get('item'):
            qs = qs.filter(item_id=p['item'])
        if p.get('tipo'):
            qs = qs.filter(tipo_actividad=p['tipo'])
        if p.get('buscar'):
            from django.db.models import Q
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(tema_tratado__icontains=b) | Q(capacitador__icontains=b))
        return qs

    def _respuesta(self, s, codigo=status.HTTP_200_OK):
        return Response(SesionSerializer(Sesion.objects.get(pk=s.pk)).data, status=codigo)

    def perform_create(self, serializer):
        s = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(s, self.request, 'Registro')
        s.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        s = self.get_object()
        if s.estado != 'en_registro':
            campos = [k for k in request.data if k in Sesion.CAMPOS_REGISTRO]
            if campos:
                return self._error(f'La etapa de registro está cerrada: «{campos[0]}» ya no se modifica.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return self._error('Una sesión no se elimina: si se registró por error, anúlela con motivo.')

    def _abierta(self, s):
        if s.estado != 'en_registro':
            return self._error('La sesión ya está cerrada: la lista de asistencia no se modifica.')
        return None

    @action(detail=True, methods=['post'])
    def asistentes(self, request, pk=None):
        """Agrega asistentes. Body: {trabajadores: [ids]}"""
        from organizacion.models import Trabajador
        s = self.get_object()
        error = self._abierta(s)
        if error:
            return error
        ids = request.data.get('trabajadores') or []
        for t in Trabajador.objects.filter(pk__in=ids, is_active=True):
            if not s.asistentes.filter(trabajador=t, is_active=True).exists():
                Asistente.objects.create(sesion=s, trabajador=t, created_by=request.user, updated_by=request.user)
        return self._respuesta(s)
    asistentes.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_asistente(self, request, pk=None):
        s = self.get_object()
        error = self._abierta(s)
        if error:
            return error
        a = s.asistentes.filter(pk=request.data.get('id'), is_active=True).first()
        if not a:
            return self._error('Asistente no encontrado.')
        a.is_active = False
        a.save(update_fields=['is_active'])
        return self._respuesta(s)
    quitar_asistente.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def firmar_asistente(self, request, pk=None):
        """El asistente firma: con la contraseña de su usuario o con su PIN.
        Body: {id, clave_trabajador | pin | pin_nuevo + pin_confirmacion}"""
        from sst.epp_api import firma_persona
        s = self.get_object()
        error = self._abierta(s)
        if error:
            return error
        a = s.asistentes.filter(pk=request.data.get('id'), is_active=True).select_related('trabajador').first()
        if not a:
            return self._error('Asistente no encontrado.')
        if a.firma.get('metodo') in ('usuario', 'pin'):
            return self._error(f'{a.trabajador.nombre_completo} ya firmó.')
        f, error = firma_persona(request, a.trabajador)
        if error:
            return error
        a.firma = f
        a.save(update_fields=['firma', 'updated_at'])
        return self._respuesta(s)
    firmar_asistente.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def nota(self, request, pk=None):
        """Body: {id, nota} (0 a 20). Las notas se registran hasta el cierre de la sesión."""
        s = self.get_object()
        error = self._abierta(s)
        if error:
            return error
        a = s.asistentes.filter(pk=request.data.get('id'), is_active=True).first()
        n = _decimal(request.data.get('nota'))
        if not a or n is None or not (0 <= n <= 20):
            return self._error('Indique una nota de 0 a 20.')
        a.nota = n
        a.save(update_fields=['nota', 'updated_at'])
        return self._respuesta(s)
    nota.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def lista_papel(self, request, pk=None):
        """Lista de asistencia firmada en papel (escaneada). Multipart: {archivo}"""
        s = self.get_object()
        error = self._abierta(s)
        if error:
            return error
        if not request.FILES.get('archivo'):
            return self._error('Adjunte la lista firmada.')
        s.lista_papel = request.FILES['archivo']
        s.updated_by = request.user
        s.save()
        for a in s.asistentes.filter(is_active=True):
            if not a.firma:
                a.firma = {'metodo': 'papel', 'fecha': timezone.localtime().isoformat(timespec='seconds')}
                a.save(update_fields=['firma'])
        return self._respuesta(s)
    lista_papel.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def archivo(self, request, pk=None):
        """Material, evaluación o constancia. Multipart: {tipo, descripcion, archivo, asistente?}"""
        s = self.get_object()
        if s.estado == 'anulada':
            return self._error('La lista de asistencia está anulada.')
        if not request.FILES.get('archivo'):
            return self._error('Adjunte el archivo.')
        tipos = dict(ArchivoSesion._meta.get_field('tipo').choices)
        if not request.data.get('asistente') and (request.data.get('tipo') or 'material') not in tipos:
            return self._error('Tipo de archivo no válido.')
        if request.data.get('asistente'):
            a = s.asistentes.filter(pk=request.data['asistente'], is_active=True).first()
            if not a:
                return self._error('Asistente no encontrado.')
            a.constancia = request.FILES['archivo']
            a.save(update_fields=['constancia', 'updated_at'])
        else:
            ArchivoSesion.objects.create(sesion=s, tipo=request.data.get('tipo') or 'material',
                                         descripcion=(request.data.get('descripcion') or '').strip(),
                                         archivo=request.FILES['archivo'], created_by=request.user,
                                         updated_by=request.user)
        return self._respuesta(s)
    archivo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """Cierra la lista de asistencia: el responsable del registro firma con su contraseña. Body: {password}"""
        s = self.get_object()
        error = self._abierta(s)
        if error:
            return error
        asist = list(s.asistentes.filter(is_active=True).select_related('trabajador'))
        if not asist:
            return self._error('Registre a los asistentes.')
        sin_firma = [a.trabajador.nombre_completo for a in asist if not a.firma]
        if sin_firma:
            return self._error(f'Falta la firma de {", ".join(sin_firma[:3])}'
                               f'{" y otros" if len(sin_firma) > 3 else ""} (o adjunte la lista firmada en papel).')
        if s.con_evaluacion:
            sin_nota = [a.trabajador.nombre_completo for a in asist if a.nota is None]
            if sin_nota:
                return self._error(f'Falta la nota de {", ".join(sin_nota[:3])}.')
        if not s.duracion_horas:
            return self._error('Indique la duración.')
        if s.fecha > timezone.localdate():
            return self._error('La sesión tiene fecha futura: se cierra después de realizarse.')
        error = self._clave(request, 'la lista de asistencia')
        if error:
            return error
        s.estado, s.firma_registro = 'cerrada', _firma(request)
        _hist(s, request, 'Cierre de la lista de asistencia', asistentes=len(asist))
        s.updated_by = request.user
        s.save()
        if s.item_id and not s.item.fecha_realizada:
            i = s.item
            i.fecha_realizada = s.fecha
            i.vb = getattr(request.user, 'sigla_cargo', '') or _nombre(request.user)
            i.save(update_fields=['fecha_realizada', 'vb', 'updated_at'])
        return self._respuesta(s)
    cerrar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def eficacia(self, request, pk=None):
        """Evaluación de la eficacia (dentro de los 6 meses). Body: {resultado, comentario, password}"""
        s = self.get_object()
        if s.estado != 'cerrada':
            return self._error('La eficacia se evalúa sobre una sesión cerrada.')
        if s.eficacia.get('resultado'):
            return self._error('La eficacia ya fue evaluada.')
        resultado = request.data.get('resultado')
        comentario = (request.data.get('comentario') or '').strip()
        if resultado not in dict(RESULTADOS_EFICACIA) or not comentario:
            return self._error('Indique el resultado y cómo se evaluó (evidencia).')
        error = self._clave(request, 'la evaluación de la eficacia')
        if error:
            return error
        s.eficacia = {'resultado': resultado, 'comentario': comentario, 'fecha': timezone.localdate().isoformat(),
                      'firma': _firma(request)}
        _hist(s, request, 'Evaluación de la eficacia', resultado=resultado)
        s.save()
        return self._respuesta(s)
    eficacia.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        s = self.get_object()
        if s.estado != 'en_registro':
            return self._error('Solo se anula una sesión en registro.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo.')
        s.estado, s.motivo_anulacion = 'anulada', motivo
        _hist(s, request, 'Anulación', motivo=motivo)
        s.save()
        return self._respuesta(s)
    anular.operacion = 'eliminar'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf import generar_lista_asistencia_pdf
        s = self.get_object()
        return self._pdf(generar_lista_asistencia_pdf(s), f'Lista de asistencia {s.codigo}')
    pdf.operacion = 'leer'


# ========================================================================================= inducción
class ParteSerializer(serializers.ModelSerializer):
    parte_display = serializers.CharField(source='get_parte_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    nota = serializers.DecimalField(max_digits=4, decimal_places=1, read_only=True)

    class Meta:
        model = ParteInduccion
        fields = ['id', 'parte', 'parte_display', 'intento', 'responsable', 'fecha', 'hora_inicio', 'hora_fin', 'temas',
                  'documentos', 'preguntas', 'evaluacion_url', 'nota_directa', 'nota', 'evaluador', 'fecha_evaluacion',
                  'observaciones', 'estado', 'estado_display', 'firma_responsable', 'firma_colaborador']


class InduccionSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='trabajador.nombre_completo', read_only=True)
    puesto = serializers.CharField(source='trabajador.puesto.nombre', read_only=True)
    area = serializers.SerializerMethodField()
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado = serializers.CharField(read_only=True)
    partes = serializers.SerializerMethodField()
    forma_firma = serializers.SerializerMethodField()

    class Meta:
        model = Induccion
        fields = ['id', 'codigo', 'trabajador', 'nombre', 'puesto', 'area', 'tipo', 'tipo_display', 'fecha_inicio',
                  'motivo', 'estado', 'partes', 'forma_firma', 'historial', 'is_active', 'motivo_anulacion']
        read_only_fields = ['historial', 'is_active', 'motivo_anulacion']

    def get_area(self, obj):
        a = obj.trabajador.area_efectiva
        return a.nombre if a else ''

    def get_partes(self, obj):
        return ParteSerializer(obj.partes.filter(is_active=True), many=True).data

    def get_forma_firma(self, obj):
        from sst.epp_api import _estado_pin
        return _estado_pin(obj.trabajador)


def _fusionar_parte(p, d):
    """Toma del cliente solo lo que se registra en la inducción (temas incluidos, documentos entregados,
    calificaciones); el texto y los puntos son los de la copia guardada, para que la nota no se pueda alterar.
    Devuelve un mensaje de error o None."""
    reglas = (('temas', 'incluido', bool), ('documentos', 'entregado', bool), ('preguntas', 'calificacion', None))
    for campo, marca, tipo in reglas:
        if campo not in d:
            continue
        nuevos, actuales = d.get(campo), list(getattr(p, campo) or [])
        if not isinstance(nuevos, list) or len(nuevos) != len(actuales) or \
                any(not isinstance(x, dict) for x in nuevos):
            return f'El contenido de {campo} no coincide con el de la inducción: recargue la página.'
        resultado = []
        for actual, nuevo in zip(actuales, nuevos):
            fila = dict(actual)
            if tipo is bool:
                fila[marca] = bool(nuevo.get(marca))
            else:
                c = nuevo.get('calificacion')
                if c in (None, ''):
                    fila['calificacion'] = None
                else:
                    v = _decimal(c)
                    tope = _decimal(actual.get('puntos') or 0) or 0
                    if v is None or v < 0 or v > tope:
                        return f'La calificación de «{str(actual.get("pregunta", ""))[:60]}» va de 0 a {actual.get("puntos")}.'
                    fila['calificacion'] = float(v)
                # Preguntas pendientes de definir en el formato: el evaluador escribe la pregunta real.
                if 'definir' in str(actual.get('pregunta', '')).lower() and str(nuevo.get('pregunta') or '').strip():
                    fila['pregunta'] = str(nuevo['pregunta']).strip()[:500]
            resultado.append(fila)
        setattr(p, campo, resultado)
    return None


def _desde_plantilla(parte):
    pl = PlantillaInduccion.objects.filter(parte=parte).first()
    if not pl:
        return {}
    return {'temas': [{**t, 'incluido': False} for t in pl.temas],
            'documentos': [{**d, 'entregado': False} for d in _resolver_documentos(pl.documentos)],
            'preguntas': [{**q, 'calificacion': None} for q in pl.preguntas],
            'evaluacion_url': pl.evaluacion_url}


class InduccionViewSet(_Base, viewsets.ModelViewSet):
    queryset = Induccion.objects.all().select_related('trabajador__puesto', 'trabajador__area')
    serializer_class = InduccionSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list' and p.get('anuladas') != '1':
            qs = qs.filter(is_active=True)
        if p.get('trabajador'):
            qs = qs.filter(trabajador_id=p['trabajador'])
        return qs

    def _respuesta(self, i, codigo=status.HTTP_200_OK):
        return Response(InduccionSerializer(Induccion.objects.get(pk=i.pk)).data, status=codigo)

    def create(self, request, *args, **kwargs):
        from organizacion.models import Trabajador
        t = Trabajador.objects.filter(pk=request.data.get('trabajador'), is_active=True).first()
        if not t:
            return self._error('Elija al trabajador.')
        tipo = request.data.get('tipo') or 'induccion'
        if tipo not in dict(TIPOS_INDUCCION):
            return self._error('Tipo no válido.')
        if t.estado == 'cesado':
            return self._error(f'{t.nombre_completo} está cesado.')
        abierta = next((x for x in t.inducciones.filter(is_active=True) if x.estado != 'completa'), None)
        if abierta:
            return self._error(f'{t.nombre_completo} ya tiene una inducción en proceso ({abierta.codigo}).')
        if tipo == 'reinduccion' and not (request.data.get('motivo') or '').strip():
            return self._error('Indique el motivo de la re-inducción (cambio de puesto, retorno, actualización…).')
        i = Induccion.objects.create(trabajador=t, tipo=tipo, motivo=(request.data.get('motivo') or '').strip()[:200],
                                     fecha_inicio=parse_date(str(request.data.get('fecha_inicio') or '')[:10])
                                     or timezone.localdate(), created_by=request.user, updated_by=request.user)
        for k, _ in PARTES_INDUCCION:
            ParteInduccion.objects.create(induccion=i, parte=k, intento=1, created_by=request.user,
                                          updated_by=request.user, **_desde_plantilla(k))
        _hist(i, request, 'Registro')
        i.save(update_fields=['historial'])
        return self._respuesta(i, status.HTTP_201_CREATED)

    def _parte(self, i, request):
        if not i.is_active:  # inducción anulada: ninguna parte avanza
            return None
        return i.partes.filter(pk=request.data.get('id'), is_active=True).first()

    @action(detail=True, methods=['post'])
    def guardar_parte(self, request, pk=None):
        """Body: {id, responsable, fecha, hora_inicio, hora_fin, temas, documentos, preguntas, nota_directa,
        evaluador, fecha_evaluacion, observaciones}"""
        i = self.get_object()
        p = self._parte(i, request)
        if not p:
            return self._error('Parte no encontrada.')
        if p.estado != 'en_registro':
            return self._error(f'La {p.get_parte_display().lower()} ya fue firmada: no se modifica.')
        d = request.data
        for k, largo in (('responsable', 150), ('evaluador', 150), ('observaciones', None)):
            if k in d:
                setattr(p, k, (d.get(k) or '').strip()[:largo] if largo else (d.get(k) or '').strip())
        if 'evaluacion_url' in d:
            try:
                p.evaluacion_url = _enlace_valido(d.get('evaluacion_url'))
            except serializers.ValidationError as e:
                return self._error(str(e.detail[0]))
        for k in ('fecha', 'fecha_evaluacion'):
            if k in d:
                setattr(p, k, parse_date(str(d.get(k) or '')[:10]))
        for k in ('hora_inicio', 'hora_fin'):
            if k in d:
                setattr(p, k, parse_time(str(d.get(k) or '')[:5]) if d.get(k) else None)
        error = _fusionar_parte(p, d)
        if error:
            return self._error(error)
        if 'nota_directa' in d:
            n = _decimal(d.get('nota_directa'))
            if n is not None and not (0 <= n <= 20):
                return self._error('La nota es de 0 a 20.')
            p.nota_directa = n
        for q in p.preguntas or []:
            c = _decimal(q.get('calificacion'))
            if c is not None and (c < 0 or c > _decimal(q.get('puntos') or 0)):
                return self._error(f'La calificación de «{q.get("pregunta", "")[:60]}» va de 0 a {q.get("puntos")}.')
        p.updated_by = request.user
        p.save()
        return self._respuesta(i)
    guardar_parte.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def firmar_parte(self, request, pk=None):
        """Firman el responsable (su contraseña) y el colaborador (contraseña de su usuario o PIN).
        Con nota ≥ 14 la parte queda aprobada; si no, desaprobada (se repite solo esa parte)."""
        from sst.epp_api import firma_persona
        i = self.get_object()
        p = self._parte(i, request)
        if not p or p.estado != 'en_registro':
            return self._error('La parte no está en registro.')
        falta = []
        if not p.responsable:
            falta.append('el responsable')
        if not p.fecha:
            falta.append('la fecha')
        if not any(t.get('incluido') for t in p.temas or []):
            falta.append('los temas incluidos')
        if p.nota is None:
            falta.append('la evaluación (todas las calificaciones o la nota de la evaluación en línea)')
        if falta:
            return self._error('Falta registrar ' + ', '.join(falta) + '.')
        error = self._clave(request, 'la inducción')
        if error:
            return error
        f, error = firma_persona(request, i.trabajador)
        if error:
            return error
        p.firma_responsable, p.firma_colaborador = _firma(request), f
        p.estado = 'aprobada' if p.nota >= NOTA_APROBATORIA else 'desaprobada'
        p.updated_by = request.user
        p.save()
        _hist(i, request, f'{p.get_parte_display()}: {p.get_estado_display().lower()}', nota=str(p.nota))
        i.save(update_fields=['historial'])
        return self._respuesta(i)
    firmar_parte.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def repetir_parte(self, request, pk=None):
        """Nueva inducción solo en la parte desaprobada. Body: {parte}"""
        i = self.get_object()
        if not i.is_active:
            return self._error('La inducción está anulada.')
        clave = request.data.get('parte')
        ultima = i.ultima(clave)
        if not ultima or ultima.estado != 'desaprobada':
            return self._error('Solo se repite una parte desaprobada.')
        ParteInduccion.objects.create(induccion=i, parte=clave, intento=ultima.intento + 1, created_by=request.user,
                                      updated_by=request.user, **_desde_plantilla(clave))
        _hist(i, request, f'Nueva {ultima.get_parte_display().lower()} (intento {ultima.intento + 1})')
        i.save(update_fields=['historial'])
        return self._respuesta(i)
    repetir_parte.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        i = self.get_object()
        if i.partes.filter(is_active=True).exclude(estado='en_registro').exists():
            return self._error('Ya hay partes firmadas: la inducción no se anula.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo.')
        i.is_active, i.motivo_anulacion = False, motivo
        _hist(i, request, 'Anulación', motivo=motivo)
        i.save()
        return self._respuesta(i)
    anular.operacion = 'eliminar'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf import generar_induccion_pdf
        i = self.get_object()
        return self._pdf(generar_induccion_pdf(i), f'Inducción {i.codigo}')
    pdf.operacion = 'leer'


def _enlace_valido(v):
    v = (v or '').strip()
    if v and not v.lower().startswith(('http://', 'https://')):
        raise serializers.ValidationError(f'El enlace «{v[:60]}» debe empezar con http:// o https://.')
    return v


def _documentos_lista_maestra():
    """Documentos vigentes de la lista maestra para vincularlos a la inducción."""
    from esynapse_sig.models import Documento
    return Documento.objects.filter(is_active=True, archivado=False, versiones__estado='vigente').distinct()


def _resolver_documentos(lista):
    """Completa nombre, código y enlace de los documentos vinculados con la lista maestra (versión vigente)."""
    from esynapse_sig.models import Documento
    ids = [d.get('documento_id') for d in lista if d.get('documento_id')]
    docs = {x.pk: x for x in Documento.objects.filter(pk__in=ids)}
    salida = []
    for d in lista:
        d = dict(d)
        doc = docs.get(d.get('documento_id'))
        if doc:
            vv = doc.version_vigente
            d.update({'documento': doc.titulo, 'codigo': doc.codigo, 'version': vv.version if vv else '',
                      'enlace': _url(vv.archivo_publicado or vv.archivo) if vv else d.get('enlace', '')})
        salida.append(d)
    return salida


def _resumen_cambios(antes, despues):
    partes = []
    for k, nombre in (('temas', 'temas'), ('documentos', 'documentos'), ('preguntas', 'preguntas')):
        a, b = antes.get(k) or [], despues.get(k) or []
        if a != b:
            partes.append(f'{nombre}: {len(a)} → {len(b)}' if len(a) != len(b) else f'{nombre} modificados')
    if (antes.get('evaluacion_url') or '') != (despues.get('evaluacion_url') or ''):
        partes.append('enlace de la evaluación')
    return '; '.join(partes)


class PlantillaSerializer(serializers.ModelSerializer):
    parte_display = serializers.CharField(source='get_parte_display', read_only=True)

    class Meta:
        model = PlantillaInduccion
        fields = ['id', 'parte', 'parte_display', 'temas', 'documentos', 'preguntas', 'evaluacion_url', 'version',
                  'historial']
        read_only_fields = ['parte', 'version', 'historial']

    def validate_temas(self, v):
        limpio = []
        for t in v or []:
            if not (t.get('tema') or '').strip():
                raise serializers.ValidationError('Cada tema de la lista de verificación lleva su nombre.')
            limpio.append({'grupo': (t.get('grupo') or '').strip(), 'tema': t['tema'].strip(),
                           'descripcion': (t.get('descripcion') or '').strip(), 'codigo': (t.get('codigo') or '').strip(),
                           'enlace': _enlace_valido(t.get('enlace'))})
        return limpio

    def validate_documentos(self, v):
        validos = set(_documentos_lista_maestra().values_list('pk', flat=True))
        limpio = []
        for d in v or []:
            did = d.get('documento_id') or None
            if did and int(did) not in validos:
                raise serializers.ValidationError('El documento vinculado no está vigente en la lista maestra.')
            if not did and not (d.get('documento') or '').strip():
                raise serializers.ValidationError('Cada documento lleva su nombre o el vínculo con la lista maestra.')
            limpio.append({'documento': (d.get('documento') or '').strip(), 'codigo': (d.get('codigo') or '').strip(),
                           'enlace': '' if did else _enlace_valido(d.get('enlace')),
                           'documento_id': int(did) if did else None})
        return _resolver_documentos(limpio)

    def validate_preguntas(self, v):
        for q in v or []:
            if not (q.get('pregunta') or '').strip() or _decimal(q.get('puntos')) is None:
                raise serializers.ValidationError('Cada pregunta lleva texto y puntos.')
            if _decimal(q.get('puntos')) <= 0:
                raise serializers.ValidationError('Los puntos de cada pregunta son mayores que cero.')
        return [{'pregunta': q['pregunta'].strip(), 'puntos': float(_decimal(q['puntos']))} for q in v or []]

    def to_representation(self, obj):
        data = super().to_representation(obj)
        data['documentos'] = _resolver_documentos(data['documentos'])
        return data


class PlantillaViewSet(_Base, viewsets.ModelViewSet):
    """Contenido de cada parte de la inducción (lista de verificación, documentos con enlaces y preguntas).
    Cada cambio exige motivo, sube la versión y queda en el historial; las inducciones ya registradas conservan el
    contenido con que se hicieron."""
    queryset = PlantillaInduccion.objects.all()
    serializer_class = PlantillaSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def update(self, request, *args, **kwargs):
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo del cambio.')
        pl = self.get_object()
        ser = self.get_serializer(pl, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        # Se compara con el contenido guardado normalizado igual que el nuevo (claves y tipos), para no registrar
        # como cambio lo que solo difiere en forma.
        def normal(validar, valor):
            try:
                return validar(valor)
            except serializers.ValidationError:  # p. ej. un documento vinculado que dejó de estar vigente
                return valor
        antes = {'temas': normal(ser.validate_temas, pl.temas),
                 'documentos': normal(ser.validate_documentos, pl.documentos),
                 'preguntas': normal(ser.validate_preguntas, pl.preguntas), 'evaluacion_url': pl.evaluacion_url}
        cambios = _resumen_cambios(antes, {**antes, **ser.validated_data})
        if not cambios:
            return self._error('No hay cambios que guardar.')
        nueva = pl.version + 1
        historial = (pl.historial or []) + [{'version': nueva, 'fecha': timezone.localtime().isoformat(),
                                             'usuario': request.user.get_full_name() or request.user.username,
                                             'motivo': motivo, 'cambios': cambios}]
        ser.save(updated_by=request.user, version=nueva, historial=historial)
        return Response(self.get_serializer(pl).data)

    @action(detail=False, methods=['get'])
    def documentos_sig(self, request):
        """Documentos vigentes de la lista maestra para vincular (sin exigir permiso del módulo Documentos)."""
        return Response([{'id': d.pk, 'titulo': d.titulo, 'codigo': d.codigo}
                         for d in _documentos_lista_maestra().order_by('titulo')])
    documentos_sig.operacion = 'leer'
