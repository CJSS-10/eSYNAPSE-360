from rest_framework import serializers

from .models import ATS, ACCION_NIVEL, ATSTipo, FilaIPERC, PasoATS, PeligroCatalogo, SITUACIONES


def _proceso_principal(valor):
    """En SST el proceso es el área (proceso principal del mapa), no un subproceso."""
    if valor is not None and valor.padre_id:
        raise serializers.ValidationError(f'Elija el proceso principal ({valor.padre.nombre}), no el subproceso.')
    return valor


def _escala(data, campos, maximo, nombre):
    for c in campos:
        v = data.get(c)
        if v is not None and not (1 <= v <= maximo):
            raise serializers.ValidationError({c: [f'{nombre}: use la escala de 1 a {maximo}.']})


class PeligroSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeligroCatalogo
        fields = ['id', 'clase', 'codigo', 'peligro', 'riesgo', 'consecuencia']


class FilaIPERCSerializer(serializers.ModelSerializer):
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    unidad_nombre = serializers.CharField(source='unidad.nombre', read_only=True, default=None)
    puestos_nombres = serializers.SerializerMethodField()
    responsables_nombres = serializers.SerializerMethodField()
    probabilidad = serializers.IntegerField(read_only=True)
    nivel_riesgo = serializers.IntegerField(read_only=True)
    clasificacion = serializers.CharField(read_only=True)
    aceptable = serializers.BooleanField(read_only=True, allow_null=True)
    r_probabilidad = serializers.IntegerField(read_only=True)
    r_nivel_riesgo = serializers.IntegerField(read_only=True)
    r_clasificacion = serializers.CharField(read_only=True)
    r_aceptable = serializers.BooleanField(read_only=True, allow_null=True)
    situacion_control = serializers.CharField(read_only=True)
    accion_requerida = serializers.SerializerMethodField()

    class Meta:
        model = FilaIPERC
        fields = ['id', 'codigo', 'area', 'unidad', 'unidad_nombre', 'proceso', 'proceso_nombre', 'subproceso', 'puestos',
                  'puestos_nombres',
                  'todos_los_puestos', 'puestos_texto', 'actividad', 'peligro', 'riesgo', 'consecuencia',
                  'situaciones', 'controles_existentes', 'requisito_legal', 'personas', 'procedimientos',
                  'capacitacion', 'exposicion', 'severidad', 'probabilidad', 'nivel_riesgo', 'clasificacion',
                  'aceptable', 'accion_requerida', 'control_eliminacion', 'control_sustitucion', 'control_ingenieria',
                  'control_administrativo', 'control_epp', 'responsables', 'responsables_nombres', 'responsable',
                  'r_personas', 'r_procedimientos',
                  'r_capacitacion', 'r_exposicion', 'r_severidad', 'r_probabilidad', 'r_nivel_riesgo',
                  'r_clasificacion', 'r_aceptable', 'situacion_control', 'estado', 'historial', 'is_active',
                  'updated_at']
        read_only_fields = ['codigo', 'estado', 'historial', 'is_active']

    def validate_proceso(self, valor):
        return _proceso_principal(valor)

    def get_puestos_nombres(self, obj):
        return [p.nombre for p in obj.puestos.all()] if obj.pk else []

    def get_responsables_nombres(self, obj):
        return [p.nombre for p in obj.responsables.all()] if obj.pk else []

    def get_accion_requerida(self, obj):
        return ACCION_NIVEL.get(obj.clasificacion, '')

    def validate(self, data):
        _escala(data, ('personas', 'procedimientos', 'capacitacion', 'exposicion', 'severidad', 'r_personas',
                       'r_procedimientos', 'r_capacitacion', 'r_exposicion', 'r_severidad'), 3, 'Índice')
        validas = dict(SITUACIONES)
        if 'situaciones' in data:
            if any(s not in validas for s in data['situaciones'] or []):
                raise serializers.ValidationError({'situaciones': ['Situación no válida.']})
            if not data['situaciones']:
                raise serializers.ValidationError({'situaciones': ['Marque si es rutinaria, no rutinaria o de '
                                                                   'emergencia.']})
        return data


class FilaIPERCListaSerializer(serializers.ModelSerializer):
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    nivel_riesgo = serializers.IntegerField(read_only=True)
    clasificacion = serializers.CharField(read_only=True)
    r_nivel_riesgo = serializers.IntegerField(read_only=True)
    r_clasificacion = serializers.CharField(read_only=True)
    situacion_control = serializers.CharField(read_only=True)

    class Meta:
        model = FilaIPERC
        fields = ['id', 'codigo', 'area', 'proceso_nombre', 'puestos_texto', 'actividad', 'peligro', 'riesgo',
                  'situaciones', 'nivel_riesgo', 'clasificacion', 'r_nivel_riesgo', 'r_clasificacion',
                  'situacion_control', 'estado']


class PasoSerializer(serializers.ModelSerializer):
    valor = serializers.IntegerField(read_only=True)
    nivel = serializers.CharField(read_only=True)
    r_valor = serializers.IntegerField(read_only=True)
    r_nivel = serializers.CharField(read_only=True)

    class Meta:
        model = PasoATS
        fields = ['id', 'orden', 'etapa', 'peligros', 'riesgos', 'severidad', 'probabilidad', 'valor', 'nivel',
                  'medidas', 'r_severidad', 'r_probabilidad', 'r_valor', 'r_nivel']


def _validar_pasos_tipo(pasos):
    if not isinstance(pasos, list):
        raise serializers.ValidationError('Formato de etapas no válido.')
    limpios = []
    for i, p in enumerate(pasos, start=1):
        if not isinstance(p, dict) or not (p.get('etapa') or '').strip():
            raise serializers.ValidationError(f'Etapa {i}: describa la etapa.')
        fila = {k: (p.get(k) or '').strip() for k in ('etapa', 'peligros', 'riesgos', 'medidas')}
        for k in ('severidad', 'probabilidad', 'r_severidad', 'r_probabilidad'):
            v = p.get(k)
            if v in (None, ''):
                fila[k] = None
                continue
            try:
                v = int(v)
            except (TypeError, ValueError):
                raise serializers.ValidationError(f'Etapa {i}: valor no válido.')
            if not 1 <= v <= 4:
                raise serializers.ValidationError(f'Etapa {i}: severidad y probabilidad van de 1 a 4.')
            fila[k] = v
        limpios.append(fila)
    return limpios


class ATSTipoSerializer(serializers.ModelSerializer):
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    filas_iperc_info = serializers.SerializerMethodField()
    n_ats = serializers.SerializerMethodField()

    class Meta:
        model = ATSTipo
        fields = ['id', 'nombre', 'descripcion', 'tipos_trabajo', 'proceso', 'proceso_nombre', 'filas_iperc',
                  'filas_iperc_info', 'pasos', 'is_active', 'n_ats']
        read_only_fields = ['is_active']

    def validate_proceso(self, valor):
        return _proceso_principal(valor)

    def get_filas_iperc_info(self, obj):
        return [{'id': f.id, 'codigo': f.codigo, 'peligro': f.peligro} for f in obj.filas_iperc.all()] if obj.pk else []

    def get_n_ats(self, obj):
        return obj.ats.count() if obj.pk else 0

    def validate_pasos(self, valor):
        return _validar_pasos_tipo(valor)

    def validate_nombre(self, valor):
        valor = valor.strip()
        otros = ATSTipo.objects.exclude(pk=getattr(self.instance, 'pk', None)).values_list('nombre', flat=True)
        if any(n.casefold() == valor.casefold() for n in otros):
            raise serializers.ValidationError('Ya existe un ATS tipo con ese nombre.')
        return valor


class ATSSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    lugar_display = serializers.CharField(source='get_lugar_ejecucion_display', read_only=True)
    formato_display = serializers.CharField(source='get_formato_display', read_only=True)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    ats_tipo_nombre = serializers.CharField(source='ats_tipo.nombre', read_only=True, default=None)
    supervisor_nombre = serializers.SerializerMethodField()
    recibido_por_nombre = serializers.SerializerMethodField()
    revisor_nombre = serializers.SerializerMethodField()
    evidencia_url = serializers.SerializerMethodField()
    pasos = serializers.SerializerMethodField()
    filas_iperc_info = serializers.SerializerMethodField()
    pasos_editables = serializers.BooleanField(read_only=True)
    etapas_abiertas = serializers.SerializerMethodField()

    class Meta:
        model = ATS
        fields = ['id', 'codigo', 'estado', 'estado_display', 'lugar_ejecucion', 'lugar_display', 'formato',
                  'formato_display', 'cliente', 'ats_tipo', 'ats_tipo_nombre', 'zona', 'fecha', 'hora_inicio',
                  'hora_fin', 'tarea', 'lugar', 'orden_trabajo', 'empresa', 'planificado', 'tipos_trabajo',
                  'tipo_otro', 'proceso', 'proceso_nombre', 'filas_iperc', 'filas_iperc_info', 'ejecutantes',
                  'comentarios', 'equipos', 'supervisor', 'supervisor_nombre', 'firma_supervisor',
                  'responsable_cliente', 'ssoma_cliente', 'motivo_anulacion', 'evidencia_url', 'fecha_ejecucion',
                  'observaciones_campo', 'recibido_por_nombre', 'fecha_recepcion', 'revisor_nombre',
                  'firma_revision', 'observaciones_revision', 'historial', 'pasos', 'pasos_editables',
                  'etapas_abiertas', 'is_active', 'created_at']
        read_only_fields = ['codigo', 'estado', 'supervisor', 'firma_supervisor', 'motivo_anulacion', 'is_active',
                            'fecha_ejecucion', 'observaciones_campo', 'fecha_recepcion', 'firma_revision',
                            'observaciones_revision', 'historial']

    def validate_proceso(self, valor):
        return _proceso_principal(valor)

    @staticmethod
    def _n(u):
        return (u.get_full_name() or u.username) if u else None

    def get_supervisor_nombre(self, obj):
        return self._n(obj.supervisor)

    def get_recibido_por_nombre(self, obj):
        return self._n(obj.recibido_por)

    def get_revisor_nombre(self, obj):
        return self._n(obj.revisor)

    def get_evidencia_url(self, obj):
        return obj.evidencia.url if obj.evidencia else None

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas() if obj.pk else ['preparacion', 'campo']

    def validate(self, data):
        lugar = data.get('lugar_ejecucion', getattr(self.instance, 'lugar_ejecucion', 'instalaciones'))
        formato = data.get('formato', getattr(self.instance, 'formato', 'metrindust'))
        if formato == 'cliente' and lugar != 'campo':
            raise serializers.ValidationError({'formato': ['El formato del cliente solo aplica a trabajos en campo.']})
        return data

    def get_pasos(self, obj):
        return PasoSerializer(obj.pasos.filter(is_active=True), many=True).data if obj.pk else []

    def get_filas_iperc_info(self, obj):
        return [{'id': f.id, 'codigo': f.codigo, 'peligro': f.peligro, 'clasificacion': f.clasificacion}
                for f in obj.filas_iperc.all()] if obj.pk else []

    def validate_ejecutantes(self, valor):
        """Cada ejecutante es un trabajador de Organización y personal o, si es externo, solo su nombre."""
        from organizacion.models import Trabajador
        valor = valor or []
        if not isinstance(valor, list):
            raise serializers.ValidationError('Formato no válido.')
        if len(valor) > 9:
            raise serializers.ValidationError('El formato admite hasta 9 ejecutantes.')
        limpios, vistos = [], set()
        for e in valor:
            if not isinstance(e, dict):
                raise serializers.ValidationError('Formato no válido.')
            tid = e.get('trabajador')
            if tid:
                t = Trabajador.objects.filter(pk=tid, is_active=True).select_related('puesto').first()
                if not t:
                    raise serializers.ValidationError('Trabajador no encontrado.')
                if t.estado != 'activo':
                    raise serializers.ValidationError(f'{t.nombre_completo} está cesado.')
                if t.pk in vistos:
                    raise serializers.ValidationError(f'{t.nombre_completo} está repetido.')
                vistos.add(t.pk)
                limpios.append({'trabajador': t.pk, 'nombre': t.nombre_completo, 'puesto': t.puesto.nombre})
            elif (e.get('nombre') or '').strip():
                limpios.append({'trabajador': None, 'nombre': e['nombre'].strip(), 'puesto': (e.get('puesto') or '').strip()})
        return limpios
