from rest_framework import serializers

from .models import (ESTRATEGIAS_OPORTUNIDAD, ESTRATEGIAS_RIESGO, AccionRiesgo, ElementoContexto, OportunidadMejora,
                     RevisionMatriz, RiesgoOportunidad)


def _nombre(u):
    return (u.get_full_name() or u.username) if u else None


def _url(f):
    return f.url if f else None


def _escala(valor, campo):
    if valor is not None and not (1 <= valor <= 5):
        raise serializers.ValidationError({campo: ['Use la escala de 1 a 5.']})


class ElementoContextoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    n_riesgos = serializers.SerializerMethodField()

    class Meta:
        model = ElementoContexto
        fields = ['id', 'tipo', 'tipo_display', 'codigo', 'descripcion', 'requisitos', 'is_active', 'n_riesgos']
        read_only_fields = ['codigo']

    def get_n_riesgos(self, obj):
        return obj.riesgos.filter(is_active=True).count()


class AccionSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    responsable_nombre = serializers.CharField(read_only=True)
    evidencia_url = serializers.SerializerMethodField()
    vencida = serializers.BooleanField(read_only=True)
    hallazgo_codigo = serializers.CharField(source='hallazgo_incumplimiento.codigo', read_only=True, default=None)

    class Meta:
        model = AccionRiesgo
        fields = ['id', 'orden', 'actividad', 'implementacion_documental', 'responsable', 'responsable_texto',
                  'responsable_nombre', 'fecha_inicio', 'fecha_maxima', 'recursos', 'estado', 'estado_display',
                  'fecha_ejecucion', 'evidencia_url', 'observaciones', 'vencida', 'hallazgo_codigo']

    def get_evidencia_url(self, obj):
        return _url(obj.evidencia)


class RiesgoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    estrategia_display = serializers.CharField(source='get_estrategia_display', read_only=True)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    hallazgo_codigo = serializers.CharField(source='hallazgo.codigo', read_only=True, default=None)
    contexto_info = serializers.SerializerMethodField()
    valor = serializers.IntegerField(read_only=True)
    nivel = serializers.CharField(read_only=True)
    requiere_accion = serializers.CharField(read_only=True)
    valor_residual = serializers.IntegerField(read_only=True)
    nivel_residual = serializers.CharField(read_only=True)
    eficacia = serializers.CharField(read_only=True)
    situacion = serializers.CharField(read_only=True)
    etapas_abiertas = serializers.SerializerMethodField()
    acciones = serializers.SerializerMethodField()
    verificado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = RiesgoOportunidad
        fields = ['id', 'codigo', 'tipo', 'tipo_display', 'estado', 'estado_display', 'proceso', 'proceso_nombre',
                  'contexto', 'contexto_info', 'categoria', 'categoria_display', 'fuente', 'fuente_display',
                  'fecha_identificacion', 'actividad', 'descripcion', 'causa', 'efecto', 'controles_existentes',
                  'hallazgo', 'hallazgo_codigo', 'probabilidad', 'impacto', 'valor', 'nivel', 'requiere_accion',
                  'estrategia', 'estrategia_display', 'justificacion_aceptacion', 'firma_aceptacion',
                  'decision_cartera', 'motivo_cartera', 'residual_probabilidad', 'residual_impacto', 'valor_residual',
                  'nivel_residual', 'fecha_verificacion', 'evidencia_verificacion', 'verificado_por',
                  'verificado_por_nombre', 'eficacia', 'situacion', 'historial', 'motivo_retiro', 'etapas_abiertas',
                  'acciones', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['codigo', 'estado', 'firma_aceptacion', 'decision_cartera', 'motivo_cartera',
                            'residual_probabilidad', 'residual_impacto', 'fecha_verificacion',
                            'evidencia_verificacion', 'verificado_por', 'historial', 'motivo_retiro', 'is_active']

    def get_contexto_info(self, obj):
        return [{'id': e.id, 'codigo': e.codigo, 'tipo': e.tipo, 'descripcion': e.descripcion}
                for e in obj.contexto.all()] if obj.pk else []

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas()

    def get_acciones(self, obj):
        return AccionSerializer(obj.acciones.filter(is_active=True), many=True).data if obj.pk else []

    def get_verificado_por_nombre(self, obj):
        return _nombre(obj.verificado_por)

    def validate(self, data):
        inst = self.instance
        tipo = data.get('tipo', inst.tipo if inst else None)
        _escala(data.get('probabilidad'), 'probabilidad')
        _escala(data.get('impacto'), 'impacto')
        estrategia = data.get('estrategia', inst.estrategia if inst else '')
        if estrategia:
            validas = ESTRATEGIAS_RIESGO if tipo == 'riesgo' else ESTRATEGIAS_OPORTUNIDAD
            if estrategia not in validas:
                raise serializers.ValidationError({'estrategia': [
                    'Para un riesgo: reducir, aceptar, evitar, compartir o remover.' if tipo == 'riesgo'
                    else 'Para una oportunidad la estrategia es incrementar.']})
        if inst and 'tipo' in data and data['tipo'] != inst.tipo:
            raise serializers.ValidationError({'tipo': ['El tipo no cambia: el código depende de él.']})
        return data


class RiesgoListaSerializer(serializers.ModelSerializer):
    """Columnas de la matriz en pantalla."""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    estrategia_display = serializers.CharField(source='get_estrategia_display', read_only=True)
    valor = serializers.IntegerField(read_only=True)
    nivel = serializers.CharField(read_only=True)
    requiere_accion = serializers.CharField(read_only=True)
    valor_residual = serializers.IntegerField(read_only=True)
    nivel_residual = serializers.CharField(read_only=True)
    eficacia = serializers.CharField(read_only=True)
    situacion = serializers.CharField(read_only=True)
    n_acciones = serializers.SerializerMethodField()
    vencidas = serializers.SerializerMethodField()

    class Meta:
        model = RiesgoOportunidad
        fields = ['id', 'codigo', 'tipo', 'tipo_display', 'estado', 'proceso', 'proceso_nombre', 'categoria',
                  'categoria_display', 'fuente', 'fecha_identificacion', 'descripcion', 'probabilidad', 'impacto',
                  'valor', 'nivel', 'requiere_accion', 'estrategia', 'estrategia_display', 'valor_residual',
                  'nivel_residual', 'eficacia', 'situacion', 'n_acciones', 'vencidas']

    def get_n_acciones(self, obj):
        return len(obj.acciones_activas())

    def get_vencidas(self, obj):
        return len(obj.acciones_vencidas)


class OportunidadMejoraSerializer(serializers.ModelSerializer):
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    decision_display = serializers.CharField(source='get_decision_display', read_only=True)
    estado_accion_display = serializers.CharField(source='get_estado_accion_display', read_only=True)
    eficacia_display = serializers.CharField(source='get_eficacia_display', read_only=True)
    responsable_nombre = serializers.CharField(read_only=True)
    hallazgo_codigo = serializers.CharField(source='hallazgo.codigo', read_only=True, default=None)
    evidencia_url = serializers.SerializerMethodField()
    cerrada = serializers.BooleanField(read_only=True)
    evaluacion_vencida = serializers.BooleanField(read_only=True)
    accion_vencida = serializers.BooleanField(read_only=True)
    etapas_abiertas = serializers.SerializerMethodField()

    class Meta:
        model = OportunidadMejora
        fields = ['id', 'codigo', 'proceso', 'proceso_nombre', 'fuente', 'fuente_display', 'detectado_por',
                  'fecha_identificacion', 'descripcion', 'situacion', 'hallazgo', 'hallazgo_codigo', 'decision',
                  'decision_display', 'justificacion', 'fecha_decision', 'accion', 'responsable', 'responsable_texto',
                  'responsable_nombre', 'fecha_maxima', 'estado_accion', 'estado_accion_display', 'fecha_ejecucion',
                  'fecha_verificacion', 'evidencia', 'evidencia_url', 'eficacia', 'eficacia_display', 'historial',
                  'cerrada', 'evaluacion_vencida', 'accion_vencida', 'etapas_abiertas', 'is_active', 'created_at']
        read_only_fields = ['codigo', 'decision', 'justificacion', 'fecha_decision', 'accion', 'responsable',
                            'responsable_texto', 'fecha_maxima', 'estado_accion', 'fecha_ejecucion',
                            'fecha_verificacion', 'evidencia', 'eficacia', 'historial', 'is_active']

    def get_evidencia_url(self, obj):
        return _url(obj.evidencia_archivo)

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas()


class RevisionSerializer(serializers.ModelSerializer):
    matriz_display = serializers.CharField(source='get_matriz_display', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    responsable_nombre = serializers.CharField(read_only=True)

    class Meta:
        model = RevisionMatriz
        fields = ['id', 'matriz', 'matriz_display', 'tipo', 'tipo_display', 'fecha', 'responsable_nombre',
                  'observaciones', 'firma']
