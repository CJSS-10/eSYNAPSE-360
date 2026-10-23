from rest_framework import serializers

from .models import MOTIVOS_QUEJA, AdjuntoQueja, ComunicacionQueja, Queja


def _nombre(u):
    return (u.get_full_name() or u.username) if u else None


class ComunicacionQuejaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    medio_display = serializers.CharField(source='get_medio_display', read_only=True)
    registrado_por = serializers.SerializerMethodField()
    evidencia_url = serializers.SerializerMethodField()

    class Meta:
        model = ComunicacionQueja
        fields = ['id', 'tipo', 'tipo_display', 'fecha', 'medio', 'medio_display', 'resumen',
                  'evidencia_url', 'registrado_por']

    def get_registrado_por(self, obj):
        return _nombre(obj.created_by)

    def get_evidencia_url(self, obj):
        return obj.evidencia.url if obj.evidencia else None


class AdjuntoQuejaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    nombre = serializers.SerializerMethodField()

    class Meta:
        model = AdjuntoQueja
        fields = ['id', 'descripcion', 'url', 'nombre', 'created_at']

    def get_url(self, obj):
        return obj.archivo.url if obj.archivo else None

    def get_nombre(self, obj):
        return obj.archivo.name.rsplit('/', 1)[-1] if obj.archivo else ''


class QuejaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    resultado_display = serializers.CharField(source='get_resultado_display', read_only=True)
    tipo_reclamante_display = serializers.CharField(source='get_tipo_reclamante_display', read_only=True)
    medio_recepcion_display = serializers.CharField(source='get_medio_recepcion_display', read_only=True)
    origen_display = serializers.CharField(source='get_origen_display', read_only=True)
    medio_cierre_display = serializers.CharField(source='get_medio_cierre_display', read_only=True)
    conformidad_cliente_display = serializers.CharField(source='get_conformidad_cliente_display', read_only=True)
    recibido_por_nombre = serializers.SerializerMethodField()
    registrado_por = serializers.SerializerMethodField()
    validado_por_nombre = serializers.SerializerMethodField()
    decidido_por_nombre = serializers.SerializerMethodField()
    responsable_acciones_nombre = serializers.SerializerMethodField()
    notificado_por_nombre = serializers.SerializerMethodField()
    responsables_nombres = serializers.SerializerMethodField()
    involucrados_nombres = serializers.SerializerMethodField()
    hallazgo_codigo = serializers.CharField(source='hallazgo.codigo', read_only=True, default=None)
    hallazgo_estado = serializers.CharField(source='hallazgo.get_estado_display', read_only=True, default=None)
    sac_codigo = serializers.SerializerMethodField()
    etapas_abiertas = serializers.SerializerMethodField()
    plazos = serializers.SerializerMethodField()
    comunicaciones = serializers.SerializerMethodField()
    adjuntos = serializers.SerializerMethodField()

    class Meta:
        model = Queja
        fields = ['id', 'codigo', 'estado', 'estado_display', 'resultado', 'resultado_display',
                  'fecha_recepcion', 'recibido_por', 'recibido_por_nombre', 'registrado_por',
                  'tipo_reclamante', 'tipo_reclamante_display', 'empresa', 'contacto', 'contacto_email',
                  'contacto_telefono', 'orden_trabajo', 'medio_recepcion', 'medio_recepcion_display', 'medio_otro',
                  'origen', 'origen_display', 'motivo', 'desde_encuesta', 'descripcion',
                  'relacionada', 'motivo_validacion', 'fecha_validacion', 'validado_por', 'validado_por_nombre',
                  'responsables', 'responsables_nombres', 'involucrados', 'involucrados_nombres',
                  'fecha_evaluacion', 'evaluacion', 'investigacion', 'dentro_alcance', 'plazo_ampliado',
                  'motivo_ampliacion', 'fecha_compromiso', 'cliente_solicita_informe',
                  'fundamento_decision', 'fecha_decision', 'decidido_por', 'decidido_por_nombre',
                  'acciones', 'responsable_acciones', 'responsable_acciones_nombre', 'hallazgo', 'hallazgo_codigo',
                  'hallazgo_estado', 'sac_codigo', 'requiere_tnc', 'certificado_original', 'certificado_nuevo',
                  'seguimiento', 'fecha_seguimiento',
                  'comunicacion_cliente', 'medio_cierre', 'medio_cierre_display', 'conformidad_cliente',
                  'conformidad_cliente_display', 'fecha_cierre', 'notificado_por', 'notificado_por_nombre',
                  'observaciones', 'reaperturas', 'etapas_abiertas', 'plazos', 'comunicaciones', 'adjuntos',
                  'is_active', 'created_at']
        read_only_fields = ['codigo', 'estado', 'resultado', 'relacionada', 'motivo_validacion', 'fecha_validacion',
                            'validado_por', 'fundamento_decision', 'fecha_decision', 'decidido_por', 'hallazgo',
                            'fecha_cierre', 'notificado_por', 'reaperturas', 'is_active']

    def get_recibido_por_nombre(self, obj):
        return _nombre(obj.recibido_por)

    def get_registrado_por(self, obj):
        return _nombre(obj.created_by)

    def get_validado_por_nombre(self, obj):
        return _nombre(obj.validado_por)

    def get_decidido_por_nombre(self, obj):
        return _nombre(obj.decidido_por)

    def get_responsable_acciones_nombre(self, obj):
        return _nombre(obj.responsable_acciones)

    def get_notificado_por_nombre(self, obj):
        return _nombre(obj.notificado_por)

    def get_responsables_nombres(self, obj):
        return [_nombre(u) for u in obj.responsables.all()] if obj.pk else []

    def get_involucrados_nombres(self, obj):
        return [_nombre(u) for u in obj.involucrados.all()] if obj.pk else []

    def get_sac_codigo(self, obj):
        h = obj.hallazgo
        return h.sac.codigo if (h and h.sac_id) else None

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas()

    def get_plazos(self, obj):
        return obj.plazos() if obj.pk else []

    def get_comunicaciones(self, obj):
        return ComunicacionQuejaSerializer(obj.comunicaciones.filter(is_active=True), many=True).data if obj.pk else []

    def get_adjuntos(self, obj):
        return AdjuntoQuejaSerializer(obj.adjuntos.filter(is_active=True), many=True).data if obj.pk else []

    def validate(self, data):
        inst = self.instance

        def val(c, defecto=None):
            return data[c] if c in data else (getattr(inst, c) if inst else defecto)
        errores = {}
        origen, motivo = val('origen'), (val('motivo', '') or '').strip()
        if origen and motivo and motivo not in MOTIVOS_QUEJA.get(origen, []):
            errores['motivo'] = ['Elija un motivo del origen indicado.']
        if val('medio_recepcion') == 'otros' and not (val('medio_otro', '') or '').strip():
            errores['medio_otro'] = ['Indique el otro medio de recepción.']
        if val('plazo_ampliado', False):
            if not (val('motivo_ampliacion', '') or '').strip():
                errores['motivo_ampliacion'] = ['Indique el motivo de la ampliación del plazo.']
            if not val('fecha_compromiso'):
                errores['fecha_compromiso'] = ['Indique la nueva fecha comprometida con el cliente.']
        if bool((val('certificado_nuevo', '') or '').strip()) != bool((val('certificado_original', '') or '').strip()):
            errores['certificado_nuevo'] = ['El nuevo certificado debe indicar el certificado original al que reemplaza.']
        from django.utils import timezone
        f = data.get('fecha_recepcion')
        if f and f > timezone.now():
            errores['fecha_recepcion'] = ['La fecha de recepción no puede ser futura.']
        if errores:
            raise serializers.ValidationError(errores)
        return data


class QuejaListaSerializer(serializers.ModelSerializer):
    """Columnas del Registro de Seguimiento de Quejas."""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    resultado_display = serializers.CharField(source='get_resultado_display', read_only=True)
    origen_display = serializers.CharField(source='get_origen_display', read_only=True)
    recibido_por_nombre = serializers.SerializerMethodField()
    alerta = serializers.SerializerMethodField()

    class Meta:
        model = Queja
        fields = ['id', 'codigo', 'fecha_recepcion', 'orden_trabajo', 'empresa', 'contacto', 'descripcion',
                  'recibido_por_nombre', 'resultado', 'resultado_display', 'dentro_alcance', 'estado',
                  'estado_display', 'origen_display', 'motivo', 'observaciones', 'alerta']

    def get_recibido_por_nombre(self, obj):
        return _nombre(obj.recibido_por)

    def get_alerta(self, obj):
        """El plazo más urgente sin cumplir (vencido o por vencer)."""
        for p in obj.plazos():
            if p['estado'] in ('vencido', 'por_vencer'):
                return {'nombre': p['nombre'], 'estado': p['estado']}
        return None
