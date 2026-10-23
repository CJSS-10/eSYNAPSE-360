"""API del Comité de SST (miembros, reuniones, acuerdos) y del Programa anual SSOMA."""
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .comite import (CARGOS_COMITE, CONDICION, ESTADOS_ACUERDO, REPRESENTACION, TIPOS_REUNION, AcuerdoComite,
                     ActividadSSOMA, ComiteSST, MiembroComite, ObjetivoSSOMA, ProgramaSSOMA, ReunionComite)
from .eventos_api import _Base, _firma, _hist, _nombre

ARCHIVOS_COMITE = {'acta_eleccion': 'el acta del proceso de elección', 'acta_instalacion': 'el acta de instalación',
                   'constancia_t_registro': 'la constancia del T-Registro'}


def _url(f):
    return f.url if f else None


# ============================================================================ serializers
class MiembroSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source='trabajador.nombre_completo', read_only=True)
    documento = serializers.CharField(source='trabajador.documento', read_only=True)
    puesto = serializers.CharField(source='trabajador.puesto.nombre', read_only=True)
    representacion_display = serializers.CharField(source='get_representacion_display', read_only=True)
    condicion_display = serializers.CharField(source='get_condicion_display', read_only=True)
    cargo_display = serializers.CharField(source='get_cargo_display', read_only=True)

    class Meta:
        model = MiembroComite
        fields = ['id', 'trabajador', 'nombre', 'documento', 'puesto', 'representacion', 'representacion_display',
                  'condicion', 'condicion_display', 'cargo', 'cargo_display', 'fecha_alta', 'fecha_baja',
                  'motivo_baja']


class ComiteSerializer(serializers.ModelSerializer):
    miembros = serializers.SerializerMethodField()
    vigente = serializers.BooleanField(read_only=True)
    archivos = serializers.SerializerMethodField()
    alertas = serializers.SerializerMethodField()

    class Meta:
        model = ComiteSST
        fields = ['id', 'periodo', 'fecha_eleccion', 'fecha_instalacion', 'fecha_fin', 'fecha_t_registro',
                  'observaciones', 'vigente', 'miembros', 'archivos', 'alertas', 'historial']
        read_only_fields = ['historial']

    def get_miembros(self, obj):
        return MiembroSerializer(obj.miembros.filter(is_active=True).select_related('trabajador__puesto'),
                                 many=True).data

    def get_archivos(self, obj):
        return {k: _url(getattr(obj, k)) for k in ARCHIVOS_COMITE}

    def get_alertas(self, obj):
        hoy = timezone.localdate()
        al = []
        act = [m for m in obj.miembros.filter(is_active=True, fecha_baja__isnull=True)]
        tit = [m for m in act if m.condicion == 'titular']
        emp = sum(1 for m in tit if m.representacion == 'empleador')
        trab = sum(1 for m in tit if m.representacion == 'trabajadores')
        if emp != trab:
            al.append(f'Comité no paritario: {emp} titular(es) del empleador y {trab} de los trabajadores.')
        for cargo, nombre in (('presidente', 'presidente'), ('secretario', 'secretario')):
            if not any(m.cargo == cargo for m in act):
                al.append(f'Falta designar al {nombre}.')
        if not obj.fecha_t_registro:
            al.append('Falta registrar el comité en el T-Registro (no hacerlo es infracción grave).')
        if obj.vigente and (obj.fecha_fin - hoy).days <= 60:
            al.append(f'El mandato vence el {obj.fecha_fin.isoformat()}: programe la nueva elección.')
        if obj.vigente and not obj.reuniones.filter(is_active=True, estado='realizada', fecha__year=hoy.year,
                                                    fecha__month=hoy.month).exists():
            al.append('Aún no se registra la reunión ordinaria de este mes.')
        vencidos = sum(1 for a in AcuerdoComite.objects.filter(reunion__comite=obj, is_active=True) if a.vencido)
        if vencidos:
            al.append(f'{vencidos} acuerdo(s) vencido(s).')
        return al


class AcuerdoSerializer(serializers.ModelSerializer):
    responsable_nombre = serializers.CharField(source='responsable.nombre_completo', read_only=True, default=None)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    reunion_codigo = serializers.CharField(source='reunion.codigo', read_only=True)
    reunion_fecha = serializers.DateField(source='reunion.fecha', read_only=True)
    vencido = serializers.BooleanField(read_only=True)

    class Meta:
        model = AcuerdoComite
        fields = ['id', 'reunion', 'reunion_codigo', 'reunion_fecha', 'orden', 'descripcion', 'responsable',
                  'responsable_nombre', 'plazo', 'estado', 'estado_display', 'seguimiento', 'fecha_cumplimiento',
                  'vencido']


class ReunionSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    acuerdos = serializers.SerializerMethodField()
    quorum = serializers.SerializerMethodField()
    acta_url = serializers.SerializerMethodField()

    class Meta:
        model = ReunionComite
        fields = ['id', 'comite', 'codigo', 'tipo', 'tipo_display', 'fecha', 'hora', 'lugar', 'asistentes',
                  'invitados', 'agenda', 'desarrollo', 'proxima_reunion', 'estado', 'estado_display',
                  'motivo_cancelacion', 'acta_url', 'acuerdos', 'quorum', 'historial']
        read_only_fields = ['codigo', 'estado', 'motivo_cancelacion', 'historial']

    def get_acuerdos(self, obj):
        return AcuerdoSerializer(obj.acuerdos.filter(is_active=True).select_related('responsable', 'reunion'),
                                 many=True).data

    def get_quorum(self, obj):
        return obj.quorum()

    def get_acta_url(self, obj):
        return _url(obj.acta_firmada)

    def validate_agenda(self, v):
        return [str(x).strip() for x in v or [] if str(x).strip()]

    def validate(self, data):
        comite = data.get('comite') or getattr(self.instance, 'comite', None)
        for m in data.get('asistentes') or []:
            if m.comite_id != comite.pk:
                raise serializers.ValidationError({'asistentes': ['Solo asisten miembros de este comité.']})
        return data


class ActividadSerializer(serializers.ModelSerializer):
    responsable_nombre = serializers.CharField(source='responsable.nombre', read_only=True, default=None)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True, default=None)
    avance = serializers.IntegerField(read_only=True)

    class Meta:
        model = ActividadSSOMA
        fields = ['id', 'objetivo', 'orden', 'descripcion', 'indicador', 'meta', 'responsable', 'responsable_nombre',
                  'area', 'area_nombre', 'meses', 'meses_ejecutados', 'evidencias', 'avance']
        read_only_fields = ['meses_ejecutados', 'evidencias']

    def validate_meses(self, v):
        return sorted({int(m) for m in v or [] if str(m).isdigit() and 1 <= int(m) <= 12})


class ProgramaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    objetivos = serializers.SerializerMethodField()
    actividades = serializers.SerializerMethodField()
    indicadores = serializers.SerializerMethodField()
    reunion_aprobacion_codigo = serializers.CharField(source='reunion_aprobacion.codigo', read_only=True,
                                                      default=None)

    class Meta:
        model = ProgramaSSOMA
        fields = ['id', 'anio', 'version', 'estado', 'estado_display', 'objetivo_general', 'recursos', 'fecha',
                  'fecha_actualizacion', 'elaborado', 'revisado', 'aprobado', 'reunion_aprobacion',
                  'reunion_aprobacion_codigo', 'objetivos', 'actividades', 'indicadores', 'historial']
        read_only_fields = ['version', 'estado', 'elaborado', 'revisado', 'aprobado', 'historial']

    def get_objetivos(self, obj):
        return [{'id': o.pk, 'codigo': o.codigo, 'descripcion': o.descripcion, 'orden': o.orden}
                for o in obj.objetivos.filter(is_active=True)]

    def get_actividades(self, obj):
        return ActividadSerializer(obj.actividades.filter(is_active=True).select_related('responsable', 'area',
                                                                                         'objetivo'), many=True).data

    def get_indicadores(self, obj):
        """Avance por objetivo: actividades ejecutadas / programadas hasta el mes actual (o todo el año)."""
        hoy = timezone.localdate()
        mes = 12 if obj.anio < hoy.year else hoy.month if obj.anio == hoy.year else 0
        salida = []
        for o in obj.objetivos.filter(is_active=True):
            prog = ejec = 0
            for a in o.actividades.filter(is_active=True):
                p = [m for m in a.meses or [] if m <= mes]
                prog += len(p)
                ejec += len([m for m in a.meses_ejecutados or [] if m in p])
            salida.append({'objetivo': o.pk, 'codigo': o.codigo, 'programadas': prog, 'ejecutadas': ejec,
                           'avance': round(100 * ejec / prog) if prog else None})
        return salida


# ================================================================================ comité
class ComiteViewSet(_Base, viewsets.ModelViewSet):
    queryset = ComiteSST.objects.filter(is_active=True).prefetch_related('miembros__trabajador')
    serializer_class = ComiteSerializer

    def perform_create(self, serializer):
        c = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(c, self.request, 'Registro del comité')
        c.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        c = serializer.save(updated_by=self.request.user)
        _hist(c, self.request, 'Actualización', campos=', '.join(serializer.validated_data))
        c.save(update_fields=['historial'])

    def destroy(self, request, *args, **kwargs):
        return self._error('Un comité no se elimina: queda como registro de su periodo.')

    def _respuesta(self, c):
        return Response(ComiteSerializer(ComiteSST.objects.get(pk=c.pk)).data)

    @action(detail=False, methods=['get'])
    def vigente(self, request):
        hoy = timezone.localdate()
        c = (ComiteSST.objects.filter(is_active=True, fecha_instalacion__lte=hoy, fecha_fin__gte=hoy).first()
             or ComiteSST.objects.filter(is_active=True).first())
        return Response(ComiteSerializer(c).data if c else None)
    vigente.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'representacion': REPRESENTACION, 'condicion': CONDICION, 'cargos': CARGOS_COMITE,
                         'tipos_reunion': TIPOS_REUNION, 'estados_acuerdo': ESTADOS_ACUERDO})
    catalogos.operacion = 'leer'

    @action(detail=True, methods=['post'])
    def adjuntar(self, request, pk=None):
        """Multipart: {campo (acta_eleccion / acta_instalacion / constancia_t_registro), archivo}"""
        c = self.get_object()
        campo = request.data.get('campo')
        if campo not in ARCHIVOS_COMITE or not request.FILES.get('archivo'):
            return self._error('Elija el documento y adjunte el archivo.')
        setattr(c, campo, request.FILES['archivo'])
        _hist(c, request, f'Adjunto: {ARCHIVOS_COMITE[campo]}')
        c.updated_by = request.user
        c.save()
        return self._respuesta(c)
    adjuntar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def miembro(self, request, pk=None):
        """Agrega o corrige un miembro. Body: {id?, trabajador, representacion, condicion, cargo, fecha_alta}"""
        from organizacion.models import Trabajador
        c = self.get_object()
        m = c.miembros.filter(pk=request.data.get('id'), is_active=True, fecha_baja__isnull=True).first() \
            if request.data.get('id') else None
        t = Trabajador.objects.filter(pk=request.data.get('trabajador') or (m.trabajador_id if m else None),
                                      is_active=True, estado='activo').first()
        if not t:
            return self._error('Elija un trabajador activo.')
        if c.miembros.filter(trabajador=t, is_active=True, fecha_baja__isnull=True).exclude(pk=getattr(m, 'pk', None)) \
                .exists():
            return self._error(f'{t.nombre_completo} ya es miembro del comité.')
        datos = {k: request.data.get(k) for k in ('representacion', 'condicion', 'cargo') if request.data.get(k)}
        for k, opciones in (('representacion', REPRESENTACION), ('condicion', CONDICION), ('cargo', CARGOS_COMITE)):
            if k in datos and datos[k] not in dict(opciones):
                return self._error('Valor no válido.')
        if not m and 'representacion' not in datos:
            return self._error('Indique a quién representa (empleador o trabajadores).')
        cargo = datos.get('cargo') or (m.cargo if m else 'miembro')
        if cargo in ('presidente', 'secretario') and c.miembros.filter(cargo=cargo, is_active=True,
                                                                       fecha_baja__isnull=True) \
                .exclude(pk=getattr(m, 'pk', None)).exists():
            return self._error(f'El comité ya tiene {dict(CARGOS_COMITE)[cargo].lower()}: cambie primero su cargo.')
        if cargo in ('presidente', 'secretario') and (datos.get('condicion') or getattr(m, 'condicion', 'titular')) \
                != 'titular':
            return self._error('El presidente y el secretario se eligen entre los miembros titulares.')
        m = m or MiembroComite(comite=c, created_by=request.user)
        m.trabajador = t
        for k, v in datos.items():
            setattr(m, k, v)
        if request.data.get('fecha_alta'):
            m.fecha_alta = parse_date(str(request.data['fecha_alta'])[:10]) or m.fecha_alta
        m.updated_by = request.user
        m.save()
        _hist(c, request, 'Miembro', trabajador=t.nombre_completo, cargo=m.get_cargo_display(),
              condicion=m.get_condicion_display(), representa=m.get_representacion_display())
        c.save(update_fields=['historial'])
        return self._respuesta(c)
    miembro.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def baja_miembro(self, request, pk=None):
        c = self.get_object()
        m = c.miembros.filter(pk=request.data.get('id'), is_active=True, fecha_baja__isnull=True).first()
        if not m:
            return self._error('Miembro no encontrado.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la baja (renuncia, cese, reemplazo por el suplente…).')
        m.fecha_baja = parse_date(str(request.data.get('fecha') or '')[:10]) or timezone.localdate()
        m.motivo_baja = motivo
        m.updated_by = request.user
        m.save()
        _hist(c, request, 'Baja de miembro', trabajador=m.trabajador.nombre_completo, motivo=motivo)
        c.save(update_fields=['historial'])
        return self._respuesta(c)
    baja_miembro.operacion = 'editar'


class ReunionViewSet(_Base, viewsets.ModelViewSet):
    """Reunión: programada (agenda, asistentes, acuerdos) → realizada con el acta firmada adjunta."""
    queryset = ReunionComite.objects.filter(is_active=True).select_related('comite').prefetch_related('asistentes')
    serializer_class = ReunionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('comite'):
            qs = qs.filter(comite_id=p['comite'])
        if p.get('anio'):
            qs = qs.filter(fecha__year=p['anio'])
        return qs

    def _respuesta(self, r, codigo=status.HTTP_200_OK):
        return Response(ReunionSerializer(ReunionComite.objects.get(pk=r.pk)).data, status=codigo)

    def perform_create(self, serializer):
        r = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(r, self.request, 'Programación')
        r.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        r = self.get_object()
        if r.estado != 'programada':
            return self._error(f'La reunión está {r.get_estado_display().lower()}: el acta ya no se modifica.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return self._error('Una reunión no se elimina: si no se realizó, se cancela con motivo.')

    @action(detail=True, methods=['post'])
    def acuerdo(self, request, pk=None):
        """Agrega o corrige un acuerdo (antes de cerrar el acta). Body: {id?, descripcion, responsable, plazo}"""
        from organizacion.models import Trabajador
        r = self.get_object()
        if r.estado != 'programada':
            return self._error('Los acuerdos se registran antes de cerrar el acta.')
        a = r.acuerdos.filter(pk=request.data.get('id'), is_active=True).first() if request.data.get('id') else None
        desc = (request.data.get('descripcion') or (a.descripcion if a else '')).strip()
        if not desc:
            return self._error('Describa el acuerdo.')
        a = a or AcuerdoComite(reunion=r, orden=r.acuerdos.filter(is_active=True).count() + 1,
                               created_by=request.user)
        a.descripcion = desc
        if 'responsable' in request.data:
            a.responsable = Trabajador.objects.filter(pk=request.data.get('responsable'), is_active=True).first() \
                if request.data.get('responsable') else None
        if 'plazo' in request.data:
            a.plazo = parse_date(str(request.data.get('plazo') or '')[:10])
        a.updated_by = request.user
        a.save()
        return self._respuesta(r)
    acuerdo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_acuerdo(self, request, pk=None):
        r = self.get_object()
        if r.estado != 'programada':
            return self._error('El acta ya está cerrada.')
        a = r.acuerdos.filter(pk=request.data.get('id'), is_active=True).first()
        if not a:
            return self._error('Acuerdo no encontrado.')
        a.is_active = False
        a.save(update_fields=['is_active'])
        return self._respuesta(r)
    quitar_acuerdo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """Registra la reunión como realizada con el acta firmada (multipart: {acta})."""
        r = self.get_object()
        if r.estado != 'programada':
            return self._error('La reunión ya fue cerrada o cancelada.')
        falta = []
        if not r.agenda:
            falta.append('la agenda')
        q = r.quorum()
        if not q['hay_quorum']:
            falta.append(f'el quórum (asisten {q["presentes"]} titular(es); se requieren {q["requerido"]})')
        if not request.FILES.get('acta'):
            falta.append('el acta firmada (adjunta)')
        if falta:
            return self._error('Para cerrar la reunión falta ' + ', '.join(falta) + '.')
        r.acta_firmada = request.FILES['acta']
        r.estado = 'realizada'
        _hist(r, request, 'Acta firmada adjunta: reunión realizada')
        r.updated_by = request.user
        r.save()
        return self._respuesta(r)
    cerrar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        r = self.get_object()
        if r.estado != 'programada':
            return self._error('Solo se cancela una reunión programada.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo.')
        r.estado, r.motivo_cancelacion = 'cancelada', motivo
        _hist(r, request, 'Cancelación', motivo=motivo)
        r.save()
        return self._respuesta(r)
    cancelar.operacion = 'eliminar'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf_comite import generar_acta_pdf
        r = self.get_object()
        return self._pdf(generar_acta_pdf(r), f'Acta {r.codigo}')
    pdf.operacion = 'leer'


class AcuerdoViewSet(_Base, viewsets.ReadOnlyModelViewSet):
    """Acuerdos del comité y su seguimiento mensual."""
    queryset = AcuerdoComite.objects.filter(is_active=True, reunion__is_active=True,
                                            reunion__estado='realizada').select_related('responsable', 'reunion')
    serializer_class = AcuerdoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('comite'):
            qs = qs.filter(reunion__comite_id=p['comite'])
        if p.get('abiertos') == '1':
            qs = qs.filter(estado__in=['pendiente', 'en_proceso'])
        return qs

    @action(detail=True, methods=['post'])
    def seguimiento(self, request, pk=None):
        """Body: {estado, comentario, fecha_cumplimiento}"""
        a = self.get_object()
        est = request.data.get('estado')
        if est not in dict(ESTADOS_ACUERDO):
            return self._error('Indique el estado del acuerdo.')
        coment = (request.data.get('comentario') or '').strip()
        if not coment:
            return self._error('Describa el avance o la evidencia.')
        a.estado = est
        if est == 'cumplido':
            a.fecha_cumplimiento = parse_date(str(request.data.get('fecha_cumplimiento') or '')[:10]) \
                or timezone.localdate()
        a.seguimiento = list(a.seguimiento or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                      'usuario': _nombre(request.user), 'estado': a.get_estado_display(),
                                                      'comentario': coment}]
        a.updated_by = request.user
        a.save()
        return Response(AcuerdoSerializer(a).data)
    seguimiento.operacion = 'editar'


# ============================================================================ programa SSOMA
class ProgramaSSOMAViewSet(_Base, viewsets.ModelViewSet):
    queryset = ProgramaSSOMA.objects.all()
    serializer_class = ProgramaSerializer

    def _respuesta(self, p, codigo=status.HTTP_200_OK):
        return Response(ProgramaSerializer(ProgramaSSOMA.objects.get(pk=p.pk)).data, status=codigo)

    def perform_create(self, serializer):
        p = serializer.save(created_by=self.request.user, updated_by=self.request.user,
                            fecha=timezone.localdate(), elaborado=_firma(self.request))
        _hist(p, self.request, 'Creación')
        p.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        p = self.get_object()
        if p.estado == 'aprobado':
            return self._error('El programa está aprobado: para cambiarlo, inicie una reprogramación.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user, fecha_actualizacion=timezone.localdate())

    def destroy(self, request, *args, **kwargs):
        return self._error('El programa anual no se elimina.')

    @action(detail=False, methods=['get'])
    def anio(self, request):
        a = int(request.query_params.get('anio') or timezone.localdate().year)
        p = ProgramaSSOMA.objects.filter(anio=a).first()
        return Response(ProgramaSerializer(p).data if p else None)
    anio.operacion = 'leer'

    def _editable(self, p):
        if p.estado == 'aprobado':
            return self._error('El programa está aprobado: lo programado no se modifica (inicie una reprogramación).')
        return None

    @action(detail=True, methods=['post'])
    def objetivo(self, request, pk=None):
        """Body: {id?, codigo, descripcion}"""
        p = self.get_object()
        error = self._editable(p)
        if error:
            return error
        o = p.objetivos.filter(pk=request.data.get('id'), is_active=True).first() if request.data.get('id') else None
        cod, desc = (request.data.get('codigo') or '').strip(), (request.data.get('descripcion') or '').strip()
        if not cod or not desc:
            return self._error('Indique el código y el objetivo.')
        o = o or ObjetivoSSOMA(programa=p, orden=p.objetivos.count() + 1, created_by=request.user)
        o.codigo, o.descripcion, o.updated_by = cod, desc, request.user
        o.save()
        return self._respuesta(p)
    objetivo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def actividad(self, request, pk=None):
        """Agrega o corrige una actividad. Body: {id?, objetivo, descripcion, indicador, meta, responsable, area, meses}"""
        p = self.get_object()
        error = self._editable(p)
        if error:
            return error
        a = p.actividades.filter(pk=request.data.get('id'), is_active=True).first() if request.data.get('id') else None
        datos = {k: v for k, v in request.data.items() if k != 'id'}
        if not a and 'orden' not in datos:
            datos['orden'] = p.actividades.filter(is_active=True).count() + 1
        ser = ActividadSerializer(a, data=datos, partial=bool(a))
        ser.is_valid(raise_exception=True)
        if ser.validated_data.get('objetivo') and ser.validated_data['objetivo'].programa_id != p.pk:
            return self._error('Objetivo no válido.')
        if a:
            ser.save(updated_by=request.user)
        else:
            ser.save(programa=p, created_by=request.user, updated_by=request.user)
        return self._respuesta(p)
    actividad.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_actividad(self, request, pk=None):
        p = self.get_object()
        error = self._editable(p)
        if error:
            return error
        a = p.actividades.filter(pk=request.data.get('id'), is_active=True).first()
        if not a:
            return self._error('Actividad no encontrada.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo.')
        a.is_active = False
        a.save(update_fields=['is_active'])
        _hist(p, request, 'Actividad retirada', actividad=a.descripcion[:100], motivo=motivo)
        p.save(update_fields=['historial'])
        return self._respuesta(p)
    quitar_actividad.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def ejecutar(self, request, pk=None):
        """Marca un mes programado como ejecutado (o lo desmarca) con su evidencia.
        Body: {actividad, mes, ejecutado, evidencia}"""
        p = self.get_object()
        if p.estado != 'aprobado':
            return self._error('La ejecución se registra sobre el programa aprobado.')
        a = p.actividades.filter(pk=request.data.get('actividad'), is_active=True).first()
        if not a:
            return self._error('Actividad no encontrada.')
        try:
            mes = int(request.data.get('mes'))
        except (TypeError, ValueError):
            return self._error('Mes no válido.')
        if mes not in (a.meses or []):
            return self._error('Ese mes no está programado para la actividad.')
        hoy = timezone.localdate()
        if (p.anio, mes) > (hoy.year, hoy.month):
            return self._error('No se registra la ejecución de un mes futuro.')
        ejecutado = request.data.get('ejecutado') in (True, 'true', '1', 1)
        evid = (request.data.get('evidencia') or '').strip()
        if ejecutado and not evid:
            return self._error('Indique la evidencia de la ejecución (registro, acta, informe…).')
        ej = set(a.meses_ejecutados or [])
        ev = dict(a.evidencias or {})
        if ejecutado:
            ej.add(mes)
            ev[str(mes)] = evid
        else:
            ej.discard(mes)
            ev.pop(str(mes), None)
        a.meses_ejecutados, a.evidencias = sorted(ej), ev
        a.updated_by = request.user
        a.save()
        p.fecha_actualizacion = hoy
        _hist(p, request, 'Ejecución' if ejecutado else 'Ejecución anulada', actividad=a.descripcion[:80], mes=mes)
        p.save(update_fields=['historial', 'fecha_actualizacion'])
        return self._respuesta(p)
    ejecutar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        """Aprueba el programa (o su reprogramación) con firma. Body: {password, reunion?}"""
        p = self.get_object()
        if p.estado == 'aprobado':
            return self._error('El programa ya está aprobado.')
        acts = list(p.actividades.filter(is_active=True))
        if not acts:
            return self._error('Registre al menos una actividad.')
        sin_meses = [a for a in acts if not a.meses]
        if sin_meses:
            return self._error(f'Programe los meses de «{sin_meses[0].descripcion[:80]}».')
        sin_resp = [a for a in acts if not a.responsable_id]
        if sin_resp:
            return self._error(f'Indique el responsable de «{sin_resp[0].descripcion[:80]}».')
        error = self._clave(request, 'el programa')
        if error:
            return error
        if request.data.get('reunion'):
            p.reunion_aprobacion = ReunionComite.objects.filter(pk=request.data['reunion'], is_active=True).first()
        p.aprobado = list(p.aprobado or []) + [_firma(request)]
        p.estado, p.fecha_actualizacion = 'aprobado', timezone.localdate()
        _hist(p, request, f'Aprobación (versión {p.version})')
        p.updated_by = request.user
        p.save()
        return self._respuesta(p)
    aprobar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def reprogramar(self, request, pk=None):
        """Abre una nueva versión para cambiar lo programado. Body: {motivo}"""
        p = self.get_object()
        if p.estado != 'aprobado':
            return self._error('Solo se reprograma un programa aprobado.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la reprogramación.')
        foto = [{'actividad': a.descripcion[:120], 'meses': a.meses, 'responsable': a.responsable.nombre
                 if a.responsable_id else ''} for a in p.actividades.filter(is_active=True).select_related('responsable')]
        p.version += 1
        p.estado = 'reprogramacion'
        _hist(p, request, f'Reprogramación (versión {p.version})', motivo=motivo, programado_anterior=foto)
        p.updated_by = request.user
        p.save()
        return self._respuesta(p)
    reprogramar.operacion = 'editar'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf_comite import generar_programa_ssoma_pdf
        p = self.get_object()
        return self._pdf(generar_programa_ssoma_pdf(p), f'Programa anual SSOMA {p.anio}')
    pdf.operacion = 'leer'

