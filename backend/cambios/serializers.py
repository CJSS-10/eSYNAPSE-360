from rest_framework import serializers

from .models import (CLASIFICACIONES, CRITERIOS_EFICACIA, FUENTES_PLANIFICACION, IMPACTOS, MOTIVOS_ORIGEN,
                     ActividadCambio, Cambio, ComunicacionCambio, FotoCambio)


def _nombre(u):
    return (u.get_full_name() or u.username) if u else None


def _url(f):
    return f.url if f else None


class ActividadSerializer(serializers.ModelSerializer):
    responsable_nombre = serializers.SerializerMethodField()
    evidencia_url = serializers.SerializerMethodField()

    class Meta:
        model = ActividadCambio
        fields = ['id', 'orden', 'actividad', 'responsable', 'responsable_nombre', 'recursos', 'plazo', 'seguimiento',
                  'completada', 'fecha_completada', 'evidencia_url']

    def get_responsable_nombre(self, obj):
        return _nombre(obj.responsable)

    def get_evidencia_url(self, obj):
        return _url(obj.evidencia)


class ComunicacionSerializer(serializers.ModelSerializer):
    destinatario_display = serializers.CharField(source='get_destinatario_display', read_only=True)
    medio_display = serializers.CharField(source='get_medio_display', read_only=True)
    registrado_por = serializers.SerializerMethodField()
    evidencia_url = serializers.SerializerMethodField()

    class Meta:
        model = ComunicacionCambio
        fields = ['id', 'destinatario', 'destinatario_display', 'fecha', 'medio', 'medio_display', 'resumen',
                  'evidencia_url', 'registrado_por']

    def get_registrado_por(self, obj):
        return _nombre(obj.created_by)

    def get_evidencia_url(self, obj):
        return _url(obj.evidencia)


class FotoSerializer(serializers.ModelSerializer):
    momento_display = serializers.CharField(source='get_momento_display', read_only=True)
    url = serializers.SerializerMethodField()

    class Meta:
        model = FotoCambio
        fields = ['id', 'momento', 'momento_display', 'descripcion', 'url']

    def get_url(self, obj):
        return _url(obj.archivo)


class CambioSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    origen_display = serializers.CharField(source='get_origen_display', read_only=True)
    clasificacion_display = serializers.CharField(source='get_clasificacion_display', read_only=True)
    prevision_display = serializers.CharField(source='get_prevision_display', read_only=True)
    temporalidad_display = serializers.CharField(source='get_temporalidad_display', read_only=True)
    reversion_display = serializers.CharField(source='get_reversion_display', read_only=True)
    solicitante_nombre = serializers.SerializerMethodField()
    proceso_solicitante_nombre = serializers.CharField(source='proceso_solicitante.nombre', read_only=True, default=None)
    procesos_afectados_nombres = serializers.SerializerMethodField()
    responsable_evaluador_nombre = serializers.SerializerMethodField()
    responsable_evaluador_cargo = serializers.CharField(source='responsable_evaluador.cargo', read_only=True, default=None)
    equipo_evaluador_nombres = serializers.SerializerMethodField()
    resuelto_por_nombre = serializers.SerializerMethodField()
    responsable_implementacion_nombre = serializers.SerializerMethodField()
    responsable_implementacion_cargo = serializers.CharField(source='responsable_implementacion.cargo', read_only=True,
                                                             default=None)
    equipo_implementacion_nombres = serializers.SerializerMethodField()
    documentos_actualizados_info = serializers.SerializerMethodField()
    verificado_por_nombre = serializers.SerializerMethodField()
    cerrado_por_nombre = serializers.SerializerMethodField()
    sac_origen_codigo = serializers.CharField(source='sac_origen.codigo', read_only=True, default=None)
    sac_derivada_codigo = serializers.CharField(source='sac_derivada.codigo', read_only=True, default=None)
    etapas_abiertas = serializers.SerializerMethodField()
    requiere_planificacion = serializers.BooleanField(read_only=True)
    reversion_vencida = serializers.BooleanField(read_only=True)
    fin_temporal_por_nombre = serializers.SerializerMethodField()
    fin_temporal_evidencia_url = serializers.SerializerMethodField()
    cambio_origen_codigo = serializers.CharField(source='cambio_origen.codigo', read_only=True, default=None)
    cambios_permanentes = serializers.SerializerMethodField()
    queda_en_vigor = serializers.BooleanField(read_only=True)
    actividades = serializers.SerializerMethodField()
    comunicaciones = serializers.SerializerMethodField()
    fotos = serializers.SerializerMethodField()

    class Meta:
        model = Cambio
        fields = [
            'id', 'codigo', 'estado', 'estado_display',
            'solicitante', 'solicitante_nombre', 'proceso_solicitante', 'proceso_solicitante_nombre', 'fecha_solicitud',
            'prioridad', 'prioridad_display', 'origen', 'origen_display', 'motivo_origen', 'descripcion',
            'justificacion', 'sac_origen', 'sac_origen_codigo',
            'factibilidad_tecnica', 'aspectos_operativos', 'aspectos_financieros', 'procesos_afectados',
            'procesos_afectados_nombres', 'alcance', 'beneficios', 'impactos', 'riesgos', 'controles', 'consecuencias',
            'clasificacion', 'clasificacion_display', 'es_tecnico', 'afecta_clientes', 'responsable_evaluador',
            'responsable_evaluador_nombre', 'responsable_evaluador_cargo', 'equipo_evaluador',
            'equipo_evaluador_nombres',
            'resultado', 'resuelto_por', 'resuelto_por_nombre', 'fecha_resolucion', 'motivo_resolucion', 'historial',
            'fecha_planificacion', 'prevision', 'prevision_display', 'temporalidad', 'temporalidad_display',
            'fecha_reversion', 'fuentes', 'fuente_otro', 'responsable_implementacion',
            'responsable_implementacion_nombre', 'responsable_implementacion_cargo', 'plazo_implementacion',
            'equipo_implementacion', 'equipo_implementacion_nombres',
            'fecha_inicio_implementacion', 'documentos_actualizados', 'documentos_actualizados_info',
            'se_implemento', 'fue_eficaz', 'criterios_eficacia', 'verificacion', 'reversion', 'reversion_display',
            'detalle_reversion', 'fecha_reversion_real', 'sac_derivada', 'sac_derivada_codigo', 'fecha_verificacion',
            'verificado_por', 'verificado_por_nombre',
            'prorrogas', 'fin_temporal_fecha', 'fin_temporal_detalle', 'fin_temporal_evidencia_url',
            'fin_temporal_por', 'fin_temporal_por_nombre', 'cambio_origen', 'cambio_origen_codigo',
            'cambios_permanentes', 'queda_en_vigor',
            'cerrado_por', 'cerrado_por_nombre', 'fecha_cierre', 'reaperturas',
            'etapas_abiertas', 'requiere_planificacion', 'reversion_vencida', 'actividades', 'comunicaciones', 'fotos',
            'is_active', 'created_at',
        ]
        read_only_fields = ['codigo', 'estado', 'resultado', 'resuelto_por', 'fecha_resolucion', 'motivo_resolucion',
                            'historial', 'fecha_inicio_implementacion', 'fecha_verificacion', 'verificado_por',
                            'cerrado_por', 'fecha_cierre', 'reaperturas', 'is_active', 'prorrogas',
                            'fin_temporal_fecha', 'fin_temporal_detalle', 'fin_temporal_por', 'cambio_origen']

    def get_solicitante_nombre(self, obj):
        return _nombre(obj.solicitante)

    def get_procesos_afectados_nombres(self, obj):
        return [p.nombre for p in obj.procesos_afectados.all()] if obj.pk else []

    def get_responsable_evaluador_nombre(self, obj):
        return _nombre(obj.responsable_evaluador)

    def get_equipo_evaluador_nombres(self, obj):
        return [_nombre(u) for u in obj.equipo_evaluador.all()] if obj.pk else []

    def get_resuelto_por_nombre(self, obj):
        return _nombre(obj.resuelto_por)

    def get_responsable_implementacion_nombre(self, obj):
        return _nombre(obj.responsable_implementacion)

    def get_equipo_implementacion_nombres(self, obj):
        return [_nombre(u) for u in obj.equipo_implementacion.all()] if obj.pk else []

    def get_documentos_actualizados_info(self, obj):
        if not obj.pk:
            return []
        salida = []
        for d in obj.documentos_actualizados.all():
            vv, vp = d.version_vigente, d.version_en_proceso
            salida.append({'id': d.id, 'codigo': d.codigo, 'titulo': d.titulo,
                           'version_vigente': vv.version if vv else None,
                           'version_en_proceso': vp.version if vp else None})
        return salida

    def get_verificado_por_nombre(self, obj):
        return _nombre(obj.verificado_por)

    def get_cerrado_por_nombre(self, obj):
        return _nombre(obj.cerrado_por)

    def get_fin_temporal_por_nombre(self, obj):
        return _nombre(obj.fin_temporal_por)

    def get_fin_temporal_evidencia_url(self, obj):
        return _url(obj.fin_temporal_evidencia)

    def get_cambios_permanentes(self, obj):
        if not obj.pk:
            return []
        return [{'id': x.id, 'codigo': x.codigo, 'estado_display': x.get_estado_display()}
                for x in obj.cambios_permanentes.filter(is_active=True)]

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas()

    def get_actividades(self, obj):
        return ActividadSerializer(obj.actividades.filter(is_active=True), many=True).data if obj.pk else []

    def get_comunicaciones(self, obj):
        return ComunicacionSerializer(obj.comunicaciones.filter(is_active=True), many=True).data if obj.pk else []

    def get_fotos(self, obj):
        return FotoSerializer(obj.fotos.filter(is_active=True), many=True).data if obj.pk else []

    def validate(self, data):
        inst = self.instance

        def val(c, defecto=None):
            return data[c] if c in data else (getattr(inst, c) if inst else defecto)
        errores = {}
        origen, motivo = val('origen', 'interno'), (val('motivo_origen', '') or '').strip()
        if motivo and motivo not in MOTIVOS_ORIGEN.get(origen, []):
            errores['motivo_origen'] = ['Elija un motivo del origen indicado.']
        validos = {k for k, _ in IMPACTOS}
        if 'impactos' in data and any(x not in validos for x in data['impactos'] or []):
            errores['impactos'] = ['Impacto no válido.']
        validos = {k for k, _ in FUENTES_PLANIFICACION}
        if 'fuentes' in data and any(x not in validos for x in data['fuentes'] or []):
            errores['fuentes'] = ['Fuente no válida.']
        validos = {k for k, _ in CRITERIOS_EFICACIA}
        if 'criterios_eficacia' in data and any(x not in validos for x in data['criterios_eficacia'] or []):
            errores['criterios_eficacia'] = ['Criterio no válido.']
        if 'clasificacion' in data and data['clasificacion'] and data['clasificacion'] not in dict(CLASIFICACIONES):
            errores['clasificacion'] = ['Clasificación no válida.']
        from django.utils import timezone
        if data.get('fecha_solicitud') and data['fecha_solicitud'] > timezone.localdate():
            errores['fecha_solicitud'] = ['La fecha de solicitud no puede ser futura.']
        if errores:
            raise serializers.ValidationError(errores)
        return data


class CambioListaSerializer(serializers.ModelSerializer):
    """Columnas del Seguimiento de Cambios."""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    clasificacion_display = serializers.CharField(source='get_clasificacion_display', read_only=True)
    solicitante_nombre = serializers.SerializerMethodField()
    area = serializers.CharField(source='proceso_solicitante.nombre', read_only=True, default=None)
    responsable_implementacion_nombre = serializers.SerializerMethodField()
    resuelto_por_nombre = serializers.SerializerMethodField()
    cerrado_por_nombre = serializers.SerializerMethodField()
    reversion_vencida = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cambio
        fields = ['id', 'codigo', 'fecha_solicitud', 'solicitante_nombre', 'area', 'origen', 'descripcion',
                  'prioridad', 'prioridad_display', 'clasificacion', 'clasificacion_display',
                  'responsable_implementacion_nombre', 'resuelto_por_nombre', 'se_implemento', 'fue_eficaz',
                  'cerrado_por_nombre', 'fecha_cierre', 'estado', 'estado_display', 'temporalidad',
                  'fecha_reversion', 'reversion_vencida']

    def get_solicitante_nombre(self, obj):
        return _nombre(obj.solicitante)

    def get_responsable_implementacion_nombre(self, obj):
        return _nombre(obj.responsable_implementacion)

    def get_resuelto_por_nombre(self, obj):
        return _nombre(obj.resuelto_por) if obj.resultado == 'aprobado' else None

    def get_cerrado_por_nombre(self, obj):
        return _nombre(obj.cerrado_por)
