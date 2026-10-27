"""API de Revisión por la dirección: programa anual, revisiones (preparación → reunión → cerrada) y plan de acción."""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular

from . import datos as fuentes
from .models import (ELEMENTOS, ENTRADAS, ESTADOS_ACUERDO, ESTADOS_REVISION, MOTIVOS_EXTRAORDINARIA, SALIDAS,
                     SALIDAS_OBLIGATORIAS, SIGLAS_OBLIGATORIAS_CIERRE, TIPOS_REVISION, TITULO_ELEMENTO,
                     AcuerdoRevision, AsistenteRevision, EntradaRevision, ItemProgramaRevision, ProgramaRevision,
                     Revision, SalidaRevision, sigla_de_puesto)

TIT_ENTRADA, TIT_SALIDA = dict(ENTRADAS), dict(SALIDAS)


def _nombre(u):
    return (u.get_full_name() or u.username) if u else ''


def _firma(request):
    u = request.user
    return {'usuario_id': u.pk, 'nombre': _nombre(u), 'cargo': getattr(u, 'cargo', ''),
            'sigla': getattr(u, 'sigla_cargo', ''), 'fecha': timezone.localtime().isoformat(timespec='seconds'),
            'ip': get_client_ip(request)}


def _hist(obj, request, accion, **extra):
    obj.historial = list(obj.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                  'usuario': _nombre(request.user), 'accion': accion, **extra}]


def _url(f):
    return f.url if f else None


class _Base:
    permission_classes = [PermisoModular]
    modulo = 'revision_direccion'
    pagination_class = None

    def _error(self, mensaje, **extra):
        return Response({'detail': mensaje, **extra}, status=status.HTTP_400_BAD_REQUEST)

    def _clave(self, request, que):
        pw = request.data.get('password') or ''
        if not pw:
            return self._error(f'Confirme con su contraseña para {que}.')
        if not request.user.check_password(pw):
            return self._error(f'Contraseña incorrecta. No se registró {que}.')
        return None

    def _pdf(self, contenido, nombre):
        resp = HttpResponse(contenido, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{nombre}.pdf"'
        return resp


# ================================================================================================= programa
class ItemProgramaSerializer(serializers.ModelSerializer):
    titulo = serializers.SerializerMethodField()
    responsable_nombre = serializers.CharField(source='responsable.nombre', read_only=True, default=None)

    class Meta:
        model = ItemProgramaRevision
        fields = ['id', 'clave', 'titulo', 'responsable', 'responsable_nombre', 'meses', 'ejecutados', 'observaciones']

    def get_titulo(self, obj):
        return TITULO_ELEMENTO.get(obj.clave, obj.clave)


class ProgramaSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = ProgramaRevision
        fields = ['id', 'anio', 'fecha_elaboracion', 'observaciones', 'items', 'historial', 'updated_at']
        read_only_fields = ['historial']

    def get_items(self, obj):
        return ItemProgramaSerializer(obj.items.select_related('responsable'), many=True).data


class ProgramaViewSet(_Base, viewsets.ModelViewSet):
    serializer_class = ProgramaSerializer
    queryset = ProgramaRevision.objects.all()
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def create(self, request, *args, **kwargs):
        anio = str(request.data.get('anio') or '')
        if not anio.isdigit():
            return self._error('Indique el año.')
        if ProgramaRevision.objects.filter(anio=int(anio)).exists():
            return self._error(f'Ya existe el programa {anio}.')
        with transaction.atomic():
            p = ProgramaRevision.objects.create(anio=int(anio), created_by=request.user, updated_by=request.user)
            ItemProgramaRevision.objects.bulk_create([
                ItemProgramaRevision(programa=p, clave=c, created_by=request.user, updated_by=request.user)
                for c, _ in ELEMENTOS])
            _hist(p, request, 'Registro')
            p.save(update_fields=['historial'])
        return Response(self.get_serializer(p).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['get'])
    def anio(self, request):
        v = str(request.query_params.get('anio') or timezone.localdate().year)
        p = ProgramaRevision.objects.filter(anio=int(v) if v.isdigit() else 0).first()
        return Response(self.get_serializer(p).data if p else None)
    anio.operacion = 'leer'

    @action(detail=True, methods=['post'])
    def item(self, request, pk=None):
        """Actualiza un elemento del programa. Body: {id, responsable?, meses?, ejecutados?, observaciones?}"""
        p = self.get_object()
        i = p.items.filter(pk=request.data.get('id')).first()
        if not i:
            return self._error('Elemento no encontrado.')
        d = request.data
        for campo in ('meses', 'ejecutados'):
            if campo in d:
                v = d[campo] or []
                if not isinstance(v, list) or any(not isinstance(m, int) or not 1 <= m <= 12 for m in v):
                    return self._error('Los meses van del 1 al 12.')
                setattr(i, campo, sorted(set(v)))
        if 'ejecutados' in d:
            hoy = timezone.localdate()
            if any((p.anio, m) > (hoy.year, hoy.month) for m in i.ejecutados):
                return self._error('No se marca como ejecutado un mes futuro.')
        if 'responsable' in d:
            from organizacion.models import Puesto
            i.responsable = Puesto.objects.filter(pk=d['responsable']).first() if d['responsable'] else None
        if 'observaciones' in d:
            i.observaciones = str(d['observaciones'] or '')[:300]
        i.updated_by = request.user
        i.save()
        p.updated_by = request.user
        p.save(update_fields=['updated_by', 'updated_at'])
        return Response(self.get_serializer(p).data)
    item.operacion = 'editar'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf import generar_programa_pdf
        p = self.get_object()
        return self._pdf(generar_programa_pdf(p), f'Programa de revisión por la dirección {p.anio}')
    pdf.operacion = 'leer'


# ================================================================================================ revisiones
class EntradaSerializer(serializers.ModelSerializer):
    titulo = serializers.SerializerMethodField()
    completa = serializers.BooleanField(read_only=True)

    class Meta:
        model = EntradaRevision
        fields = ['id', 'clave', 'titulo', 'datos', 'analisis', 'sin_actividad', 'completa']

    def get_titulo(self, obj):
        return TIT_ENTRADA.get(obj.clave, '')


class SalidaSerializer(serializers.ModelSerializer):
    titulo = serializers.SerializerMethodField()

    class Meta:
        model = SalidaRevision
        fields = ['id', 'clave', 'titulo', 'texto']

    def get_titulo(self, obj):
        return TIT_SALIDA.get(obj.clave, '')


class AsistenteSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='trabajador.nombre_completo', read_only=True)
    forma_firma = serializers.SerializerMethodField()

    class Meta:
        model = AsistenteRevision
        fields = ['id', 'trabajador', 'nombre', 'cargo', 'sigla', 'firma', 'forma_firma']

    def get_forma_firma(self, obj):
        """'usuario' (contraseña), 'activo' (PIN), 'sin_pin' (lo crea al firmar) o 'bloqueado'."""
        from sst.epp_api import _estado_pin
        return None if obj.firma else _estado_pin(obj.trabajador)


class AcuerdoSerializer(serializers.ModelSerializer):
    revision_codigo = serializers.CharField(source='revision.codigo', read_only=True)
    revision_estado = serializers.CharField(source='revision.estado', read_only=True)
    revision_fecha = serializers.DateField(source='revision.fecha', read_only=True)
    elemento_titulo = serializers.SerializerMethodField()
    responsable_nombre = serializers.CharField(source='responsable.nombre_completo', read_only=True, default=None)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    archivo_evidencia_url = serializers.SerializerMethodField()
    vencido = serializers.BooleanField(read_only=True)

    class Meta:
        model = AcuerdoRevision
        fields = ['id', 'revision', 'revision_codigo', 'revision_estado', 'revision_fecha', 'numero', 'descripcion',
                  'elemento', 'elemento_titulo', 'responsable', 'responsable_nombre', 'fecha_compromiso',
                  'costo_estimado', 'evidencia', 'archivo_evidencia', 'archivo_evidencia_url', 'estado',
                  'estado_display', 'seguimiento_1', 'seguimiento_2', 'fecha_cierre', 'firma_cierre', 'vencido',
                  'historial']
        read_only_fields = ['revision', 'numero', 'estado', 'fecha_cierre', 'firma_cierre', 'historial']
        extra_kwargs = {'archivo_evidencia': {'write_only': True, 'required': False}}

    def get_elemento_titulo(self, obj):
        return TITULO_ELEMENTO.get(obj.elemento, '')

    def get_archivo_evidencia_url(self, obj):
        return _url(obj.archivo_evidencia)


class RevisionSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    motivo_display = serializers.CharField(source='get_motivo_extraordinaria_display', read_only=True)
    recopilacion_nombre = serializers.CharField(source='responsable_recopilacion.nombre_completo', read_only=True,
                                                default=None)
    verificacion_nombre = serializers.CharField(source='responsable_verificacion.nombre_completo', read_only=True,
                                                default=None)
    reunion_comite_codigo = serializers.CharField(source='reunion_comite.codigo', read_only=True, default=None)
    etapas_abiertas = serializers.SerializerMethodField()
    resumen = serializers.SerializerMethodField()

    class Meta:
        model = Revision
        fields = ['id', 'codigo', 'programa', 'tipo', 'tipo_display', 'motivo_extraordinaria', 'motivo_display',
                  'detalle_motivo', 'fecha', 'lugar', 'periodo_desde', 'periodo_hasta', 'responsable_recopilacion',
                  'recopilacion_nombre', 'responsable_verificacion', 'verificacion_nombre', 'conclusiones',
                  'observaciones', 'comunicacion_fecha', 'comunicacion_detalle', 'reunion_comite',
                  'reunion_comite_codigo', 'estado', 'estado_display', 'datos_generados', 'firma_cierre',
                  'motivo_anulacion', 'historial', 'etapas_abiertas', 'resumen', 'updated_at']
        read_only_fields = ['codigo', 'estado', 'datos_generados', 'firma_cierre', 'motivo_anulacion', 'historial']

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas()

    def get_resumen(self, obj):
        ent = list(obj.entradas.all())
        acu = [a for a in obj.acuerdos.all() if a.is_active]
        asi = [a for a in obj.asistentes.all() if a.is_active]
        return {'entradas': len(ent), 'entradas_completas': len([e for e in ent if e.completa]),
                'asistentes': len(asi), 'firmados': len([a for a in asi if a.firma]),
                'acuerdos': len(acu), 'acuerdos_cerrados': len([a for a in acu if a.estado == 'cerrado'])}

    def validate(self, data):
        inst = self.instance

        def val(c):
            return data[c] if c in data else getattr(inst, c, None)
        if val('tipo') == 'extraordinaria' and not val('motivo_extraordinaria'):
            raise serializers.ValidationError({'motivo_extraordinaria': ['Indique el motivo de la revisión '
                                                                         'extraordinaria.']})
        if val('tipo') == 'ordinaria':
            data['motivo_extraordinaria'] = ''
        d, h = val('periodo_desde'), val('periodo_hasta')
        if d and h and h < d:
            raise serializers.ValidationError({'periodo_hasta': ['El fin del periodo es anterior a su inicio.']})
        f = val('fecha')
        if f and h and f < h:
            raise serializers.ValidationError({'fecha': ['La revisión se realiza después del periodo que evalúa.']})
        return data


class RevisionDetalleSerializer(RevisionSerializer):
    entradas = EntradaSerializer(many=True, read_only=True)
    salidas = SalidaSerializer(many=True, read_only=True)
    asistentes = serializers.SerializerMethodField()
    acuerdos = serializers.SerializerMethodField()

    class Meta(RevisionSerializer.Meta):
        fields = RevisionSerializer.Meta.fields + ['entradas', 'salidas', 'asistentes', 'acuerdos']

    def get_asistentes(self, obj):
        return AsistenteSerializer(obj.asistentes.filter(is_active=True).select_related('trabajador__usuario'),
                                   many=True).data

    def get_acuerdos(self, obj):
        return AcuerdoSerializer(obj.acuerdos.filter(is_active=True).select_related('responsable', 'revision'),
                                 many=True).data


class RevisionViewSet(_Base, viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_serializer_class(self):
        return RevisionSerializer if self.action == 'list' else RevisionDetalleSerializer

    def get_queryset(self):
        qs = Revision.objects.select_related('responsable_recopilacion', 'responsable_verificacion', 'reunion_comite') \
            .prefetch_related('entradas', 'asistentes', 'acuerdos')
        p = self.request.query_params
        if self.action == 'list' and p.get('anulados') != '1':
            qs = qs.filter(is_active=True)
        if str(p.get('anio') or '').isdigit():
            qs = qs.filter(codigo__endswith=f'-{p["anio"]}')
        return qs

    def _det(self, r):
        return Response(RevisionDetalleSerializer(self.get_queryset().get(pk=r.pk),
                                                  context={'request': self.request}).data)

    def perform_create(self, serializer):
        with transaction.atomic():
            fecha = serializer.validated_data.get('fecha') or timezone.localdate()
            programa = serializer.validated_data.get('programa') or \
                ProgramaRevision.objects.filter(anio=fecha.year).first()
            r = serializer.save(created_by=self.request.user, updated_by=self.request.user, programa=programa)
            EntradaRevision.objects.bulk_create([EntradaRevision(revision=r, clave=c, created_by=self.request.user,
                                                                 updated_by=self.request.user) for c, _ in ENTRADAS])
            SalidaRevision.objects.bulk_create([SalidaRevision(revision=r, clave=c, created_by=self.request.user,
                                                               updated_by=self.request.user) for c, _ in SALIDAS])
            _hist(r, self.request, 'Registro')
            r.save(update_fields=['historial'])

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        self.perform_create(s)
        return Response(RevisionDetalleSerializer(s.instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Solo se modifican los campos de las etapas abiertas (ADR-0005)."""
        r = self.get_object()
        if not r.is_active:
            return self._error('La revisión está anulada.')
        abiertas = r.etapas_abiertas()
        for campo in request.data.keys():
            etapa = Revision.etapa_de_campo(campo)
            if etapa and etapa not in abiertas:
                nombre = Revision._meta.get_field(campo).verbose_name
                orden = [e for e, _ in ESTADOS_REVISION]
                inicio = next(est[0] for n, est, _ in Revision.ETAPAS if n == etapa)
                situacion = 'aún no se abre' if orden.index(inicio) > orden.index(r.estado) else 'está cerrada'
                return self._error(f'La etapa de {Revision.NOMBRES_ETAPA[etapa]} {situacion}: no se modifica '
                                   f'«{nombre}».')
        kwargs['partial'] = True
        super().update(request, *args, **kwargs)
        return self._det(self.get_object())

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def _en(self, r, estado, que):
        if not r.is_active or r.estado != estado:
            nombre = dict(ESTADOS_REVISION)[estado].lower()
            return self._error(f'{que} solo en la etapa «{nombre}» (la revisión está en «{r.get_estado_display().lower()}»).')
        return None

    # ---------------------------------------------------------------------------------------- preparación
    @action(detail=True, methods=['post'])
    def generar_datos(self, request, pk=None):
        """Obtiene de los módulos los datos de cada entrada para el periodo evaluado."""
        r = self.get_object()
        error = self._en(r, 'preparacion', 'Los datos del sistema se generan')
        if error:
            return error
        for e in r.entradas.all():
            e.datos = fuentes.generar(r, e.clave)
            e.updated_by = request.user
            e.save(update_fields=['datos', 'updated_by', 'updated_at'])
        r.datos_generados = timezone.now()
        _hist(r, request, 'Datos del sistema generados',
              periodo=' al '.join(str(x) for x in fuentes.periodo(r)))
        r.save(update_fields=['datos_generados', 'historial'])
        return self._det(r)
    generar_datos.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def entrada(self, request, pk=None):
        """Análisis de una entrada. Body: {clave, analisis?, sin_actividad?}"""
        r = self.get_object()
        error = self._en(r, 'preparacion', 'El análisis de las entradas se registra')
        if error:
            return error
        e = r.entradas.filter(clave=request.data.get('clave')).first()
        if not e:
            return self._error('Entrada no encontrada.')
        if 'analisis' in request.data:
            e.analisis = str(request.data.get('analisis') or '').strip()
        if 'sin_actividad' in request.data:
            e.sin_actividad = request.data.get('sin_actividad') in (True, 'true', '1', 1)
        e.updated_by = request.user
        e.save()
        return Response(EntradaSerializer(e).data)
    entrada.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def convocar(self, request, pk=None):
        """Pasa a la reunión: exige los datos generales y que todas las entradas tengan análisis o se marquen sin
        actividad en el periodo (el Gerente SIG verifica la totalidad antes de convocar)."""
        r = self.get_object()
        error = self._en(r, 'preparacion', 'Se convoca')
        if error:
            return error
        faltan = [Revision._meta.get_field(c).verbose_name for c in
                  ('fecha', 'periodo_desde', 'periodo_hasta', 'responsable_recopilacion', 'responsable_verificacion')
                  if not getattr(r, c)]
        if faltan:
            return self._error(f'Complete antes de convocar: {", ".join(faltan)}.')
        incompletas = [e.clave for e in r.entradas.all() if not e.completa]
        if incompletas:
            return self._error('Entradas sin análisis (o sin marcar «sin actividad en el periodo»): '
                               f'{", ".join(c + ")" for c in incompletas)}.', entradas=incompletas)
        r.estado, r.updated_by = 'reunion', request.user
        _hist(r, request, 'Convocatoria a la reunión')
        r.save()
        return self._det(r)
    convocar.operacion = 'editar'

    # --------------------------------------------------------------------------------------------- reunión
    @action(detail=True, methods=['post'])
    def asistente(self, request, pk=None):
        """Agrega un asistente. Body: {trabajador}"""
        from organizacion.models import Trabajador
        r = self.get_object()
        error = self._en(r, 'reunion', 'Los asistentes se registran')
        if error:
            return error
        t = Trabajador.objects.filter(pk=request.data.get('trabajador'), is_active=True, estado='activo') \
            .select_related('puesto').first()
        if not t:
            return self._error('Elija un trabajador activo.')
        if r.asistentes.filter(trabajador=t, is_active=True).exists():
            return self._error(f'{t.nombre_completo} ya está en la lista de asistentes.')
        AsistenteRevision.objects.create(revision=r, trabajador=t, cargo=t.puesto.nombre[:150],
                                         sigla=sigla_de_puesto(t.puesto), created_by=request.user,
                                         updated_by=request.user)
        return self._det(r)
    asistente.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_asistente(self, request, pk=None):
        r = self.get_object()
        error = self._en(r, 'reunion', 'Los asistentes se modifican')
        if error:
            return error
        a = r.asistentes.filter(pk=request.data.get('id'), is_active=True).first()
        if not a:
            return self._error('Asistente no encontrado.')
        if a.firma:
            return self._error('El asistente ya firmó: no se quita de la lista.')
        a.is_active, a.updated_by = False, request.user
        a.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return self._det(r)
    quitar_asistente.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def firmar_asistente(self, request, pk=None):
        """Firma de asistencia: contraseña del usuario del asistente o su PIN. Body: {id, clave | pin | pin_nuevo +
        pin_confirmacion}"""
        from sst.epp_api import firma_persona
        r = self.get_object()
        error = self._en(r, 'reunion', 'La asistencia se firma')
        if error:
            return error
        a = r.asistentes.filter(pk=request.data.get('id'), is_active=True).select_related('trabajador__usuario').first()
        if not a:
            return self._error('Asistente no encontrado.')
        if a.firma:
            return self._error('El asistente ya firmó.')
        f, error = firma_persona(request, a.trabajador, clave='clave')
        if error:
            return error
        a.firma, a.updated_by = f, request.user
        a.save(update_fields=['firma', 'updated_by', 'updated_at'])
        return self._det(r)
    firmar_asistente.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def salida(self, request, pk=None):
        """Decisiones y acciones de una salida. Body: {clave, texto}"""
        r = self.get_object()
        error = self._en(r, 'reunion', 'Las salidas se registran')
        if error:
            return error
        s = r.salidas.filter(clave=request.data.get('clave')).first()
        if not s:
            return self._error('Salida no encontrada.')
        s.texto, s.updated_by = str(request.data.get('texto') or '').strip(), request.user
        s.save()
        return Response(SalidaSerializer(s).data)
    salida.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def acuerdo(self, request, pk=None):
        """Registra o corrige un acuerdo en la reunión. Body: {id?, descripcion, elemento, responsable,
        fecha_compromiso, costo_estimado}"""
        from organizacion.models import Trabajador
        r = self.get_object()
        error = self._en(r, 'reunion', 'Los acuerdos se registran')
        if error:
            return error
        d = request.data
        a = r.acuerdos.filter(pk=d.get('id'), is_active=True).first() if d.get('id') else None
        desc = str(d.get('descripcion') if 'descripcion' in d else (a.descripcion if a else '') or '').strip()
        if not desc:
            return self._error('Describa el acuerdo.')
        elemento = d.get('elemento', a.elemento if a else '') or ''
        if elemento and elemento not in TITULO_ELEMENTO:
            return self._error('Elemento de la revisión no válido.')
        resp = Trabajador.objects.filter(pk=d.get('responsable')).first() if d.get('responsable') else None
        if not resp:
            return self._error('Indique el responsable del acuerdo.')
        fecha = parse_date(str(d.get('fecha_compromiso') or '')[:10])
        if not fecha:
            return self._error('Indique la fecha de cumplimiento.')
        costo = None
        if str(d.get('costo_estimado') or '').strip():
            try:
                costo = Decimal(str(d['costo_estimado']).replace(',', '.'))
            except InvalidOperation:
                return self._error('Costo estimado no válido.')
            if costo < 0:
                return self._error('El costo estimado no puede ser negativo.')
        if not a:
            n = (r.acuerdos.order_by('-numero').values_list('numero', flat=True).first() or 0) + 1
            a = AcuerdoRevision(revision=r, numero=n, created_by=request.user)
        a.descripcion, a.elemento, a.responsable, a.fecha_compromiso, a.costo_estimado = desc, elemento, resp, fecha, costo
        a.updated_by = request.user
        a.save()
        return self._det(r)
    acuerdo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_acuerdo(self, request, pk=None):
        r = self.get_object()
        error = self._en(r, 'reunion', 'Los acuerdos se quitan')
        if error:
            return error
        a = r.acuerdos.filter(pk=request.data.get('id'), is_active=True).first()
        if not a:
            return self._error('Acuerdo no encontrado.')
        a.is_active, a.updated_by = False, request.user
        a.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return self._det(r)
    quitar_acuerdo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """Cierra la revisión (informe firmado): conclusiones, salidas, asistencia firmada por todos con el Gerente SIG
        y el Gerente General entre ellos, y la contraseña de quien la cierra. Body: {password}"""
        r = self.get_object()
        error = self._en(r, 'reunion', 'Se cierra')
        if error:
            return error
        faltan = []
        if not (r.conclusiones or '').strip():
            faltan.append('las conclusiones')
        sin_salida = [s.clave for s in r.salidas.all() if s.clave in SALIDAS_OBLIGATORIAS and not (s.texto or '').strip()]
        if sin_salida:
            faltan.append(f'las salidas {", ".join(c + ")" for c in sin_salida)} (escriba «Ninguna» si no hubo '
                          'decisiones)')
        asi = list(r.asistentes.filter(is_active=True))
        if not asi:
            faltan.append('los asistentes')
        sin_firma = [a.trabajador.nombre_completo for a in asi if not a.firma]
        if sin_firma:
            faltan.append(f'la firma de asistencia de {", ".join(sin_firma)}')
        siglas = {a.sigla for a in asi if a.firma}
        nombres = {'GSIG': 'el Gerente SIG', 'GG': 'el Gerente General'}
        for s in SIGLAS_OBLIGATORIAS_CIERRE:
            if s not in siglas:
                faltan.append(f'la participación y firma de {nombres[s]}')
        if faltan:
            return self._error('Para cerrar falta: ' + '; '.join(faltan) + '.')
        error = self._clave(request, 'el cierre de la revisión')
        if error:
            return error
        r.estado, r.firma_cierre, r.updated_by = 'cerrada', _firma(request), request.user
        _hist(r, request, 'Cierre (informe firmado)', acuerdos=r.acuerdos.filter(is_active=True).count())
        r.save()
        return self._det(r)
    cerrar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """Anula una revisión registrada por error, antes de su cierre. Body: {motivo}"""
        r = self.get_object()
        if not r.is_active or r.estado not in ('preparacion', 'reunion'):
            return self._error('Una revisión cerrada no se anula.')
        motivo = str(request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la anulación.')
        r.estado, r.is_active, r.motivo_anulacion, r.updated_by = 'anulada', False, motivo, request.user
        _hist(r, request, 'Anulación', motivo=motivo)
        r.save()
        return Response(RevisionSerializer(r).data)
    anular.operacion = 'eliminar'

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'entradas': ENTRADAS, 'salidas': SALIDAS, 'elementos': ELEMENTOS, 'tipos': TIPOS_REVISION,
                         'motivos': MOTIVOS_EXTRAORDINARIA, 'estados': ESTADOS_REVISION,
                         'estados_acuerdo': ESTADOS_ACUERDO})
    catalogos.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf import generar_informe_pdf
        r = self.get_object()
        return self._pdf(generar_informe_pdf(r), f'Informe de revisión por la dirección {r.codigo}')
    pdf.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def plan_pdf(self, request, pk=None):
        from .pdf import generar_plan_pdf
        r = self.get_object()
        return self._pdf(generar_plan_pdf(r), f'Plan de acción {r.codigo}')
    plan_pdf.operacion = 'leer'


# ============================================================================================ plan de acción
class AcuerdoViewSet(_Base, viewsets.ModelViewSet):
    """Plan de acción: todos los acuerdos. Tras cerrar la revisión solo se registra su seguimiento."""
    serializer_class = AcuerdoSerializer
    http_method_names = ['get', 'patch', 'post', 'head', 'options']

    def get_queryset(self):
        qs = AcuerdoRevision.objects.filter(is_active=True, revision__is_active=True) \
            .select_related('revision', 'responsable')
        p = self.request.query_params
        if p.get('estado') == 'pendientes':
            qs = qs.exclude(estado='cerrado')
        elif p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        if str(p.get('revision') or '').isdigit():
            qs = qs.filter(revision_id=p['revision'])
        if str(p.get('responsable') or '').isdigit():
            qs = qs.filter(responsable_id=p['responsable'])
        return qs.order_by('-revision__created_at', 'numero')

    def create(self, request, *args, **kwargs):
        return self._error('Los acuerdos se registran en la reunión de la revisión.')

    def update(self, request, *args, **kwargs):
        """Seguimiento del acuerdo (revisión cerrada): evidencia, archivo, seguimiento semestral y estado
        (abierto / en proceso). El cierre va con su visto bueno."""
        a = self.get_object()
        if a.revision.estado != 'cerrada':
            return self._error('El seguimiento se registra cuando la revisión está cerrada; antes, el acuerdo se '
                               'corrige en la reunión.')
        if a.estado == 'cerrado':
            return self._error('El acuerdo está cerrado: no se modifica.')
        cambios = []
        for c in AcuerdoRevision.CAMPOS_SEGUIMIENTO:
            if c in request.data:
                if c == 'archivo_evidencia':
                    f = request.FILES.get('archivo_evidencia')
                    if f:
                        a.archivo_evidencia = f
                        cambios.append('archivo de evidencia')
                    continue
                v = str(request.data.get(c) or '').strip()
                if v != getattr(a, c):
                    setattr(a, c, v)
                    cambios.append(AcuerdoRevision._meta.get_field(c).verbose_name)
        prohibidos = [c for c in AcuerdoRevision.CAMPOS_ACUERDO if c in request.data]
        if prohibidos:
            return self._error('Lo acordado en la reunión no se modifica después del cierre de la revisión '
                               f'({", ".join(AcuerdoRevision._meta.get_field(c).verbose_name for c in prohibidos)}).')
        nuevo = request.data.get('estado')
        if nuevo:
            if nuevo not in ('abierto', 'en_proceso'):
                return self._error('El acuerdo se cierra con su visto bueno de cumplimiento.')
            if nuevo != a.estado:
                cambios.append(f'estado: {dict(ESTADOS_ACUERDO)[nuevo]}')
                a.estado = nuevo
        if cambios:
            _hist(a, request, 'Seguimiento', campos=', '.join(cambios))
        a.updated_by = request.user
        a.save()
        return Response(self.get_serializer(a).data)

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """V°B° de cumplimiento: exige evidencia y la contraseña de quien da el visto bueno. Body: {password}"""
        a = self.get_object()
        if a.revision.estado != 'cerrada':
            return self._error('El acuerdo se cierra cuando la revisión está cerrada.')
        if a.estado == 'cerrado':
            return self._error('El acuerdo ya está cerrado.')
        if not ((a.evidencia or '').strip() or a.archivo_evidencia):
            return self._error('Registre la evidencia de ejecución antes de cerrar el acuerdo.')
        error = self._clave(request, 'el visto bueno de cumplimiento')
        if error:
            return error
        a.estado, a.fecha_cierre, a.firma_cierre, a.updated_by = 'cerrado', timezone.localdate(), _firma(request), \
            request.user
        _hist(a, request, 'V°B° de cumplimiento (cerrado)')
        a.save()
        return Response(self.get_serializer(a).data)
    cerrar.operacion = 'aprobar'
