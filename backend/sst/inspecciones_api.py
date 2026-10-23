"""API de inspecciones de SST (inventario, plantillas, inspecciones) y monitoreos de agentes."""
from datetime import date

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .eventos_api import _Base, _firma, _hist, _nombre
from .inspecciones import (AGENTES_MONITOREO, ESCALAS, ESTADOS_RECOMENDACION, FRECUENCIAS,
                           MESES_FRECUENCIA, TIPOS_ELEMENTO, TIPOS_INSPECCION, ElementoSeguridad, Inspeccion,
                           ItemInspeccion, Monitoreo, MonitoreoProgramado, PlantillaInspeccion, ProgramaMonitoreo,
                           RecomendacionMonitoreo, estado_fecha)

TIPOS_CONTENIDO = ('botiquin', 'kit_antiderrame')
TIPOS_VEHICULO = ('vehiculo', 'moto')


def _fecha(valor):
    if not valor:
        return None
    return valor if isinstance(valor, date) else parse_date(str(valor)[:10])


def _trabajadores_activos():
    from organizacion.models import Trabajador
    return Trabajador.objects.filter(is_active=True, estado='activo')


def _datos_elemento(e):
    """Columnas descriptivas del elemento, como las imprime el formato de su tipo."""
    f = lambda d: d.isoformat() if d else ''  # noqa: E731
    if e.tipo == 'extintor':
        return {'Ubicación': e.ubicacion, 'N° de extintor': e.codigo, 'Tipo de extintor': e.subtipo,
                'Capacidad': e.capacidad, 'Fecha de fabricación': f(e.fecha_fabricacion),
                'Fecha de prueba hidrostática': f(e.fecha_prueba_hidrostatica),
                'Fecha de vencimiento': f(e.fecha_vencimiento)}
    if e.tipo == 'escalera':
        return {'Ubicación': e.ubicacion, 'Tipo': e.subtipo, 'Código': e.codigo}
    if e.tipo in TIPOS_VEHICULO:
        return {'Placa': e.placa or e.codigo, 'Marca': e.marca, 'Tipo de combustible': e.combustible}
    return {'Ubicación': e.ubicacion, 'Piso': e.piso, 'Código': e.codigo}


def _valores_escala(escala):
    return [v for v, _ in ESCALAS.get(escala or 'c_nc_na', ESCALAS['c_nc_na'])['valores']]


# ============================================================================ serializers
class ElementoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True, default=None)
    vencimientos = serializers.SerializerMethodField()
    ultima_inspeccion = serializers.SerializerMethodField()

    class Meta:
        model = ElementoSeguridad
        fields = ['id', 'tipo', 'tipo_display', 'codigo', 'ubicacion', 'piso', 'area', 'area_nombre', 'subtipo',
                  'marca', 'capacidad', 'fecha_fabricacion', 'fecha_vencimiento', 'fecha_prueba_hidrostatica',
                  'fecha_revision_tecnica', 'placa', 'combustible', 'contenido', 'observaciones', 'motivo_baja',
                  'fecha_baja', 'is_active', 'vencimientos', 'ultima_inspeccion', 'historial']
        read_only_fields = ['motivo_baja', 'fecha_baja', 'is_active', 'historial']

    def get_vencimientos(self, obj):
        return obj.vencimientos()

    def get_ultima_inspeccion(self, obj):
        ins = (Inspeccion.objects.filter(Q(elemento=obj) | Q(items__elemento=obj), is_active=True)
               .exclude(estado__in=['anulada', 'en_registro']).order_by('-fecha').first())
        return {'codigo': ins.codigo, 'fecha': ins.fecha.isoformat()} if ins else None

    def validate_codigo(self, v):
        v = (v or '').strip()
        if not v:
            raise serializers.ValidationError('Indique el código o número del elemento.')
        return v

    def validate_contenido(self, valor):
        if not isinstance(valor or [], list):
            raise serializers.ValidationError('Formato no válido.')
        salida = []
        for c in valor or []:
            producto = (c.get('producto') or '').strip() if isinstance(c, dict) else ''
            if not producto:
                continue
            venc = _fecha(c.get('vencimiento'))
            salida.append({'producto': producto, 'cantidad': c.get('cantidad') or '',
                           'unidad': (c.get('unidad') or '').strip(), 'vencimiento': venc.isoformat() if venc else ''})
        return salida

    def validate(self, data):
        tipo = data.get('tipo') or getattr(self.instance, 'tipo', None)
        codigo = data.get('codigo') or getattr(self.instance, 'codigo', None)
        qs = ElementoSeguridad.objects.filter(tipo=tipo, codigo__iexact=codigo)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({'codigo': ['Ya existe un elemento de ese tipo con ese código.']})
        if tipo in TIPOS_VEHICULO and not (data.get('placa') or getattr(self.instance, 'placa', '')):
            data['placa'] = codigo
        return data


# Nombres en pantalla del «tipo de lista» de una plantilla, con su explicación (el modelo guarda la clave).
TIPOS_LISTA = [
    ('elementos', 'Lista de equipos', 'Cada fila es un equipo del inventario (extintor, luz, escalera…) evaluado con '
                                      'los criterios en columnas.'),
    ('contenido', 'Contenido de un equipo', 'Cada fila es un producto que debe haber dentro del equipo (botiquín, kit '
                                            'antiderrame), con su cantidad.'),
    ('preguntas', 'Lista de preguntas', 'Cada fila es una pregunta de verificación, agrupada por secciones.'),
    ('trabajadores', 'Lista de trabajadores', 'Cada fila es un trabajador del área, evaluado con los mismos criterios.'),
]
NOMBRE_TIPO_LISTA = {k: n for k, n, _ in TIPOS_LISTA}


class PlantillaSerializer(serializers.ModelSerializer):
    familia_display = serializers.SerializerMethodField()
    tipo_elemento_display = serializers.CharField(source='get_tipo_elemento_display', read_only=True)
    frecuencia_display = serializers.CharField(source='get_frecuencia_display', read_only=True)
    escala_display = serializers.CharField(source='get_escala_display', read_only=True)
    valores_escala = serializers.SerializerMethodField()
    total_inspecciones = serializers.SerializerMethodField()

    def get_familia_display(self, obj):
        return NOMBRE_TIPO_LISTA.get(obj.familia, obj.familia)

    class Meta:
        model = PlantillaInspeccion
        fields = ['id', 'nombre', 'codigo_formato', 'familia', 'familia_display', 'tipo_elemento',
                  'tipo_elemento_display', 'escala', 'escala_display', 'valores_escala', 'criterios', 'columnas_datos',
                  'secciones', 'contenido_base', 'frecuencia', 'frecuencia_display', 'objetivo', 'nota',
                  'version_formato', 'fecha_formato', 'elaborado', 'revisado', 'aprobado', 'is_active',
                  'total_inspecciones', 'historial']
        read_only_fields = ['is_active', 'historial']

    def get_valores_escala(self, obj):
        return ESCALAS.get(obj.escala, ESCALAS['c_nc_na'])['valores']

    def get_total_inspecciones(self, obj):
        return obj.inspecciones.filter(is_active=True).exclude(estado='anulada').count()

    def validate_nombre(self, v):
        v = (v or '').strip()
        qs = PlantillaInspeccion.objects.all()
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if any(p.nombre.casefold() == v.casefold() for p in qs):
            raise serializers.ValidationError('Ya existe una plantilla con ese nombre.')
        return v

    def validate(self, data):
        g = lambda k: data.get(k, getattr(self.instance, k, None))  # noqa: E731
        familia, tipo = g('familia'), g('tipo_elemento') or ''
        if familia == 'contenido' and tipo not in TIPOS_CONTENIDO:
            raise serializers.ValidationError({'tipo_elemento': ['La inspección de contenido es de un botiquín o un '
                                                                 'kit antiderrame.']})
        if familia == 'elementos' and tipo in TIPOS_CONTENIDO + TIPOS_VEHICULO:
            raise serializers.ValidationError({'tipo_elemento': ['Para botiquines y kits use la familia «contenido»; '
                                                                 'para vehículos, «por preguntas».']})
        if familia in ('elementos', 'trabajadores'):
            crit = [c for c in (g('criterios') or []) if isinstance(c, dict) and (c.get('nombre') or '').strip()]
            if not crit:
                raise serializers.ValidationError({'criterios': ['Registre al menos un criterio (columna).']})
            data['criterios'] = [{'grupo': (c.get('grupo') or '').strip(), 'nombre': c['nombre'].strip(),
                                  'invertido': bool(c.get('invertido'))} for c in crit]
            if familia == 'elementos' and not tipo and not [x for x in (g('columnas_datos') or []) if str(x).strip()]:
                raise serializers.ValidationError({'columnas_datos': [
                    'Sin elementos del inventario, indique las columnas que describen cada fila '
                    '(p. ej. Cantidad, Tipo de herramienta).']})
        if familia == 'preguntas':
            secc = []
            for s in g('secciones') or []:
                preguntas = [str(p).strip() for p in (s.get('preguntas') or []) if str(p).strip()]
                if (s.get('titulo') or '').strip() and preguntas:
                    secc.append({'titulo': s['titulo'].strip(), 'preguntas': preguntas})
            if not secc:
                raise serializers.ValidationError({'secciones': ['Registre al menos una sección con sus preguntas.']})
            data['secciones'] = secc
        if 'columnas_datos' in data:
            data['columnas_datos'] = [str(x).strip() for x in data['columnas_datos'] or [] if str(x).strip()]
        return data


class ItemSerializer(serializers.ModelSerializer):
    elemento_codigo = serializers.CharField(source='elemento.codigo', read_only=True, default=None)
    trabajador_nombre = serializers.CharField(source='trabajador.nombre_completo', read_only=True, default=None)
    responsable_accion_nombre = serializers.SerializerMethodField()
    hallazgo_codigo = serializers.CharField(source='hallazgo.codigo', read_only=True, default=None)
    evidencia_url = serializers.SerializerMethodField()
    accion_vencida = serializers.SerializerMethodField()

    class Meta:
        model = ItemInspeccion
        fields = ['id', 'orden', 'seccion', 'texto', 'elemento', 'elemento_codigo', 'trabajador', 'trabajador_nombre',
                  'datos', 'resultados', 'observacion', 'no_conforme', 'accion', 'responsable_accion',
                  'responsable_accion_nombre', 'plazo_accion', 'accion_completada', 'fecha_accion_completada',
                  'seguimiento_accion', 'evidencia_url', 'hallazgo', 'hallazgo_codigo', 'accion_vencida']

    def get_responsable_accion_nombre(self, obj):
        return _nombre(obj.responsable_accion) if obj.responsable_accion_id else None

    def get_evidencia_url(self, obj):
        return obj.evidencia_accion.url if obj.evidencia_accion else None

    def get_accion_vencida(self, obj):
        return bool(obj.no_conforme and not obj.accion_completada and obj.plazo_accion
                    and obj.plazo_accion < timezone.localdate())


class InspeccionListaSerializer(serializers.ModelSerializer):
    plantilla_nombre = serializers.CharField(source='plantilla.nombre', read_only=True)
    familia = serializers.CharField(source='plantilla.familia', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True, default=None)
    elemento_codigo = serializers.CharField(source='elemento.codigo', read_only=True, default=None)
    inspector_nombre = serializers.SerializerMethodField()
    resumen = serializers.SerializerMethodField()

    class Meta:
        model = Inspeccion
        fields = ['id', 'codigo', 'plantilla', 'plantilla_nombre', 'familia', 'estado', 'estado_display', 'fecha',
                  'area', 'area_nombre', 'lugar', 'elemento', 'elemento_codigo', 'inspector_nombre', 'resumen']

    def get_inspector_nombre(self, obj):
        return _nombre(obj.inspector) if obj.inspector_id else None

    def get_resumen(self, obj):
        items = [i for i in obj.items.all() if i.is_active]
        nc = [i for i in items if i.no_conforme]
        hoy = timezone.localdate()
        return {'items': len(items), 'no_conformes': len(nc),
                'acciones_pendientes': sum(1 for i in nc if not i.accion_completada),
                'acciones_vencidas': sum(1 for i in nc if not i.accion_completada and i.plazo_accion
                                         and i.plazo_accion < hoy)}


class InspeccionSerializer(InspeccionListaSerializer):
    tipo_inspeccion_display = serializers.CharField(source='get_tipo_inspeccion_display', read_only=True)
    responsable_area_nombre = serializers.CharField(source='responsable_area.nombre_completo', read_only=True,
                                                    default=None)
    conductor_nombre = serializers.CharField(source='conductor.nombre_completo', read_only=True, default=None)
    items = serializers.SerializerMethodField()
    valores_escala = serializers.SerializerMethodField()
    etapas_abiertas = serializers.SerializerMethodField()

    class Meta:
        model = Inspeccion
        fields = InspeccionListaSerializer.Meta.fields + [
            'estructura', 'hora', 'tipo_inspeccion', 'tipo_inspeccion_display', 'tipo_detalle', 'responsable_area',
            'responsable_area_nombre', 'objetivo', 'n_trabajadores', 'conductor', 'conductor_nombre', 'km', 'inspector',
            'conclusiones', 'firma_registro', 'fecha_cierre', 'motivo_anulacion', 'historial', 'items',
            'valores_escala', 'etapas_abiertas']
        read_only_fields = ['codigo', 'estructura', 'estado', 'firma_registro', 'fecha_cierre', 'motivo_anulacion',
                            'historial']

    def get_items(self, obj):
        return ItemSerializer(obj.items.filter(is_active=True).select_related(
            'elemento', 'trabajador', 'responsable_accion', 'hallazgo'), many=True).data

    def get_valores_escala(self, obj):
        return ESCALAS.get(obj.estructura.get('escala') or 'c_nc_na', ESCALAS['c_nc_na'])['valores']

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas()


class ProgramadoSerializer(serializers.ModelSerializer):
    agente_display = serializers.CharField(source='get_agente_display', read_only=True)
    frecuencia_display = serializers.CharField(source='get_frecuencia_display', read_only=True)
    meses_ejecutados = serializers.SerializerMethodField()
    nombre = serializers.CharField(read_only=True)

    class Meta:
        model = MonitoreoProgramado
        fields = ['id', 'programa', 'orden', 'agente', 'agente_display', 'detalle', 'nombre', 'fecha_programada',
                  'frecuencia', 'frecuencia_display', 'meses', 'meses_ejecutados', 'filas_iperc', 'comentarios']

    def get_meses_ejecutados(self, obj):
        return obj.meses_ejecutados()

    def validate_meses(self, v):
        v = sorted({int(m) for m in v or [] if str(m).isdigit() and 1 <= int(m) <= 12})
        return v

    def validate(self, data):
        f = data.get('fecha_programada')
        meses = data.get('meses', getattr(self.instance, 'meses', None))
        if f and not meses:
            data['meses'] = [f.month]
        elif not f and not meses and not self.instance:
            raise serializers.ValidationError({'meses': ['Indique la fecha programada o los meses del monitoreo.']})
        return data


class MonitoreoSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    frecuencia_display = serializers.CharField(source='get_frecuencia_display', read_only=True)
    programados_info = serializers.SerializerMethodField()
    informe_url = serializers.SerializerMethodField()
    con_desviaciones = serializers.BooleanField(read_only=True)
    total_recomendaciones = serializers.SerializerMethodField()

    class Meta:
        model = Monitoreo
        fields = ['id', 'codigo', 'estado', 'estado_display', 'programados', 'programados_info', 'area_monitoreada',
                  'fecha', 'frecuencia', 'frecuencia_display', 'tipo_riesgo', 'n_expuestos', 'organizacion',
                  'resultados', 'causas_desviacion', 'conclusiones', 'informe_url', 'firma_registro',
                  'motivo_anulacion', 'historial', 'con_desviaciones', 'total_recomendaciones']
        read_only_fields = ['codigo', 'estado', 'firma_registro', 'motivo_anulacion', 'historial']

    def get_programados_info(self, obj):
        return [{'id': p.pk, 'nombre': p.nombre, 'anio': p.programa.anio} for p in obj.programados.all()]

    def get_informe_url(self, obj):
        return obj.informe.url if obj.informe else None

    def get_total_recomendaciones(self, obj):
        return obj.recomendaciones.filter(is_active=True).count()

    def validate_resultados(self, valor):
        salida = []
        for r in valor or []:
            if not isinstance(r, dict) or not (r.get('agente') or '').strip():
                continue
            d = r.get('dentro_lmp')
            salida.append({'agente': r['agente'].strip(), 'resultado': (r.get('resultado') or '').strip(),
                           'valor': (str(r.get('valor') or '')).strip(), 'lmp': (str(r.get('lmp') or '')).strip(),
                           'dentro_lmp': d if d in (True, False) else None})
        return salida


class RecomendacionSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    monitoreo_codigo = serializers.CharField(source='monitoreo.codigo', read_only=True, default=None)
    vencida = serializers.BooleanField(read_only=True)

    class Meta:
        model = RecomendacionMonitoreo
        fields = ['id', 'anio', 'monitoreo', 'monitoreo_codigo', 'orden', 'agente', 'actividad', 'fecha_programada',
                  'programacion', 'meses', 'meses_ejecutados', 'responsable', 'responsable_nombre', 'estado',
                  'estado_display', 'fecha_ejecucion', 'observaciones', 'vencida', 'historial']
        read_only_fields = ['historial']

    def get_responsable_nombre(self, obj):
        return _nombre(obj.responsable) if obj.responsable_id else None

    def validate(self, data):
        for k in ('meses', 'meses_ejecutados'):
            if k in data:
                data[k] = sorted({int(m) for m in data[k] or [] if str(m).isdigit() and 1 <= int(m) <= 12})
        f = data.get('fecha_programada')
        if f and not data.get('meses') and not getattr(self.instance, 'meses', None):
            data['meses'] = [f.month]
        if not self.instance and not f and not (data.get('programacion') or '').strip():
            raise serializers.ValidationError({'fecha_programada': ['Indique la fecha programada o la frecuencia.']})
        return data


# ============================================================================ inventario
class ElementoViewSet(_Base, viewsets.ModelViewSet):
    """Inventario de elementos de seguridad y vehículos, con sus vencimientos."""
    queryset = ElementoSeguridad.objects.all().select_related('area')
    serializer_class = ElementoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('tipo'):
            qs = qs.filter(tipo=p['tipo'])
        if p.get('bajas') != '1' and self.action == 'list':
            qs = qs.filter(is_active=True)
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(ubicacion__icontains=b) | Q(placa__icontains=b))
        return qs

    def perform_create(self, serializer):
        e = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(e, self.request, 'Registro')
        e.save(update_fields=['historial'])

    def perform_update(self, serializer):
        antes = ElementoSerializer(serializer.instance).data
        e = serializer.save(updated_by=self.request.user)
        cambios = [ElementoSeguridad._meta.get_field(k).verbose_name for k in serializer.validated_data
                   if str(antes.get(k)) != str(ElementoSerializer(e).data.get(k))]
        if cambios:
            _hist(e, self.request, 'Actualización', campos=', '.join(cambios))
            e.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        if not self.get_object().is_active:
            return self._error('El elemento está dado de baja.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return self._error('Un elemento no se elimina: se da de baja con motivo.')

    @action(detail=True, methods=['post'])
    def dar_baja(self, request, pk=None):
        e = self.get_object()
        motivo = (request.data.get('motivo') or '').strip()
        if not e.is_active:
            return self._error('El elemento ya está dado de baja.')
        if not motivo:
            return self._error('Indique el motivo de la baja.')
        e.is_active, e.motivo_baja, e.fecha_baja = False, motivo, timezone.localdate()
        _hist(e, request, 'Baja', motivo=motivo)
        e.updated_by = request.user
        e.save()
        return Response(ElementoSerializer(e).data)
    dar_baja.operacion = 'eliminar'

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'tipos': TIPOS_ELEMENTO, 'familias': TIPOS_LISTA, 'frecuencias': FRECUENCIAS,
                         'escalas': [(k, v['nombre'], v['valores']) for k, v in ESCALAS.items()],
                         'tipos_inspeccion': TIPOS_INSPECCION, 'agentes': AGENTES_MONITOREO,
                         'estados_recomendacion': ESTADOS_RECOMENDACION})
    catalogos.operacion = 'leer'


class PlantillaViewSet(_Base, viewsets.ModelViewSet):
    """Plantillas (formatos) de inspección. Cambiarlas no altera las inspecciones ya hechas."""
    queryset = PlantillaInspeccion.objects.all()
    serializer_class = PlantillaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('inactivas') != '1' and self.action == 'list':
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        p = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(p, self.request, 'Creación')
        p.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        p = serializer.save(updated_by=self.request.user)
        _hist(p, self.request, 'Modificación', campos=', '.join(
            str(PlantillaInspeccion._meta.get_field(k).verbose_name) for k in serializer.validated_data))
        p.save(update_fields=['historial'])

    def destroy(self, request, *args, **kwargs):
        p = self.get_object()
        p.is_active = False
        _hist(p, request, 'Desactivación')
        p.updated_by = request.user
        p.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================================ inspecciones
class InspeccionViewSet(_Base, viewsets.ModelViewSet):
    """Inspección: registro (respuestas, acciones de los no conformes) → firma → acciones → cerrada."""
    queryset = Inspeccion.objects.all().select_related('plantilla', 'area', 'elemento', 'inspector',
                                                       'responsable_area', 'conductor').prefetch_related('items')

    def get_serializer_class(self):
        return InspeccionListaSerializer if self.action == 'list' else InspeccionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list':
            qs = qs.filter(is_active=True)
        for campo in ('plantilla', 'estado', 'area', 'elemento'):
            if p.get(campo):
                qs = qs.filter(**{campo: p[campo]})
        if p.get('anio'):
            qs = qs.filter(fecha__year=p['anio'])
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(plantilla__nombre__icontains=b) | Q(lugar__icontains=b))
        return qs

    def _respuesta(self, i, codigo=status.HTTP_200_OK):
        return Response(InspeccionSerializer(Inspeccion.objects.get(pk=i.pk)).data, status=codigo)

    def create(self, request, *args, **kwargs):
        """Body: {plantilla, fecha, …, elemento (contenido / vehículo), elementos: [ids], trabajadores: [ids]}"""
        pl = PlantillaInspeccion.objects.filter(pk=request.data.get('plantilla'), is_active=True).first()
        if not pl:
            return self._error('Elija la plantilla de la inspección.')
        elemento = None
        if request.data.get('elemento'):
            elemento = ElementoSeguridad.objects.filter(pk=request.data['elemento'], is_active=True).first()
        if pl.familia == 'contenido' and (not elemento or elemento.tipo != pl.tipo_elemento):
            return self._error(f'Elija el {dict(TIPOS_ELEMENTO)[pl.tipo_elemento].lower()} que se inspecciona.')
        if pl.familia == 'preguntas' and pl.tipo_elemento in TIPOS_VEHICULO and (
                not elemento or elemento.tipo != pl.tipo_elemento):
            return self._error('Elija el vehículo que se inspecciona.')
        ser = InspeccionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        datos = dict(ser.validated_data)
        for k in ('plantilla', 'elemento'):
            datos.pop(k, None)
        if datos.get('n_trabajadores') is None:
            datos['n_trabajadores'] = _trabajadores_activos().filter(puesto__tipo='propio').count() or None
        ins = Inspeccion.objects.create(plantilla=pl, estructura=pl.estructura(), elemento=elemento,
                                        objetivo=datos.pop('objetivo', '') or pl.objetivo,
                                        inspector=datos.pop('inspector', None) or request.user,
                                        created_by=request.user, updated_by=request.user, **datos)
        self._generar_items(ins, request)
        _hist(ins, request, 'Registro')
        ins.save(update_fields=['historial'])
        return self._respuesta(ins, status.HTTP_201_CREATED)

    def _generar_items(self, ins, request):
        pl, u = ins.plantilla, request.user
        crear = lambda orden, **kw: ItemInspeccion.objects.create(  # noqa: E731
            inspeccion=ins, orden=orden, created_by=u, updated_by=u, **kw)
        if pl.familia == 'elementos' and pl.tipo_elemento:
            ids = request.data.get('elementos') or []
            qs = ElementoSeguridad.objects.filter(tipo=pl.tipo_elemento, is_active=True)
            if ids:
                qs = qs.filter(pk__in=ids)
            elif ins.area_id:
                qs = qs.filter(area_id=ins.area_id) if qs.filter(area_id=ins.area_id).exists() else qs
            for n, e in enumerate(qs.order_by('piso', 'codigo'), 1):
                crear(n, elemento=e, texto=str(e), datos=_datos_elemento(e))
        elif pl.familia == 'contenido':
            contenido = ins.elemento.contenido or pl.contenido_base or []
            for n, c in enumerate(contenido, 1):
                crear(n, texto=c.get('producto', ''), datos={'Cantidad': c.get('cantidad', ''),
                                                             'Unidad': c.get('unidad', ''),
                                                             'Vencimiento': c.get('vencimiento', '')})
        elif pl.familia == 'preguntas':
            n = 0
            for s in pl.secciones or []:
                for q in s.get('preguntas') or []:
                    n += 1
                    crear(n, seccion=s.get('titulo', ''), texto=q)
        elif pl.familia == 'trabajadores':
            ids = request.data.get('trabajadores') or []
            qs = _trabajadores_activos().select_related('puesto')
            if ids:
                qs = qs.filter(pk__in=ids)
            elif ins.area_id:
                qs = qs.filter(Q(area_id=ins.area_id) | Q(puesto__area_id=ins.area_id))
            else:
                qs = qs.none()
            for n, t in enumerate(qs.order_by('apellidos', 'nombres'), 1):
                crear(n, trabajador=t, texto=t.nombre_completo, datos={'Puesto': t.puesto.nombre})

    def update(self, request, *args, **kwargs):
        ins = self.get_object()
        if 'registro' not in ins.etapas_abiertas():
            return self._error(f'La inspección está {ins.get_estado_display().lower()}: los datos del registro '
                               'ya no se modifican.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return self._error('Una inspección no se elimina: si se registró por error, se anula con motivo.')

    # --- filas
    def _en_registro(self, ins):
        if ins.estado != 'en_registro':
            return self._error(f'La inspección está {ins.get_estado_display().lower()}: sus filas y respuestas ya '
                               'no se modifican.')
        return None

    @action(detail=True, methods=['post'])
    def agregar_fila(self, request, pk=None):
        """Body: {datos} (fila libre) · {elemento} · {trabajador} · {texto} (producto del botiquín)."""
        ins = self.get_object()
        error = self._en_registro(ins)
        if error:
            return error
        familia = ins.estructura.get('familia')
        orden = (ins.items.order_by('-orden').values_list('orden', flat=True).first() or 0) + 1
        kw = {}
        if request.data.get('elemento'):
            e = ElementoSeguridad.objects.filter(pk=request.data['elemento'], is_active=True,
                                                 tipo=ins.estructura.get('tipo_elemento')).first()
            if not e or familia != 'elementos':
                return self._error('Elemento no válido para esta inspección.')
            if ins.items.filter(elemento=e, is_active=True).exists():
                return self._error(f'{e} ya está en la inspección.')
            kw = {'elemento': e, 'texto': str(e), 'datos': _datos_elemento(e)}
        elif request.data.get('trabajador'):
            t = _trabajadores_activos().filter(pk=request.data['trabajador']).select_related('puesto').first()
            if not t or familia != 'trabajadores':
                return self._error('Trabajador no válido para esta inspección.')
            if ins.items.filter(trabajador=t, is_active=True).exists():
                return self._error(f'{t.nombre_completo} ya está en la inspección.')
            kw = {'trabajador': t, 'texto': t.nombre_completo, 'datos': {'Puesto': t.puesto.nombre}}
        elif familia == 'elementos' and not ins.estructura.get('tipo_elemento'):
            cols = ins.estructura.get('columnas_datos') or []
            datos = {c: str((request.data.get('datos') or {}).get(c) or '').strip() for c in cols}
            if not any(datos.values()):
                return self._error('Describa la fila (' + ', '.join(cols) + ').')
            kw = {'datos': datos, 'texto': ' · '.join(v for v in datos.values() if v)}
        elif familia == 'contenido' and (request.data.get('texto') or '').strip():
            d = request.data.get('datos') or {}
            kw = {'texto': request.data['texto'].strip(),
                  'datos': {'Cantidad': d.get('Cantidad', ''), 'Unidad': d.get('Unidad', ''),
                            'Vencimiento': d.get('Vencimiento', '')}}
        else:
            return self._error('Indique qué fila agregar.')
        ItemInspeccion.objects.create(inspeccion=ins, orden=orden, created_by=request.user, updated_by=request.user,
                                      **kw)
        return self._respuesta(ins, status.HTTP_201_CREATED)
    agregar_fila.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_fila(self, request, pk=None):
        ins = self.get_object()
        error = self._en_registro(ins)
        if error:
            return error
        if ins.estructura.get('familia') == 'preguntas':
            return self._error('Las preguntas de la plantilla no se quitan: responda «No aplica».')
        it = ins.items.filter(pk=request.data.get('item_id'), is_active=True).first()
        if not it:
            return self._error('Fila no encontrada.')
        it.is_active = False
        it.updated_by = request.user
        it.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return self._respuesta(ins)
    quitar_fila.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def responder(self, request, pk=None):
        """Guarda respuestas. Body: {items: [{id, resultados, observacion, datos?, accion, responsable_accion,
        plazo_accion}]}"""
        ins = self.get_object()
        error = self._en_registro(ins)
        if error:
            return error
        validos = _valores_escala(ins.estructura.get('escala'))
        n_crit = len(ins.estructura.get('criterios') or [])
        familia = ins.estructura.get('familia')
        por_id = {i.pk: i for i in ins.items.filter(is_active=True)}
        from core.models import Usuario
        for d in request.data.get('items') or []:
            it = por_id.get(d.get('id'))
            if not it:
                return self._error('Fila no encontrada.')
            if 'resultados' in d:
                res = {}
                for k, v in (d.get('resultados') or {}).items():
                    if v in (None, ''):
                        continue
                    if v not in validos:
                        return self._error(f'Respuesta no válida: «{v}».')
                    if familia in ('elementos', 'trabajadores'):
                        if not str(k).isdigit() or int(k) >= n_crit:
                            return self._error('Criterio no válido.')
                    elif k != 'r':
                        return self._error('Criterio no válido.')
                    res[str(k)] = v
                it.resultados = res
            if 'observacion' in d:
                it.observacion = (d.get('observacion') or '').strip()
            if 'datos' in d and isinstance(d['datos'], dict) and familia == 'contenido':
                it.datos = {**(it.datos or {}), **{k: str(v) for k, v in d['datos'].items()
                                                   if k in ('Cantidad', 'Unidad', 'Vencimiento', 'Cantidad encontrada')}}
            for campo in ('accion', 'plazo_accion', 'responsable_accion'):
                if campo in d:
                    v = d.get(campo)
                    if campo == 'accion':
                        it.accion = (v or '').strip()
                    elif campo == 'plazo_accion':
                        it.plazo_accion = _fecha(v)
                    else:
                        it.responsable_accion = Usuario.objects.filter(pk=v, is_active=True).first() if v else None
            it.updated_by = request.user
            it.save()
        return self._respuesta(ins)
    responder.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def firmar(self, request, pk=None):
        """El responsable del registro firma: todas las filas respondidas y cada no conforme con su acción."""
        ins = self.get_object()
        error = self._en_registro(ins)
        if error:
            return error
        items = list(ins.items.filter(is_active=True))
        if not items:
            return self._error('La inspección no tiene filas que registrar.')
        familia = ins.estructura.get('familia')
        n_crit = len(ins.estructura.get('criterios') or [])
        sin_resp = []
        for it in items:
            claves = {str(k) for k in range(n_crit)} if familia in ('elementos', 'trabajadores') else {'r'}
            if not claves.issubset({k for k, v in (it.resultados or {}).items() if v}):
                sin_resp.append(it)
        if sin_resp:
            return self._error(f'Faltan respuestas en {len(sin_resp)} fila(s) (la primera: '
                               f'«{(sin_resp[0].texto or "fila " + str(sin_resp[0].orden))[:80]}»). '
                               'Use «No aplica» cuando corresponda.')
        sin_accion = [it for it in items if it.no_conforme and (not it.accion.strip() or not it.responsable_accion_id
                                                                 or not it.plazo_accion)]
        if sin_accion:
            return self._error(f'Registre la acción inmediata, el responsable y el plazo de cada «no conforme» '
                               f'({len(sin_accion)} pendiente(s); el primero: «{sin_accion[0].texto[:80]}»).')
        if not ins.inspector_id:
            return self._error('Indique el responsable de la inspección.')
        error = self._clave(request, 'la inspección')
        if error:
            return error
        ins.firma_registro = _firma(request)
        pendientes = [it for it in items if it.no_conforme and not it.accion_completada]
        if pendientes:
            ins.estado = 'con_acciones'
        else:
            ins.estado, ins.fecha_cierre = 'cerrada', timezone.now()
        _hist(ins, request, 'Firma del registro', no_conformes=sum(1 for it in items if it.no_conforme))
        ins.updated_by = request.user
        ins.save()
        return self._respuesta(ins)
    firmar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def completar_accion(self, request, pk=None):
        """Multipart: {item_id, seguimiento, fecha, evidencia}. Con todas completas, la inspección se cierra."""
        ins = self.get_object()
        if ins.estado != 'con_acciones':
            return self._error('Las acciones se completan después de firmar la inspección.')
        it = ins.items.filter(pk=request.data.get('item_id'), is_active=True, no_conforme=True).first()
        if not it:
            return self._error('Ítem no conforme no encontrado.')
        if it.accion_completada:
            return self._error('La acción ya está completada.')
        seg = (request.data.get('seguimiento') or '').strip()
        if not seg:
            return self._error('Describa lo realizado.')
        f = _fecha(request.data.get('fecha')) or timezone.localdate()
        if f > timezone.localdate():
            return self._error('La fecha no puede ser futura.')
        it.seguimiento_accion, it.accion_completada, it.fecha_accion_completada = seg, True, f
        if request.FILES.get('evidencia'):
            it.evidencia_accion = request.FILES['evidencia']
        it.updated_by = request.user
        it.save()
        _hist(ins, request, 'Acción completada', item=it.texto[:80])
        if not ins.items.filter(is_active=True, no_conforme=True, accion_completada=False).exists():
            ins.estado, ins.fecha_cierre = 'cerrada', timezone.now()
            _hist(ins, request, 'Cierre (acciones completas)')
        ins.save()
        return self._respuesta(ins)
    completar_accion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def registrar_hallazgo(self, request, pk=None):
        """Registra un ítem no conforme relevante como hallazgo con su solicitud de acción correctiva.
        Body: {item_id, tipo_nc (nc_mayor / nc_menor)}"""
        from esynapse_sig.models import Hallazgo, SolicitudAC
        from procesos.models import Proceso
        ins = self.get_object()
        if ins.estado not in ('con_acciones', 'cerrada'):
            return self._error('El hallazgo se registra después de firmar la inspección.')
        it = ins.items.filter(pk=request.data.get('item_id'), is_active=True, no_conforme=True).first()
        if not it:
            return self._error('Ítem no conforme no encontrado.')
        if it.hallazgo_id:
            return self._error(f'El ítem ya está registrado como {it.hallazgo.codigo}.')
        tipo = request.data.get('tipo_nc')
        if tipo not in ('nc_mayor', 'nc_menor'):
            return self._error('Indique la clasificación (NC mayor o NC menor).')
        u = request.user
        proceso = Proceso.objects.filter(nombre__icontains='Seguridad', padre__isnull=True).first() or \
            Proceso.objects.filter(padre__isnull=True, nombre__icontains='Integrado').first()
        desc = (f'Inspección {ins.codigo} ({ins.plantilla.nombre}, {ins.fecha.isoformat()}): '
                f'{it.texto}{" — " + it.observacion if it.observacion else ""}')
        h = Hallazgo.objects.create(
            tipo=tipo, fuente='inspeccion', proceso=proceso.nombre if proceso else 'Seguridad y Salud en el Trabajo',
            proceso_catalogo=proceso, descripcion=desc, requisito='Ley 29783 · ISO 45001:2018 9.1',
            lugar=(ins.lugar or (ins.area.nombre if ins.area_id else ''))[:150], fecha_deteccion=ins.fecha,
            estado='en_tratamiento', created_by=u, updated_by=u)
        sac = SolicitudAC.objects.create(hallazgo=h, fuente='otros', fuente_detalle=f'Inspección de SST {ins.codigo}',
                                         normas_aplicables=['iso_45001'], descripcion_nc=desc,
                                         requisito_auditado=h.requisito, fecha_registro=timezone.localdate(),
                                         created_by=u, updated_by=u)
        h.sac = sac
        h.save(update_fields=['sac'])
        it.hallazgo = h
        it.save(update_fields=['hallazgo'])
        _hist(ins, request, 'Hallazgo registrado', hallazgo=h.codigo)
        ins.save(update_fields=['historial'])
        return self._respuesta(ins)
    registrar_hallazgo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        ins = self.get_object()
        if ins.estado != 'en_registro':
            return self._error('Solo se anula una inspección aún no firmada.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la anulación.')
        ins.estado, ins.motivo_anulacion = 'anulada', motivo
        _hist(ins, request, 'Anulación', motivo=motivo)
        ins.updated_by = request.user
        ins.save()
        return self._respuesta(ins)
    anular.operacion = 'eliminar'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf_inspecciones import generar_inspeccion_pdf
        ins = self.get_object()
        return self._pdf(generar_inspeccion_pdf(ins), ins.codigo)
    pdf.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def programa(self, request):
        """Programa del año: por plantilla y mes, inspecciones esperadas según su frecuencia y realizadas."""
        anio = int(request.query_params.get('anio') or timezone.localdate().year)
        hoy = timezone.localdate()
        filas = []
        for pl in PlantillaInspeccion.objects.filter(is_active=True):
            paso = MESES_FRECUENCIA.get(pl.frecuencia)
            hechas = {}
            for i in pl.inspecciones.filter(is_active=True, fecha__year=anio).exclude(estado__in=['anulada']):
                hechas.setdefault(i.fecha.month, []).append({'id': i.pk, 'codigo': i.codigo, 'estado': i.estado})
            actual = (hoy.year, hoy.month)
            # Antes de usar la plantilla en el sistema, las inspecciones se registraban en papel: no se alertan.
            alta = timezone.localtime(pl.created_at)
            inicio = (alta.year, alta.month)
            meses = []
            for m in range(1, 13):
                # Cada inspección esperada tiene una ventana: su mes y los siguientes hasta la próxima.
                esperado = bool(paso) and (m - 1) % paso == 0
                lista = hechas.get(m, [])
                if not esperado:
                    situacion = 'realizado' if lista else 'no_programado'
                else:
                    fin = min(m + paso - 1, 12)
                    if any(hechas.get(x) for x in range(m, fin + 1)):
                        situacion = 'realizado'
                    elif (anio, m) > actual:
                        situacion = 'programado'
                    elif (anio, fin) >= actual:
                        situacion = 'en_plazo'
                    elif (anio, fin) < inicio:
                        situacion = 'antes_del_sistema'
                    else:
                        situacion = 'atrasado'
                meses.append({'mes': m, 'esperado': esperado, 'situacion': situacion, 'inspecciones': lista})
            filas.append({'plantilla': pl.pk, 'nombre': pl.nombre, 'frecuencia': pl.get_frecuencia_display(),
                          'meses': meses})
        return Response({'anio': anio, 'filas': filas})
    programa.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Alertas: vencimientos del inventario, acciones vencidas, inspecciones atrasadas, monitoreos."""
        hoy = timezone.localdate()
        venc = []
        for e in ElementoSeguridad.objects.filter(is_active=True):
            for v in e.vencimientos(hoy):
                if v['estado'] in ('vencido', 'por_vencer'):
                    venc.append({'elemento': e.pk, 'nombre': str(e), 'ubicacion': e.ubicacion, **v})
        venc.sort(key=lambda x: x['fecha'])
        acciones = []
        for it in ItemInspeccion.objects.filter(is_active=True, no_conforme=True, accion_completada=False,
                                                inspeccion__is_active=True,
                                                inspeccion__estado='con_acciones').select_related('inspeccion'):
            acciones.append({'inspeccion': it.inspeccion_id, 'codigo': it.inspeccion.codigo, 'item': it.texto[:100],
                             'plazo': it.plazo_accion.isoformat() if it.plazo_accion else None,
                             'vencida': bool(it.plazo_accion and it.plazo_accion < hoy)})
        prog = self.programa(request).data
        atrasadas = [{'plantilla': f['nombre'], 'mes': m['mes']} for f in prog['filas'] for m in f['meses']
                     if m['situacion'] == 'atrasado']
        mon = []
        for p in MonitoreoProgramado.objects.filter(is_active=True, programa__anio=hoy.year).select_related('programa'):
            ejec = p.meses_ejecutados()
            for m in p.meses or []:
                if m <= hoy.month and m not in ejec:
                    mon.append({'monitoreo': p.nombre, 'mes': m})
        recs = [{'id': r.pk, 'agente': r.agente, 'actividad': r.actividad[:100],
                 'fecha': r.fecha_programada.isoformat()}
                for r in RecomendacionMonitoreo.objects.filter(is_active=True) if r.vencida]
        return Response({'vencimientos': venc, 'acciones_pendientes': acciones, 'inspecciones_atrasadas': atrasadas,
                         'monitoreos_pendientes': mon, 'recomendaciones_vencidas': recs,
                         'en_registro': Inspeccion.objects.filter(is_active=True, estado='en_registro').count()})
    resumen.operacion = 'leer'


# ============================================================================ monitoreos
class ProgramaMonitoreoViewSet(_Base, viewsets.ModelViewSet):
    """Programa anual de monitoreos y sus ítems (POST/PATCH sobre /items vía acciones)."""
    queryset = ProgramaMonitoreo.objects.all()

    class _Ser(serializers.ModelSerializer):
        items = serializers.SerializerMethodField()

        class Meta:
            model = ProgramaMonitoreo
            fields = ['id', 'anio', 'fecha_actualizacion', 'historial', 'items']
            read_only_fields = ['historial']

        def get_items(self, obj):
            return ProgramadoSerializer(obj.items.filter(is_active=True).prefetch_related('monitoreos'),
                                        many=True).data

    serializer_class = _Ser

    def perform_create(self, serializer):
        p = serializer.save(created_by=self.request.user, updated_by=self.request.user,
                            fecha_actualizacion=timezone.localdate())
        _hist(p, self.request, 'Creación')
        p.save(update_fields=['historial'])

    def destroy(self, request, *args, **kwargs):
        return self._error('El programa anual no se elimina.')

    @action(detail=False, methods=['get'])
    def anio(self, request):
        a = int(request.query_params.get('anio') or timezone.localdate().year)
        p = ProgramaMonitoreo.objects.filter(anio=a).first()
        return Response(self._Ser(p).data if p else None)
    anio.operacion = 'leer'

    def _tocar(self, p, request, accion, **datos):
        p.fecha_actualizacion = timezone.localdate()
        _hist(p, request, accion, **datos)
        p.updated_by = request.user
        p.save()

    @action(detail=True, methods=['post'])
    def item(self, request, pk=None):
        """Agrega o corrige un monitoreo programado. Body: datos + id opcional."""
        p = self.get_object()
        inst = p.items.filter(pk=request.data.get('id'), is_active=True).first() if request.data.get('id') else None
        datos = {k: v for k, v in request.data.items() if k != 'id'}
        datos['programa'] = p.pk
        if not inst and 'orden' not in datos:
            datos['orden'] = p.items.filter(is_active=True).count() + 1
        ser = ProgramadoSerializer(inst, data=datos, partial=bool(inst))
        ser.is_valid(raise_exception=True)
        antes = (inst.meses, inst.fecha_programada) if inst else None
        it = ser.save(updated_by=request.user, **({} if inst else {'created_by': request.user}))
        if inst and antes != (it.meses, it.fecha_programada):
            self._tocar(p, request, 'Reprogramación', monitoreo=it.nombre,
                        antes=f'{antes[1] or ""} {antes[0]}', despues=f'{it.fecha_programada or ""} {it.meses}')
        else:
            self._tocar(p, request, 'Modificación' if inst else 'Monitoreo agregado', monitoreo=it.nombre)
        return Response(self._Ser(p).data, status=status.HTTP_200_OK if inst else status.HTTP_201_CREATED)
    item.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_item(self, request, pk=None):
        p = self.get_object()
        it = p.items.filter(pk=request.data.get('id'), is_active=True).first()
        if not it:
            return self._error('Monitoreo no encontrado.')
        if it.monitoreos.exclude(estado='anulado').exists():
            return self._error('Ese monitoreo ya tiene registros: no se quita del programa.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo.')
        it.is_active = False
        it.save(update_fields=['is_active'])
        self._tocar(p, request, 'Monitoreo retirado', monitoreo=it.nombre, motivo=motivo)
        return Response(self._Ser(p).data)
    quitar_item.operacion = 'editar'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf_inspecciones import generar_programa_monitoreos_pdf
        p = self.get_object()
        return self._pdf(generar_programa_monitoreos_pdf(p), f'Programa de monitoreos {p.anio}')
    pdf.operacion = 'leer'


class MonitoreoViewSet(_Base, viewsets.ModelViewSet):
    """Registro de monitoreos: en registro → registrado (firma). Anulado: registro por error."""
    queryset = Monitoreo.objects.all().prefetch_related('programados__programa', 'recomendaciones')
    serializer_class = MonitoreoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list':
            qs = qs.filter(is_active=True)
        if p.get('anio'):
            qs = qs.filter(fecha__year=p['anio'])
        return qs

    def perform_create(self, serializer):
        m = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(m, self.request, 'Registro')
        m.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        m = self.get_object()
        if m.estado != 'en_registro':
            return self._error(f'El monitoreo está {m.get_estado_display().lower()}: no se modifica.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return self._error('Un monitoreo no se elimina: si se registró por error, se anula con motivo.')

    @action(detail=True, methods=['post'])
    def informe(self, request, pk=None):
        m = self.get_object()
        if m.estado != 'en_registro':
            return self._error('El informe se adjunta antes de firmar el registro.')
        if not request.FILES.get('archivo'):
            return self._error('Adjunte el informe.')
        m.informe = request.FILES['archivo']
        m.updated_by = request.user
        m.save()
        return Response(MonitoreoSerializer(m).data)
    informe.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def firmar(self, request, pk=None):
        m = self.get_object()
        if m.estado != 'en_registro':
            return self._error('El monitoreo ya fue registrado.')
        falta = []
        if not m.resultados:
            falta.append('los resultados por agente')
        elif any(r.get('dentro_lmp') is None for r in m.resultados):
            falta.append('si cada resultado está dentro de los límites máximos permisibles')
        if m.con_desviaciones and not m.causas_desviacion.strip():
            falta.append('las causas de las desviaciones')
        if not m.conclusiones.strip():
            falta.append('las conclusiones y recomendaciones')
        if not m.informe:
            falta.append('el informe con resultados (adjunto)')
        if falta:
            return self._error('Para registrar el monitoreo indique ' + ', '.join(falta) + '.')
        error = self._clave(request, 'el registro del monitoreo')
        if error:
            return error
        m.estado, m.firma_registro = 'registrado', _firma(request)
        _hist(m, request, 'Firma del registro')
        m.updated_by = request.user
        m.save()
        return Response(MonitoreoSerializer(m).data)
    firmar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        m = self.get_object()
        if m.estado != 'en_registro':
            return self._error('Solo se anula un monitoreo aún no registrado.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la anulación.')
        m.estado, m.motivo_anulacion = 'anulado', motivo
        _hist(m, request, 'Anulación', motivo=motivo)
        m.save()
        return Response(MonitoreoSerializer(m).data)
    anular.operacion = 'eliminar'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf_inspecciones import generar_monitoreo_pdf
        m = self.get_object()
        return self._pdf(generar_monitoreo_pdf(m), m.codigo)
    pdf.operacion = 'leer'


class RecomendacionViewSet(_Base, viewsets.ModelViewSet):
    """Programa de seguimiento de recomendaciones de monitoreos."""
    queryset = RecomendacionMonitoreo.objects.all().select_related('monitoreo', 'responsable')
    serializer_class = RecomendacionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list':
            qs = qs.filter(is_active=True)
        if p.get('anio'):
            qs = qs.filter(anio=p['anio'])
        if p.get('monitoreo'):
            qs = qs.filter(monitoreo_id=p['monitoreo'])
        return qs

    def perform_create(self, serializer):
        r = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(r, self.request, 'Registro')
        r.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        antes = serializer.instance.estado
        r = serializer.save(updated_by=self.request.user)
        if r.estado != antes:
            _hist(r, self.request, f'Estado: {r.get_estado_display()}')
            if r.estado == 'ejecutada' and not r.fecha_ejecucion:
                r.fecha_ejecucion = timezone.localdate()
            if r.estado == 'ejecutada' and r.fecha_ejecucion and r.fecha_ejecucion.year == r.anio \
                    and r.fecha_ejecucion.month not in (r.meses_ejecutados or []):
                r.meses_ejecutados = sorted((r.meses_ejecutados or []) + [r.fecha_ejecucion.month])
            r.save()

    def destroy(self, request, *args, **kwargs):
        r = self.get_object()
        r.is_active = False
        _hist(r, request, 'Retirada del programa')
        r.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def programa_pdf(self, request):
        from .pdf_inspecciones import generar_recomendaciones_pdf
        anio = int(request.query_params.get('anio') or timezone.localdate().year)
        return self._pdf(generar_recomendaciones_pdf(anio), f'Seguimiento de recomendaciones {anio}')
    programa_pdf.operacion = 'leer'
