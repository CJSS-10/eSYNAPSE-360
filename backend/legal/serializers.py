from rest_framework import serializers

from .models import ComunicacionRequisito, Evaluacion, Obligacion, Requisito, ResultadoEvaluacion


def _nombre(u):
    return (u.get_full_name() or u.username) if u else None


class ComunicacionSerializer(serializers.ModelSerializer):
    medio_display = serializers.CharField(source='get_medio_display', read_only=True)
    registrado_por = serializers.SerializerMethodField()

    class Meta:
        model = ComunicacionRequisito
        fields = ['id', 'fecha', 'medio', 'medio_display', 'destinatarios', 'resumen', 'registrado_por']

    def get_registrado_por(self, obj):
        return _nombre(obj.created_by)


class ObligacionSerializer(serializers.ModelSerializer):
    ambito_display = serializers.CharField(source='get_ambito_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    documento = serializers.CharField(read_only=True)
    requisito_nombre = serializers.CharField(source='requisito.nombre', read_only=True, default=None)
    procesos_nombres = serializers.SerializerMethodField()
    ultimo_resultado = serializers.SerializerMethodField()

    class Meta:
        model = Obligacion
        fields = ['id', 'ambito', 'ambito_display', 'tema', 'orden', 'requisito', 'requisito_nombre', 'documento',
                  'documento_legal', 'articulo', 'extracto', 'evidencia_documento', 'proceso_sede', 'procesos',
                  'procesos_nombres', 'responsable', 'periodicidad', 'observaciones', 'estado', 'estado_display',
                  'ultimo_resultado', 'is_active']
        read_only_fields = ['estado', 'is_active', 'orden']

    def get_procesos_nombres(self, obj):
        return [p.nombre for p in obj.procesos.all()] if obj.pk else []

    def get_ultimo_resultado(self, obj):
        r = obj.resultados.filter(evaluacion__estado='cerrada', evaluacion__is_active=True) \
            .exclude(resultado='pendiente').select_related('evaluacion').order_by('-evaluacion__anio',
                                                                                    '-evaluacion__orden').first()
        return {'resultado': r.resultado, 'periodo': f'{r.evaluacion.anio} · {r.evaluacion.periodo}'} if r else None

    def validate(self, data):
        req = data.get('requisito')
        ambito = data.get('ambito', self.instance.ambito if self.instance else None)
        if req and req.ambito != ambito:
            raise serializers.ValidationError({'requisito': ['El requisito es de otro ámbito.']})
        return data


class RequisitoSerializer(serializers.ModelSerializer):
    ambito_display = serializers.CharField(source='get_ambito_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    denominacion = serializers.CharField(read_only=True)
    procesos_nombres = serializers.SerializerMethodField()
    n_obligaciones = serializers.SerializerMethodField()
    obligaciones = serializers.SerializerMethodField()
    comunicaciones = serializers.SerializerMethodField()

    class Meta:
        model = Requisito
        fields = ['id', 'ambito', 'ambito_display', 'tema', 'orden', 'tipo', 'codigo', 'denominacion', 'nombre',
                  'fecha_aprobacion', 'modificatorias', 'observaciones', 'estado', 'estado_display', 'procesos',
                  'procesos_nombres', 'aplicabilidad', 'fecha_identificacion', 'fecha_derogacion', 'historial',
                  'n_obligaciones', 'obligaciones', 'comunicaciones', 'is_active', 'created_at']
        read_only_fields = ['orden', 'modificatorias', 'estado', 'fecha_derogacion', 'historial', 'is_active']

    def get_procesos_nombres(self, obj):
        return [p.nombre for p in obj.procesos.all()] if obj.pk else []

    def get_n_obligaciones(self, obj):
        return obj.obligaciones.filter(is_active=True).count() if obj.pk else 0

    def get_obligaciones(self, obj):
        if not obj.pk or self.context.get('lista'):
            return []
        return ObligacionSerializer(obj.obligaciones.filter(is_active=True), many=True).data

    def get_comunicaciones(self, obj):
        if not obj.pk or self.context.get('lista'):
            return []
        return ComunicacionSerializer(obj.comunicaciones.filter(is_active=True), many=True).data


class ResultadoSerializer(serializers.ModelSerializer):
    resultado_display = serializers.CharField(source='get_resultado_display', read_only=True)
    obligacion_info = serializers.SerializerMethodField()
    evaluado_por_nombre = serializers.SerializerMethodField()
    evidencia_url = serializers.SerializerMethodField()
    hallazgo_codigo = serializers.CharField(source='hallazgo.codigo', read_only=True, default=None)

    class Meta:
        model = ResultadoEvaluacion
        fields = ['id', 'obligacion', 'obligacion_info', 'resultado', 'resultado_display', 'observaciones',
                  'evidencia_url', 'evaluado_por_nombre', 'fecha', 'hallazgo_codigo']

    def get_obligacion_info(self, obj):
        o = obj.obligacion
        return {'tema': o.tema, 'documento': o.documento, 'articulo': o.articulo, 'extracto': o.extracto,
                'evidencia_documento': o.evidencia_documento, 'responsable': o.responsable,
                'periodicidad': o.periodicidad}

    def get_evaluado_por_nombre(self, obj):
        return _nombre(obj.evaluado_por)

    def get_evidencia_url(self, obj):
        return obj.evidencia.url if obj.evidencia else None


class EvaluacionSerializer(serializers.ModelSerializer):
    ambito_display = serializers.CharField(source='get_ambito_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    cerrada_por_nombre = serializers.SerializerMethodField()
    resumen = serializers.SerializerMethodField()

    class Meta:
        model = Evaluacion
        fields = ['id', 'ambito', 'ambito_display', 'anio', 'periodo', 'orden', 'estado', 'estado_display',
                  'fecha_inicio', 'fecha_cierre', 'cerrada_por_nombre', 'firma', 'historica', 'resumen']

    def get_cerrada_por_nombre(self, obj):
        return _nombre(obj.cerrada_por)

    def get_resumen(self, obj):
        return obj.resumen()
