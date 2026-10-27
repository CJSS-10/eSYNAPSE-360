"""API de EPP (catálogo, matriz por puesto, entregas firmadas con PIN, devoluciones) y vigilancia médica."""
import re

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.middleware import get_client_ip

from .epp import (APTITUDES, CLASIFICACION_EPP, ESTADOS_DEVOLUCION, MOTIVOS_REPOSICION, NIVELES_REQUISITO,
                  TIPOS_EMO, TIPOS_ENTREGA, TIPOS_PROTECCION, CatalogoEPP, EntregaEPP, EvaluacionMedica,
                  ItemEntregaEPP, PerfilEPP, PinTrabajador, RequisitoEPP, ResultadoEMO, es_operativo, renovacion)
from .eventos_api import _Base, _firma, _hist, _nombre
from .inspecciones import estado_fecha


def _trabajador(pk):
    from organizacion.models import Trabajador
    return Trabajador.objects.filter(pk=pk, is_active=True).select_related('puesto', 'area').first() if pk else None


def _datos_trabajador(t):
    a = t.area_efectiva
    return {'puesto': t.puesto.nombre if t.puesto_id else '', 'area': a.nombre if a else ''}


INTENTOS_CLAVE_FIRMA = 5
BLOQUEO_CLAVE_FIRMA = 15 * 60  # segundos


def _clave_firma_bloqueada(u):
    from django.core.cache import cache
    return (cache.get(f'firma-fallos-{u.pk}') or 0) >= INTENTOS_CLAVE_FIRMA


def _clave_firma_fallo(u):
    from django.core.cache import cache
    k = f'firma-fallos-{u.pk}'
    cache.add(k, 0, BLOQUEO_CLAVE_FIRMA)
    try:
        return cache.incr(k)
    except ValueError:
        cache.set(k, 1, BLOQUEO_CLAVE_FIRMA)
        return 1


def firma_persona(request, t, datos=None, clave='clave_trabajador', crear_pin=True):
    """Firma presencial de una persona. Regla del sistema: quien tiene usuario firma con la contraseña de su usuario;
    quien no lo tiene (personal sin acceso, terceros) firma con su PIN personal, que crea en su primera firma.
    datos: {<clave>} o {pin} o {pin_nuevo, pin_confirmacion} (por defecto, el cuerpo de la petición).
    crear_pin=False solo valida el PIN nuevo sin guardarlo (para firmas de varias personas: se guarda cuando
    todas las credenciales son válidas). Devuelve (firma, None) o (None, respuesta de error)."""
    datos = request.data if datos is None else datos

    def err(texto, **extra):
        return None, Response({'detail': texto, **extra}, status=status.HTTP_400_BAD_REQUEST)
    base = {'trabajador_id': t.pk, 'nombre': t.nombre_completo, 'documento': t.documento,
            'fecha': timezone.localtime().isoformat(timespec='seconds'), 'ip': get_client_ip(request)}
    u = t.usuario if t.usuario_id and t.usuario.is_active else None
    if u:
        pw = str(datos.get(clave) or '')
        if not pw:
            return err(f'{t.nombre_completo} debe firmar con la contraseña de su usuario.')
        # La contraseña de un tercero no se puede probar sin límite desde las pantallas de firma.
        if _clave_firma_bloqueada(u):
            return err(f'La firma de {t.nombre_completo} está bloqueada 15 minutos por intentos fallidos.')
        if not u.check_password(pw):
            n = _clave_firma_fallo(u)
            try:
                from core.models import LogAuditoria
                LogAuditoria.objects.create(usuario=request.user, usuario_nombre=_nombre(request.user),
                                            accion='ACCESO_BLOQUEADO', modulo='sst', entidad='Firma',
                                            entidad_id=str(u.pk), ip=get_client_ip(request),
                                            valor_nuevo=f'Contraseña de firma incorrecta de {u.username} ({n})')
            except Exception:
                pass
            quedan = max(0, INTENTOS_CLAVE_FIRMA - n)
            return err(f'Contraseña incorrecta de {t.nombre_completo}.'
                       + (f' Quedan {quedan} intento(s).' if quedan else ' Firma bloqueada 15 minutos.'))
        from django.core.cache import cache
        cache.delete(f'firma-fallos-{u.pk}')
        return {**base, 'metodo': 'usuario', 'usuario_id': u.pk}, None
    reg = PinTrabajador.objects.filter(trabajador=t).first()
    if not reg or not reg.pin:
        nuevo, conf = str(datos.get('pin_nuevo') or ''), str(datos.get('pin_confirmacion') or '')
        if not re.fullmatch(r'\d{4,6}', nuevo):
            return err(f'{t.nombre_completo} aún no tiene PIN: que lo cree ahora (4 a 6 dígitos).',
                       requiere_pin_nuevo=True)
        if nuevo != conf:
            return err(f'La confirmación del PIN de {t.nombre_completo} no coincide.', requiere_pin_nuevo=True)
        if not crear_pin:
            return {**base, 'metodo': 'pin'}, None
        reg = reg or PinTrabajador(trabajador=t)
        reg.fijar(nuevo)
        reg.historial = list(reg.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                      'accion': 'PIN creado', 'ante': _nombre(request.user)}]
        reg.save()
    else:
        if reg.bloqueado:
            return err(f'El PIN de {t.nombre_completo} está bloqueado por intentos fallidos: el Área SIG debe '
                       'restablecerlo, o adjunte el cargo firmado en papel.')
        if not reg.verificar(str(datos.get('pin') or '')):
            quedan = max(0, 5 - reg.intentos_fallidos)
            return err(f'PIN incorrecto de {t.nombre_completo}.'
                       + (f' Quedan {quedan} intento(s).' if quedan else ' El PIN quedó bloqueado.'))
    return {**base, 'metodo': 'pin'}, None


def _estado_pin(t):
    """Cómo firma la persona: 'usuario' (contraseña) o, sin usuario, el estado de su PIN."""
    if t.usuario_id and t.usuario.is_active:
        return 'usuario'
    p = PinTrabajador.objects.filter(trabajador=t).first()
    if not p or not p.pin:
        return 'sin_pin'
    return 'bloqueado' if p.bloqueado else 'activo'


# ============================================================================ serializers
class CatalogoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    clasificacion_display = serializers.CharField(source='get_clasificacion_display', read_only=True)

    class Meta:
        model = CatalogoEPP
        fields = ['id', 'nombre', 'tipo', 'tipo_display', 'clasificacion', 'clasificacion_display', 'marca_modelo',
                  'certificacion', 'vida_util_meses', 'descartable', 'orden', 'is_active']
        read_only_fields = ['is_active']

    def validate_nombre(self, v):
        v = (v or '').strip()
        qs = CatalogoEPP.objects.all()
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if any(x.nombre.casefold() == v.casefold() for x in qs):
            raise serializers.ValidationError('Ya existe ese EPP en el catálogo.')
        return v


class PerfilSerializer(serializers.ModelSerializer):
    area_nombre = serializers.CharField(source='area.nombre', read_only=True, default=None)
    puestos_nombres = serializers.SerializerMethodField()
    requisitos = serializers.SerializerMethodField()

    class Meta:
        model = PerfilEPP
        fields = ['id', 'nombre', 'grupo', 'puestos', 'puestos_nombres', 'area', 'area_nombre', 'en_campo', 'orden',
                  'is_active', 'requisitos']
        read_only_fields = ['is_active']

    def get_puestos_nombres(self, obj):
        return [p.nombre for p in obj.puestos.all()]

    def get_requisitos(self, obj):
        return [{'epp': r.epp_id, 'nivel': r.nivel} for r in obj.requisitos.all()]


class ItemEntregaSerializer(serializers.ModelSerializer):
    epp_nombre = serializers.CharField(source='epp.nombre', read_only=True)
    epp_tipo = serializers.CharField(source='epp.get_tipo_display', read_only=True)
    estado_renovacion = serializers.CharField(read_only=True)
    vigente = serializers.BooleanField(read_only=True)

    class Meta:
        model = ItemEntregaEPP
        fields = ['id', 'epp', 'epp_nombre', 'epp_tipo', 'cantidad', 'talla', 'observaciones', 'renovar_el',
                  'devuelto', 'fecha_devolucion', 'estado_devolucion', 'reemplazado_por', 'vigente',
                  'estado_renovacion']


class EntregaSerializer(serializers.ModelSerializer):
    trabajador_nombre = serializers.CharField(source='trabajador.nombre_completo', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    motivo_display = serializers.CharField(source='get_motivo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    items = serializers.SerializerMethodField()
    cargo_papel_url = serializers.SerializerMethodField()

    class Meta:
        model = EntregaEPP
        fields = ['id', 'codigo', 'trabajador', 'trabajador_nombre', 'fecha', 'tipo', 'tipo_display', 'motivo',
                  'motivo_display', 'puesto', 'area', 'observaciones', 'estado', 'estado_display', 'firma_trabajador',
                  'firma_responsable', 'cargo_papel_url', 'motivo_anulacion', 'historial', 'items']
        read_only_fields = ['codigo', 'puesto', 'area', 'estado', 'firma_trabajador', 'firma_responsable',
                            'motivo_anulacion', 'historial']

    def get_items(self, obj):
        return ItemEntregaSerializer(obj.items.filter(is_active=True).select_related('epp', 'entrega'), many=True).data

    def get_cargo_papel_url(self, obj):
        return obj.cargo_papel.url if obj.cargo_papel else None


class ResultadoSerializer(serializers.ModelSerializer):
    trabajador_nombre = serializers.CharField(source='trabajador.nombre_completo', read_only=True)
    documento = serializers.SerializerMethodField()
    aptitud_display = serializers.CharField(source='get_aptitud_display', read_only=True)
    certificado_url = serializers.SerializerMethodField()

    class Meta:
        model = ResultadoEMO
        fields = ['id', 'trabajador', 'trabajador_nombre', 'documento', 'puesto', 'area', 'aptitud',
                  'aptitud_display', 'restricciones', 'fecha_proximo', 'certificado_url', 'entrega_resultados',
                  'cargo_resultados_url', 'estado_pin']

    cargo_resultados_url = serializers.SerializerMethodField()
    estado_pin = serializers.SerializerMethodField()

    def get_cargo_resultados_url(self, obj):
        return obj.cargo_resultados.url if obj.cargo_resultados else None

    def get_estado_pin(self, obj):
        return _estado_pin(obj.trabajador)

    def get_documento(self, obj):
        return obj.trabajador.documento

    def get_certificado_url(self, obj):
        return obj.certificado.url if obj.certificado else None


class EvaluacionSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    resultados = serializers.SerializerMethodField()
    totales = serializers.SerializerMethodField()

    class Meta:
        model = EvaluacionMedica
        fields = ['id', 'codigo', 'tipo', 'tipo_display', 'fecha', 'centro_medico', 'medico', 'cmp', 'medidas',
                  'observaciones', 'estado', 'estado_display', 'firma_registro', 'motivo_anulacion', 'historial',
                  'resultados', 'totales']
        read_only_fields = ['codigo', 'estado', 'firma_registro', 'motivo_anulacion', 'historial']

    def _activos(self, obj):
        return obj.resultados.filter(is_active=True).select_related('trabajador')

    def get_resultados(self, obj):
        return ResultadoSerializer(self._activos(obj), many=True).data

    def get_totales(self, obj):
        rs = list(self._activos(obj))
        return {'evaluados': len(rs), **{k: sum(1 for r in rs if r.aptitud == k) for k, _ in APTITUDES}}

    def validate_medidas(self, valor):
        salida = []
        for m in valor or []:
            if isinstance(m, dict) and (m.get('descripcion') or '').strip():
                salida.append({'descripcion': m['descripcion'].strip(), 'responsable': (m.get('responsable') or '').strip(),
                               'fecha': (m.get('fecha') or '')[:10], 'estado': (m.get('estado') or 'pendiente').strip()})
        return salida


# ================================================================================== EPP
class CatalogoEPPViewSet(_Base, viewsets.ModelViewSet):
    queryset = CatalogoEPP.objects.all()
    serializer_class = CatalogoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(is_active=True) if self.request.query_params.get('inactivos') != '1' else qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        e = self.get_object()
        e.is_active = False
        e.updated_by = request.user
        e.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'tipos': TIPOS_PROTECCION, 'clasificaciones': CLASIFICACION_EPP, 'niveles': NIVELES_REQUISITO,
                         'tipos_entrega': TIPOS_ENTREGA, 'motivos': MOTIVOS_REPOSICION,
                         'estados_devolucion': ESTADOS_DEVOLUCION, 'tipos_emo': TIPOS_EMO, 'aptitudes': APTITUDES})
    catalogos.operacion = 'leer'


class PerfilEPPViewSet(_Base, viewsets.ModelViewSet):
    """Matriz de EPP por puesto de trabajo."""
    queryset = PerfilEPP.objects.filter(is_active=True).select_related('area').prefetch_related('puestos',
                                                                                                   'requisitos')
    serializer_class = PerfilSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        p = self.get_object()
        p.is_active = False
        p.updated_by = request.user
        p.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def requisitos(self, request, pk=None):
        """Reemplaza los EPP del perfil. Body: {requisitos: [{epp, nivel}]}"""
        p = self.get_object()
        validos = dict(NIVELES_REQUISITO)
        nuevos = {}
        for r in request.data.get('requisitos') or []:
            epp = CatalogoEPP.objects.filter(pk=r.get('epp'), is_active=True).first()
            if not epp:
                return self._error('EPP no encontrado en el catálogo.')
            nuevos[epp.pk] = r.get('nivel') if r.get('nivel') in validos else 'obligatorio'
        with transaction.atomic():
            p.requisitos.exclude(epp_id__in=nuevos).delete()
            for epp_id, nivel in nuevos.items():
                RequisitoEPP.objects.update_or_create(perfil=p, epp_id=epp_id, defaults={'nivel': nivel})
        return Response(PerfilSerializer(PerfilEPP.objects.get(pk=p.pk)).data)
    requisitos.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def matriz_pdf(self, request):
        from .pdf_epp import generar_matriz_epp_pdf
        return self._pdf(generar_matriz_epp_pdf(), 'Matriz de EPP por puesto de trabajo')
    matriz_pdf.operacion = 'leer'


def requeridos(trabajador, campo=False):
    """EPP que la matriz exige al trabajador: {epp_id: nivel} (obligatorio prevalece sobre según la tarea)."""
    salida = {}
    for p in PerfilEPP.objects.filter(is_active=True).prefetch_related('puestos', 'requisitos'):
        if p.aplica_a(trabajador) or (campo and p.en_campo):
            for r in p.requisitos.all():
                if salida.get(r.epp_id) != 'obligatorio':
                    salida[r.epp_id] = r.nivel
    return salida


def estado_epp(trabajador):
    hoy = timezone.localdate()
    req = requeridos(trabajador)
    vigentes = {}
    for it in ItemEntregaEPP.objects.filter(entrega__trabajador=trabajador, entrega__estado='firmada', is_active=True,
                                            devuelto=False, reemplazado_por__isnull=True).select_related('epp',
                                                                                                         'entrega'):
        actual = vigentes.get(it.epp_id)
        if not actual or (it.entrega.fecha, it.pk) > (actual.entrega.fecha, actual.pk):
            vigentes[it.epp_id] = it
    filas = []
    ids = set(req) | set(vigentes)
    for epp in CatalogoEPP.objects.filter(pk__in=ids):
        it = vigentes.get(epp.pk)
        filas.append({'epp': epp.pk, 'nombre': epp.nombre, 'tipo': epp.get_tipo_display(), 'orden': epp.orden,
                      'nivel': req.get(epp.pk), 'item': it.pk if it else None,
                      'entregado': it.entrega.fecha.isoformat() if it else None,
                      'entrega': it.entrega.codigo if it else None,
                      'renovar_el': it.renovar_el.isoformat() if it and it.renovar_el else None,
                      'estado': ('falta' if not it and req.get(epp.pk) == 'obligatorio' else
                                 'segun_tarea' if not it else estado_fecha(it.renovar_el, hoy) or 'vigente')})
    filas.sort(key=lambda f: (f['orden'], f['nombre']))
    return filas


class EntregaEPPViewSet(_Base, viewsets.ModelViewSet):
    """Entrega de EPP: en registro → firmada (responsable con contraseña, trabajador con PIN o papel)."""
    queryset = EntregaEPP.objects.all().select_related('trabajador').prefetch_related('items__epp')
    serializer_class = EntregaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list':
            qs = qs.filter(is_active=True)
        if p.get('trabajador'):
            qs = qs.filter(trabajador_id=p['trabajador'])
        if p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        if p.get('anio'):
            qs = qs.filter(fecha__year=p['anio'])
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(trabajador__nombres__icontains=b)
                           | Q(trabajador__apellidos__icontains=b))
        return qs

    def _respuesta(self, e, codigo=status.HTTP_200_OK):
        return Response(EntregaSerializer(EntregaEPP.objects.get(pk=e.pk)).data, status=codigo)

    def _items(self, e, lista, request):
        nuevos = []
        for d in lista or []:
            epp = CatalogoEPP.objects.filter(pk=d.get('epp'), is_active=True).first()
            if not epp:
                return self._error('EPP no encontrado en el catálogo.')
            try:
                cant = int(d.get('cantidad') or 1)
            except (TypeError, ValueError):
                return self._error('Cantidad no válida.')
            if cant < 1:
                return self._error('La cantidad debe ser al menos 1.')
            nuevos.append(ItemEntregaEPP(entrega=e, epp=epp, cantidad=cant, talla=(d.get('talla') or '').strip()[:20],
                                         observaciones=(d.get('observaciones') or '').strip()[:250],
                                         created_by=request.user, updated_by=request.user))
        e.items.filter(is_active=True).update(is_active=False)
        ItemEntregaEPP.objects.bulk_create(nuevos)
        return None

    def create(self, request, *args, **kwargs):
        t = _trabajador(request.data.get('trabajador'))
        if not t or t.estado != 'activo':
            return self._error('Elija un trabajador activo.')
        ser = EntregaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        datos = {k: v for k, v in ser.validated_data.items() if k != 'trabajador'}
        with transaction.atomic():
            e = EntregaEPP.objects.create(trabajador=t, created_by=request.user, updated_by=request.user,
                                          **_datos_trabajador(t), **datos)
            error = self._items(e, request.data.get('items'), request)
            if error:
                transaction.set_rollback(True)
                return error
            _hist(e, request, 'Registro')
            e.save(update_fields=['historial'])
        return self._respuesta(e, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        e = self.get_object()
        if e.estado != 'en_registro':
            return self._error(f'La entrega está {e.get_estado_display().lower()}: no se modifica.')
        ser = EntregaSerializer(e, data={k: v for k, v in request.data.items() if k not in ('items', 'trabajador')},
                                partial=True)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            ser.save(updated_by=request.user)
            if 'items' in request.data:
                error = self._items(e, request.data['items'], request)
                if error:
                    transaction.set_rollback(True)
                    return error
        return self._respuesta(e)

    def destroy(self, request, *args, **kwargs):
        return self._error('Una entrega no se elimina: si se registró por error, se anula con motivo.')

    def _validar(self, e):
        if e.estado != 'en_registro':
            return self._error('La entrega ya fue firmada o anulada.')
        if not e.items.filter(is_active=True).exists():
            return self._error('Registre al menos un EPP entregado.')
        if e.tipo == 'reposicion' and not e.motivo:
            return self._error('Indique el motivo de la reposición.')
        return None

    def _cerrar(self, e, request, firma_trabajador):
        e.firma_trabajador, e.firma_responsable, e.estado = firma_trabajador, _firma(request), 'firmada'
        for it in e.items.filter(is_active=True).select_related('epp', 'entrega'):
            it.renovar_el = renovacion(it)
            it.save(update_fields=['renovar_el'])
            # La reposición reemplaza al EPP del mismo tipo que el trabajador tenía en uso.
            ItemEntregaEPP.objects.filter(entrega__trabajador=e.trabajador, entrega__estado='firmada', epp=it.epp,
                                          is_active=True, devuelto=False, reemplazado_por__isnull=True) \
                .exclude(entrega=e).update(reemplazado_por=it)
        _hist(e, request, 'Firma de la entrega', metodo=firma_trabajador.get('metodo'))
        e.updated_by = request.user
        e.save()
        return self._respuesta(e)

    @action(detail=True, methods=['post'])
    def firmar(self, request, pk=None):
        """Body: {password (responsable), pin} o, la primera vez, {password, pin_nuevo, pin_confirmacion}."""
        e = self.get_object()
        error = self._validar(e) or self._clave(request, 'la entrega')
        if error:
            return error
        firma, error = firma_persona(request, e.trabajador)
        if error:
            return error
        return self._cerrar(e, request, firma)
    firmar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def firmar_papel(self, request, pk=None):
        """El trabajador firmó el cargo en papel: se adjunta escaneado. Multipart: {archivo, password}"""
        e = self.get_object()
        error = self._validar(e)
        if error:
            return error
        if not request.FILES.get('archivo'):
            return self._error('Adjunte el cargo firmado por el trabajador.')
        error = self._clave(request, 'la entrega')
        if error:
            return error
        e.cargo_papel = request.FILES['archivo']
        t = e.trabajador
        return self._cerrar(e, request, {'trabajador_id': t.pk, 'nombre': t.nombre_completo, 'documento': t.documento,
                                         'metodo': 'papel', 'fecha': timezone.localtime().isoformat(timespec='seconds')})
    firmar_papel.operacion = 'editar'

    @action(detail=False, methods=['post'])
    def restablecer_pin(self, request):
        """El Área SIG restablece el PIN de un trabajador: lo crea de nuevo en su próxima entrega."""
        t = _trabajador(request.data.get('trabajador'))
        if not t:
            return self._error('Trabajador no encontrado.')
        reg = PinTrabajador.objects.filter(trabajador=t).first()
        if not reg:
            return self._error('El trabajador aún no tiene PIN.')
        reg.pin, reg.bloqueado, reg.intentos_fallidos = '', False, 0
        reg.historial = list(reg.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                      'accion': 'PIN restablecido', 'por': _nombre(request.user)}]
        reg.save()
        return Response({'trabajador': t.pk, 'estado_pin': _estado_pin(t)})
    restablecer_pin.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def devolver(self, request, pk=None):
        """Devolución por cese, rotación o cambio de puesto. Body: {fecha, items: [{id, estado_devolucion}]}"""
        e = self.get_object()
        if e.estado != 'firmada':
            return self._error('Solo se devuelven EPP de una entrega firmada.')
        f = request.data.get('fecha') or timezone.localdate().isoformat()
        hechos = []
        for d in request.data.get('items') or []:
            it = e.items.filter(pk=d.get('id'), is_active=True, devuelto=False).first()
            if not it:
                return self._error('EPP no encontrado o ya devuelto.')
            if d.get('estado_devolucion') not in dict(ESTADOS_DEVOLUCION):
                return self._error('Indique el estado del EPP devuelto.')
            it.devuelto, it.fecha_devolucion, it.estado_devolucion = True, f, d['estado_devolucion']
            it.updated_by = request.user
            it.save()
            hechos.append(it.epp.nombre)
        if not hechos:
            return self._error('Elija los EPP devueltos.')
        _hist(e, request, 'Devolución', epp=', '.join(hechos))
        e.save(update_fields=['historial'])
        return self._respuesta(e)
    devolver.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        e = self.get_object()
        if e.estado != 'en_registro':
            return self._error('Solo se anula una entrega aún no firmada.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la anulación.')
        e.estado, e.motivo_anulacion = 'anulada', motivo
        _hist(e, request, 'Anulación', motivo=motivo)
        e.save()
        return self._respuesta(e)
    anular.operacion = 'eliminar'

    @action(detail=False, methods=['get'])
    def estado(self, request):
        """Situación de EPP de un trabajador frente a la matriz: falta, vigente, por renovar, vencido."""
        t = _trabajador(request.query_params.get('trabajador'))
        if not t:
            return self._error('Trabajador no encontrado.')
        return Response({'trabajador': t.pk, 'nombre': t.nombre_completo, **_datos_trabajador(t),
                         'estado_pin': _estado_pin(t), 'filas': estado_epp(t)})
    estado.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def sugerir(self, request):
        """EPP que corresponde entregar: los obligatorios que faltan y los vencidos o por vencer (y los de campo)."""
        t = _trabajador(request.query_params.get('trabajador'))
        if not t:
            return self._error('Trabajador no encontrado.')
        campo = request.query_params.get('campo') == '1'
        filas = estado_epp(t)
        ids = {f['epp'] for f in filas if f['estado'] in ('falta', 'vencido', 'por_vencer')}
        if campo:
            vig = {f['epp'] for f in filas if f['estado'] == 'vigente'}
            ids |= set(requeridos(t, campo=True)) - vig
        return Response([{'epp': e.pk, 'nombre': e.nombre, 'cantidad': 1}
                         for e in CatalogoEPP.objects.filter(pk__in=ids)])
    sugerir.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Alertas: EPP por renovar o vencidos, obligatorios sin entregar, cesados sin devolver, PIN bloqueados."""
        from organizacion.models import Trabajador
        renovar, faltan = [], []
        for t in Trabajador.objects.filter(is_active=True, estado='activo').select_related('puesto', 'area'):
            for f in estado_epp(t):
                if f['estado'] in ('vencido', 'por_vencer'):
                    renovar.append({'trabajador': t.pk, 'nombre': t.nombre_completo, 'epp': f['nombre'],
                                    'fecha': f['renovar_el'], 'estado': f['estado']})
                elif f['estado'] == 'falta':
                    faltan.append({'trabajador': t.pk, 'nombre': t.nombre_completo, 'epp': f['nombre']})
        sin_devolver = []
        for it in ItemEntregaEPP.objects.filter(entrega__estado='firmada', is_active=True, devuelto=False,
                                                reemplazado_por__isnull=True, epp__descartable=False,
                                                entrega__trabajador__estado='cesado').select_related('epp',
                                                                                                     'entrega__trabajador'):
            sin_devolver.append({'trabajador': it.entrega.trabajador_id, 'nombre': it.entrega.trabajador.nombre_completo,
                                 'epp': it.epp.nombre, 'entrega': it.entrega_id})
        bloqueados = [{'trabajador': p.trabajador_id, 'nombre': p.trabajador.nombre_completo}
                      for p in PinTrabajador.objects.filter(bloqueado=True).select_related('trabajador')]
        return Response({'por_renovar': renovar, 'faltan': faltan, 'sin_devolver': sin_devolver,
                         'pin_bloqueados': bloqueados,
                         'en_registro': EntregaEPP.objects.filter(is_active=True, estado='en_registro').count()})
    resumen.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf_epp import generar_entregas_pdf
        e = self.get_object()
        return self._pdf(generar_entregas_pdf(e.trabajador, [e]), e.codigo)
    pdf.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def tarjeta_pdf(self, request):
        """Todas las entregas firmadas del trabajador, dos por hoja, como el formato."""
        from .pdf_epp import generar_entregas_pdf
        t = _trabajador(request.query_params.get('trabajador'))
        if not t:
            return self._error('Trabajador no encontrado.')
        entregas = list(EntregaEPP.objects.filter(trabajador=t, estado='firmada', is_active=True)
                        .order_by('fecha', 'id'))
        return self._pdf(generar_entregas_pdf(t, entregas), f'EPP {t.nombre_completo}')
    tarjeta_pdf.operacion = 'leer'


# ==================================================================== vigilancia médica
class EvaluacionMedicaViewSet(_Base, viewsets.ModelViewSet):
    """Evaluación médica ocupacional: en registro → registrada (firma). Solo aptitud, sin diagnóstico."""
    queryset = EvaluacionMedica.objects.all().prefetch_related('resultados__trabajador')
    serializer_class = EvaluacionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list':
            qs = qs.filter(is_active=True)
        if p.get('anio'):
            qs = qs.filter(fecha__year=p['anio'])
        if p.get('tipo'):
            qs = qs.filter(tipo=p['tipo'])
        return qs

    def _respuesta(self, ev, codigo=status.HTTP_200_OK):
        return Response(EvaluacionSerializer(EvaluacionMedica.objects.get(pk=ev.pk)).data, status=codigo)

    def _agregar(self, ev, t, request):
        if ev.resultados.filter(trabajador=t, is_active=True).exists():
            return False
        r = ResultadoEMO(evaluacion=ev, trabajador=t, created_by=request.user, updated_by=request.user,
                         **_datos_trabajador(t))
        if ev.tipo != 'retiro':
            r.fecha_proximo = r.proximo_sugerido()
        r.save()
        return True

    def create(self, request, *args, **kwargs):
        ser = EvaluacionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        with transaction.atomic():
            ev = ser.save(created_by=request.user, updated_by=request.user)
            for tid in request.data.get('trabajadores') or []:
                t = _trabajador(tid)
                if t:
                    self._agregar(ev, t, request)
            _hist(ev, request, 'Registro')
            ev.save(update_fields=['historial'])
        return self._respuesta(ev, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        ev = self.get_object()
        if ev.estado != 'en_registro':
            return self._error(f'La evaluación está {ev.get_estado_display().lower()}: no se modifica.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return self._error('Una evaluación no se elimina: si se registró por error, se anula con motivo.')

    def _en_registro(self, ev):
        return None if ev.estado == 'en_registro' else self._error('La evaluación ya fue registrada o anulada.')

    @action(detail=True, methods=['post'])
    def agregar(self, request, pk=None):
        """Body: {trabajadores: [ids]}"""
        ev = self.get_object()
        error = self._en_registro(ev)
        if error:
            return error
        n = sum(1 for tid in request.data.get('trabajadores') or [] if (t := _trabajador(tid)) and self._agregar(ev, t, request))
        if not n:
            return self._error('Elija trabajadores que aún no estén en la evaluación.')
        return self._respuesta(ev)
    agregar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def resultado(self, request, pk=None):
        """Body: {id, aptitud, restricciones, fecha_proximo}"""
        ev = self.get_object()
        error = self._en_registro(ev)
        if error:
            return error
        r = ev.resultados.filter(pk=request.data.get('id'), is_active=True).first()
        if not r:
            return self._error('Resultado no encontrado.')
        if 'aptitud' in request.data:
            if request.data['aptitud'] not in dict(APTITUDES) and request.data['aptitud']:
                return self._error('Aptitud no válida.')
            r.aptitud = request.data['aptitud'] or ''
        if 'restricciones' in request.data:
            r.restricciones = (request.data.get('restricciones') or '').strip()
        if 'fecha_proximo' in request.data:
            from django.utils.dateparse import parse_date
            r.fecha_proximo = parse_date(str(request.data.get('fecha_proximo') or '')[:10])
        r.updated_by = request.user
        r.save()
        return self._respuesta(ev)
    resultado.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar(self, request, pk=None):
        ev = self.get_object()
        error = self._en_registro(ev)
        if error:
            return error
        r = ev.resultados.filter(pk=request.data.get('id'), is_active=True).first()
        if not r:
            return self._error('Resultado no encontrado.')
        r.is_active = False
        r.save(update_fields=['is_active'])
        return self._respuesta(ev)
    quitar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def certificado(self, request, pk=None):
        """Certificado de aptitud de un trabajador. Multipart: {id, archivo}"""
        ev = self.get_object()
        error = self._en_registro(ev)
        if error:
            return error
        r = ev.resultados.filter(pk=request.data.get('id'), is_active=True).first()
        if not r or not request.FILES.get('archivo'):
            return self._error('Elija el trabajador y adjunte el certificado de aptitud.')
        r.certificado = request.FILES['archivo']
        r.save(update_fields=['certificado'])
        return self._respuesta(ev)
    certificado.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def firmar(self, request, pk=None):
        ev = self.get_object()
        error = self._en_registro(ev)
        if error:
            return error
        rs = list(ev.resultados.filter(is_active=True).select_related('trabajador'))
        if not rs:
            return self._error('Registre al menos un trabajador evaluado.')
        falta = []
        sin_apt = [r for r in rs if not r.aptitud]
        if sin_apt:
            falta.append(f'la aptitud de {len(sin_apt)} trabajador(es) (p. ej. {sin_apt[0].trabajador.nombre_completo})')
        sin_restr = [r for r in rs if r.aptitud in ('apto_restricciones', 'no_apto') and not r.restricciones]
        if sin_restr:
            falta.append(f'las restricciones o recomendaciones de {sin_restr[0].trabajador.nombre_completo}')
        if ev.tipo != 'retiro':
            sin_prox = [r for r in rs if not r.fecha_proximo and r.aptitud != 'no_apto']
            if sin_prox:
                falta.append(f'la fecha del próximo examen de {sin_prox[0].trabajador.nombre_completo}')
        if not ev.centro_medico.strip():
            falta.append('el centro médico')
        if falta:
            return self._error('Para registrar la evaluación indique ' + '; '.join(falta) + '.')
        error = self._clave(request, 'la evaluación médica')
        if error:
            return error
        ev.estado, ev.firma_registro = 'registrado', _firma(request)
        _hist(ev, request, 'Firma del registro')
        ev.updated_by = request.user
        ev.save()
        return self._respuesta(ev)
    firmar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        ev = self.get_object()
        error = self._en_registro(ev)
        if error:
            return error
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la anulación.')
        ev.estado, ev.motivo_anulacion = 'anulado', motivo
        _hist(ev, request, 'Anulación', motivo=motivo)
        ev.save()
        return self._respuesta(ev)
    anular.operacion = 'eliminar'

    def _resultado_registrado(self, ev, request):
        if ev.estado != 'registrado':
            return None, self._error('Los resultados se entregan después de registrar la evaluación.')
        r = ev.resultados.filter(pk=request.data.get('id'), is_active=True).select_related('trabajador').first()
        if not r:
            return None, self._error('Resultado no encontrado.')
        if r.entrega_resultados:
            return None, self._error(f'Los resultados de {r.trabajador.nombre_completo} ya se entregaron.')
        return r, None

    @action(detail=True, methods=['post'])
    def entregar_resultados(self, request, pk=None):
        """Cargo de entrega de resultados: el trabajador firma con su PIN y quien registra con su contraseña.
        Body: {id, password, pin | pin_nuevo + pin_confirmacion, entregado_por}"""
        ev = self.get_object()
        r, error = self._resultado_registrado(ev, request)
        if error:
            return error
        error = self._clave(request, 'la entrega de resultados')
        if error:
            return error
        firma, error = firma_persona(request, r.trabajador)
        if error:
            return error
        r.entrega_resultados = {**firma, 'entregado_por': (request.data.get('entregado_por') or ev.medico or '').strip(),
                                'registrado_por': _firma(request)}
        r.save(update_fields=['entrega_resultados'])
        _hist(ev, request, 'Entrega de resultados', trabajador=r.trabajador.nombre_completo)
        ev.save(update_fields=['historial'])
        return self._respuesta(ev)
    entregar_resultados.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def entregar_resultados_papel(self, request, pk=None):
        """Cargo de entrega firmado en papel. Multipart: {id, archivo, password}"""
        ev = self.get_object()
        r, error = self._resultado_registrado(ev, request)
        if error:
            return error
        if not request.FILES.get('archivo'):
            return self._error('Adjunte el cargo firmado por el trabajador.')
        error = self._clave(request, 'la entrega de resultados')
        if error:
            return error
        r.cargo_resultados = request.FILES['archivo']
        r.entrega_resultados = {'trabajador_id': r.trabajador_id, 'nombre': r.trabajador.nombre_completo,
                                'metodo': 'papel', 'fecha': timezone.localtime().isoformat(timespec='seconds'),
                                'registrado_por': _firma(request)}
        r.save(update_fields=['entrega_resultados', 'cargo_resultados'])
        _hist(ev, request, 'Entrega de resultados (cargo en papel)', trabajador=r.trabajador.nombre_completo)
        ev.save(update_fields=['historial'])
        return self._respuesta(ev)
    entregar_resultados_papel.operacion = 'editar'

    @action(detail=False, methods=['post'])
    def registrar_anexo4(self, request):
        """Multipart: {anio, fecha_presentacion, archivo, observaciones}"""
        from django.utils.dateparse import parse_date
        from .epp import InformeAnexo4
        try:
            anio = int(request.data.get('anio'))
        except (TypeError, ValueError):
            return self._error('Indique el año que informa.')
        f = parse_date(str(request.data.get('fecha_presentacion') or '')[:10])
        if not f:
            return self._error('Indique la fecha de presentación.')
        if not request.FILES.get('archivo'):
            return self._error('Adjunte el informe presentado.')
        obs = (request.data.get('observaciones') or '').strip()
        previo = InformeAnexo4.objects.filter(anio=anio).first()
        if previo:
            # Corrección controlada: se reemplaza con motivo y queda la constancia del registro anterior.
            if request.data.get('reemplazar') not in ('1', 'true', True):
                return self._error(f'El informe de {anio} ya está registrado.')
            motivo = (request.data.get('motivo') or '').strip()
            if not motivo:
                return self._error('Indique el motivo del reemplazo.')
            nota = (f'[{timezone.localdate().isoformat()}] Reemplaza el registro anterior (presentado el '
                    f'{previo.fecha_presentacion.isoformat()}) por {_nombre(request.user)}. Motivo: {motivo}')
            previo.fecha_presentacion, previo.archivo = f, request.FILES['archivo']
            previo.observaciones = '\n'.join(x for x in (obs, nota, previo.observaciones) if x)
            previo.updated_by = request.user
            previo.save()
        else:
            InformeAnexo4.objects.create(anio=anio, fecha_presentacion=f, archivo=request.FILES['archivo'],
                                         observaciones=obs, created_by=request.user, updated_by=request.user)
        return self.anexo4(request)
    registrar_anexo4.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def anexo4(self, request):
        """Informes anuales presentados y el pendiente del año anterior (plazo: 31 de marzo)."""
        from .epp import InformeAnexo4
        hoy = timezone.localdate()
        informes = [{'anio': i.anio, 'fecha_presentacion': i.fecha_presentacion.isoformat(),
                     'archivo_url': i.archivo.url if i.archivo else None, 'observaciones': i.observaciones}
                    for i in InformeAnexo4.objects.all()]
        anio = hoy.year - 1
        limite = hoy.replace(month=3, day=31)
        pendiente = None if any(i['anio'] == anio for i in informes) else {
            'anio': anio, 'limite': limite.isoformat(), 'estado': 'vencido' if hoy > limite else 'por_vencer'}
        return Response({'informes': informes, 'pendiente': pendiente})
    anexo4.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf_epp import generar_emo_pdf
        ev = self.get_object()
        return self._pdf(generar_emo_pdf(ev), ev.codigo)
    pdf.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def vigilancia(self, request):
        """Por trabajador activo: último examen registrado, aptitud y próximo examen (vencido / por vencer)."""
        from organizacion.models import Trabajador
        hoy = timezone.localdate()
        filas = []
        for t in Trabajador.objects.filter(is_active=True, estado='activo').select_related('puesto', 'area') \
                .order_by('apellidos', 'nombres'):
            r = (ResultadoEMO.objects.filter(trabajador=t, is_active=True, evaluacion__estado='registrado')
                 .select_related('evaluacion').order_by('-evaluacion__fecha', '-id').first())
            filas.append({'trabajador': t.pk, 'nombre': t.nombre_completo, **_datos_trabajador(t),
                          'personal': 'operativo' if es_operativo(t) else 'administrativo',
                          'ultimo': r.evaluacion.fecha.isoformat() if r else None,
                          'evaluacion': r.evaluacion.codigo if r else None,
                          'tipo': r.evaluacion.get_tipo_display() if r else None,
                          'aptitud': r.aptitud if r else None, 'aptitud_display': r.get_aptitud_display() if r else None,
                          'restricciones': r.restricciones if r else '',
                          'proximo': r.fecha_proximo.isoformat() if r and r.fecha_proximo else None,
                          # Sin fecha del próximo examen (p. ej. último resultado «no apto») no es «vigente»: se
                          # muestra para que se programe.
                          'estado': ('sin_examen' if not r else estado_fecha(r.fecha_proximo, hoy) or 'sin_proximo')})
        return Response(filas)
    vigilancia.operacion = 'leer'
