"""eSYNAPSE 360 — Serializers de M6 Gestión Documental."""
from rest_framework import serializers

from .models import Documento, VerificacionExterna, VersionDocumento
from .models import NORMAS_APLICABLES


class FirmaVersionSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    firmante = serializers.SerializerMethodField()

    class Meta:
        from .models import FirmaVersion
        model = FirmaVersion
        fields = ['id', 'rol', 'rol_display', 'firmante', 'cargo', 'ip', 'hash_archivo', 'created_at']

    def get_firmante(self, obj):
        return obj.usuario.get_full_name() or obj.usuario.username


class ObservacionVersionSerializer(serializers.ModelSerializer):
    etapa_display = serializers.CharField(source='get_etapa_display', read_only=True)
    accion_display = serializers.CharField(source='get_accion_display', read_only=True)
    autor = serializers.SerializerMethodField()
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        from .models import ObservacionVersion
        model = ObservacionVersion
        fields = ['id', 'etapa', 'etapa_display', 'accion', 'accion_display',
                  'comentarios', 'archivo_url', 'autor', 'resuelta', 'created_at']

    def get_autor(self, obj):
        u = obj.created_by
        return (u.get_full_name() or u.username) if u else None

    def get_archivo_url(self, obj):
        return obj.archivo.url if obj.archivo else None


class ArchivoVersionSerializer(serializers.ModelSerializer):
    origen_display = serializers.CharField(source='get_origen_display', read_only=True)
    autor = serializers.SerializerMethodField()
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        from .models import ArchivoVersion
        model = ArchivoVersion
        fields = ['id', 'origen', 'origen_display', 'etapa', 'archivo_url',
                  'hash_archivo', 'autor', 'created_at']

    def get_autor(self, obj):
        u = obj.created_by
        return (u.get_full_name() or u.username) if u else None

    def get_archivo_url(self, obj):
        return obj.archivo.url if obj.archivo else None


class VersionDocumentoSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    elaborado_por_nombre = serializers.SerializerMethodField()
    revisado_por_nombre = serializers.SerializerMethodField()
    aprobado_por_nombre = serializers.SerializerMethodField()
    archivo_url = serializers.SerializerMethodField()
    archivo_publicado_url = serializers.SerializerMethodField()
    firmas = FirmaVersionSerializer(many=True, read_only=True)
    observaciones = ObservacionVersionSerializer(many=True, read_only=True)
    historial_archivos = ArchivoVersionSerializer(many=True, read_only=True)

    class Meta:
        model = VersionDocumento
        fields = ['id', 'version', 'archivo', 'archivo_url', 'archivo_publicado_url',
                  'hash_publicado', 'firmas', 'observaciones', 'resumen_cambios', 'estado',
                  'estado_display', 'elaborado_por_nombre', 'revisado_por_nombre',
                  'aprobado_por_nombre', 'comentarios_revision', 'fecha_revision',
                  'fecha_aprobacion', 'fecha_vigencia', 'fecha_proxima_revision',
                  'requiere_recarga', 'historial_archivos', 'created_at']
        read_only_fields = ['estado', 'fecha_revision', 'fecha_aprobacion',
                            'fecha_vigencia', 'fecha_proxima_revision']

    def _nombre(self, usuario):
        if not usuario:
            return None
        return usuario.get_full_name() or usuario.username

    def get_elaborado_por_nombre(self, obj):
        return self._nombre(obj.elaborado_por)

    def get_revisado_por_nombre(self, obj):
        return self._nombre(obj.revisado_por)

    def get_aprobado_por_nombre(self, obj):
        return self._nombre(obj.aprobado_por)

    def get_archivo_url(self, obj):
        # URL relativa: el frontend la sirve por su propio origen (proxy /media de Vite),
        # necesario para que el visor de PDF en iframe funcione con SAMEORIGIN.
        return obj.archivo.url if obj.archivo else None

    def get_archivo_publicado_url(self, obj):
        return obj.archivo_publicado.url if obj.archivo_publicado else None


class VerificacionExternaSerializer(serializers.ModelSerializer):
    verificado_por = serializers.SerializerMethodField()

    class Meta:
        model = VerificacionExterna
        fields = ['id', 'vigente', 'observaciones', 'verificado_por', 'created_at']

    def get_verificado_por(self, obj):
        u = obj.created_by
        return (u.get_full_name() or u.username) if u else None


class DocumentoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    soporte_display = serializers.CharField(source='get_soporte_display', read_only=True)
    normas_aplicables = serializers.ListField(
        child=serializers.ChoiceField(choices=[c for c, _ in NORMAS_APLICABLES]),
        required=False, allow_empty=True,
    )
    normas_display = serializers.SerializerMethodField()
    origen_display = serializers.CharField(source='get_origen_display', read_only=True)
    verificaciones = VerificacionExternaSerializer(many=True, read_only=True)
    # Solo creación de externos: etiqueta de edición del emisor (ej: "2017", "Rev. 03")
    edicion = serializers.CharField(write_only=True, required=False, allow_blank=True)
    fecha_aprobacion = serializers.DateField(write_only=True, required=False, allow_null=True)
    version_vigente = serializers.SerializerMethodField()
    version_en_proceso = serializers.SerializerMethodField()
    creado_por = serializers.SerializerMethodField()
    actualizado_por = serializers.SerializerMethodField()
    padre = serializers.PrimaryKeyRelatedField(queryset=Documento.objects.all(), required=False, allow_null=True)
    padre_codigo = serializers.SerializerMethodField()
    padre_titulo = serializers.SerializerMethodField()
    versiones = VersionDocumentoSerializer(many=True, read_only=True)
    # Solo para creación: archivo de la versión 1.0
    archivo = serializers.FileField(write_only=True, required=True)

    class Meta:
        model = Documento
        fields = ['id', 'codigo', 'titulo', 'tipo', 'tipo_display', 'proceso',
                  'normas_aplicables', 'normas_display', 'soporte', 'soporte_display',
                  'origen', 'origen_display', 'entidad_emisora', 'dias_verificacion',
                  'archivado', 'fecha_archivado',
                  'ultima_verificacion', 'verificaciones',
                  'objetivo', 'alcance', 'meses_revision', 'anos_retencion', 'is_active', 'version_vigente',
                  'version_en_proceso', 'versiones', 'archivo', 'edicion', 'fecha_aprobacion',
                  'padre', 'padre_codigo', 'padre_titulo',
                  'creado_por', 'actualizado_por', 'created_at', 'updated_at']
        read_only_fields = ['is_active', 'archivado', 'fecha_archivado', 'ultima_verificacion']

    def get_normas_display(self, obj):
        mapa = dict(NORMAS_APLICABLES)
        return [mapa.get(n, n) for n in (obj.normas_aplicables or [])]

    def get_version_vigente(self, obj):
        v = obj.version_vigente
        return VersionDocumentoSerializer(v, context=self.context).data if v else None

    def get_version_en_proceso(self, obj):
        v = obj.version_en_proceso
        return VersionDocumentoSerializer(v, context=self.context).data if v else None

    def _persona(self, u):
        return (u.get_full_name() or u.username) if u else None

    def get_creado_por(self, obj):
        return self._persona(obj.created_by)

    def get_actualizado_por(self, obj):
        return self._persona(obj.updated_by or obj.created_by)

    def get_padre_codigo(self, obj):
        return obj.padre.codigo if obj.padre else None

    def get_padre_titulo(self, obj):
        return obj.padre.titulo if obj.padre else None

    def validate_codigo(self, value):
        qs = Documento.objects.filter(codigo__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un documento con este código')
        return value

    def validate(self, data):
        if data.get('origen') == 'externo' and not (data.get('entidad_emisora') or '').strip():
            raise serializers.ValidationError(
                {'entidad_emisora': 'Los documentos externos requieren la entidad emisora.'})
        return data

    def create(self, validated_data):
        """
        Interno: crea la Ver. 00 en estado En elaboración (flujo M6).
        Externo: la edición del emisor queda Vigente de inmediato — Metrindust
        no aprueba normas ajenas, solo las adopta y controla su vigencia (6.7).
        """
        archivo = validated_data.pop('archivo')
        edicion = (validated_data.pop('edicion', '') or '').strip()
        fecha_aprob = validated_data.pop('fecha_aprobacion', None)
        request = self.context.get('request')
        documento = Documento.objects.create(**validated_data)
        from django.core.files.base import ContentFile
        from .firmas import hash_sha256
        from .models import ArchivoVersion

        def _bitacora_inicial(v, origen):
            v.archivo.open('rb'); cont = v.archivo.read(); v.archivo.close()
            ArchivoVersion.objects.create(
                version=v, origen=origen, etapa=v.estado,
                hash_archivo=hash_sha256(cont),
                archivo=ContentFile(cont, name=v.archivo.name.split('/')[-1]))

        if documento.origen == 'externo':
            from django.utils import timezone
            from datetime import datetime, time
            fa_dt = None
            if fecha_aprob:
                fa_dt = datetime.combine(fecha_aprob, time.min)
                if timezone.is_naive(fa_dt):
                    try:
                        fa_dt = timezone.make_aware(fa_dt)
                    except Exception:
                        pass
            v = VersionDocumento.objects.create(
                documento=documento,
                version=edicion or '00',
                archivo=archivo,
                estado='vigente',
                fecha_vigencia=fecha_aprob or timezone.now().date(),
                fecha_aprobacion=fa_dt,
                elaborado_por=request.user if request else None,
            )
            _bitacora_inicial(v, 'nueva_version')
        else:
            v = VersionDocumento.objects.create(
                documento=documento,
                version='00',
                archivo=archivo,
                estado='borrador',
                elaborado_por=request.user if request else None,
            )
            _bitacora_inicial(v, 'elaboracion')
        return documento

    def update(self, instance, validated_data):
        validated_data.pop('archivo', None)  # el archivo se cambia vía nueva versión
        validated_data.pop('edicion', None)
        validated_data.pop('origen', None)   # el origen no se cambia después de creado
        nuevo_codigo = validated_data.get('codigo')
        if nuevo_codigo and nuevo_codigo != instance.codigo:
            tiene_firmas = instance.versiones.filter(firmas__isnull=False).exists()
            tiene_publicadas = instance.versiones.filter(
                estado__in=['vigente', 'obsoleto']).exists()
            if tiene_firmas or tiene_publicadas:
                raise serializers.ValidationError({
                    'codigo': 'No puede cambiarse el código: el documento ya tiene firmas o '
                              'versiones publicadas con ese código estampado. '
                              'Para recodificar, archívelo y cree el documento con el código nuevo.'})
        return super().update(instance, validated_data)


class DocumentoListaSerializer(serializers.ModelSerializer):
    """Versión liviana para la tabla."""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_actual = serializers.SerializerMethodField()
    version_actual = serializers.SerializerMethodField()
    fecha_proxima_revision = serializers.SerializerMethodField()
    fecha_aprobacion = serializers.SerializerMethodField()
    proceso_paralelo = serializers.SerializerMethodField()
    soporte_display = serializers.CharField(source='get_soporte_display', read_only=True)
    normas_display = serializers.SerializerMethodField()
    origen_display = serializers.CharField(source='get_origen_display', read_only=True)
    creado_por = serializers.SerializerMethodField()
    actualizado_por = serializers.SerializerMethodField()
    padre_codigo = serializers.SerializerMethodField()
    padre_titulo = serializers.SerializerMethodField()

    class Meta:
        model = Documento
        fields = ['id', 'codigo', 'titulo', 'tipo', 'tipo_display', 'proceso', 'padre_codigo', 'padre_titulo',
                  'normas_display', 'soporte', 'soporte_display', 'origen', 'origen_display',
                  'entidad_emisora', 'ultima_verificacion', 'is_active', 'archivado',
                  'estado_actual', 'version_actual', 'proceso_paralelo',
                  'fecha_aprobacion', 'fecha_proxima_revision', 'anos_retencion',
                  'dias_verificacion', 'creado_por', 'actualizado_por', 'created_at', 'updated_at']

    def get_estado_actual(self, obj):
        # La versión OFICIAL manda: si hay vigente, su estado; si no, la que esté en proceso
        v = obj.version_vigente or obj.version_en_proceso
        return v.get_estado_display() if v else '—'

    def get_version_actual(self, obj):
        v = obj.version_vigente or obj.version_en_proceso
        return v.version if v else None

    def get_proceso_paralelo(self, obj):
        """Si hay vigente Y una nueva versión en camino, se informa aparte."""
        vv, vp = obj.version_vigente, obj.version_en_proceso
        if vv and vp:
            return {'version': vp.version, 'estado': vp.get_estado_display()}
        return None

    def get_fecha_proxima_revision(self, obj):
        v = obj.version_vigente
        return v.fecha_proxima_revision if v else None

    def get_fecha_aprobacion(self, obj):
        v = obj.version_vigente
        return v.fecha_aprobacion.date() if v and v.fecha_aprobacion else None

    def get_creado_por(self, obj):
        u = obj.created_by
        return (u.get_full_name() or u.username) if u else None

    def get_actualizado_por(self, obj):
        u = obj.updated_by or obj.created_by
        return (u.get_full_name() or u.username) if u else None

    def get_padre_codigo(self, obj):
        return obj.padre.codigo if obj.padre else None

    def get_padre_titulo(self, obj):
        return obj.padre.titulo if obj.padre else None

    def get_normas_display(self, obj):
        mapa = dict(NORMAS_APLICABLES)
        return [mapa.get(n, n) for n in (obj.normas_aplicables or [])]


# ============================================================
# M8 — HALLAZGOS
# ============================================================
from .models import Hallazgo  # noqa: E402


class HallazgoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    cerrado_por_nombre = serializers.SerializerMethodField()
    registrado_por = serializers.SerializerMethodField()
    evidencia_url = serializers.SerializerMethodField()
    sac = serializers.SerializerMethodField()
    puede_generar_sac = serializers.SerializerMethodField()

    class Meta:
        model = Hallazgo
        fields = ['id', 'codigo', 'tipo', 'tipo_display', 'fuente', 'fuente_display',
                  'proceso', 'descripcion', 'requisito', 'lugar', 'fecha_deteccion',
                  'evidencia', 'evidencia_url', 'responsable', 'responsable_nombre',
                  'estado', 'estado_display', 'analisis', 'correccion',
                  'comentarios_cierre', 'cerrado_por_nombre', 'fecha_cierre',
                  'requiere_ac', 'is_active', 'registrado_por', 'sac', 'puede_generar_sac',
                  'created_at', 'updated_at']
        read_only_fields = ['codigo', 'estado', 'comentarios_cierre', 'fecha_cierre',
                            'requiere_ac', 'is_active']
        extra_kwargs = {'evidencia': {'write_only': True, 'required': False}}

    def _nombre(self, u):
        return (u.get_full_name() or u.username) if u else None

    def get_responsable_nombre(self, obj):
        return self._nombre(obj.responsable)

    def get_cerrado_por_nombre(self, obj):
        return self._nombre(obj.cerrado_por)

    def get_registrado_por(self, obj):
        return self._nombre(obj.created_by)

    def get_evidencia_url(self, obj):
        return obj.evidencia.url if obj.evidencia else None

    def _sac_activa(self, obj):
        return obj.solicitudes_ac.filter(is_active=True).order_by('-id').first()

    def get_sac(self, obj):
        sac = self._sac_activa(obj)
        if not sac:
            return None
        return {'id': sac.id, 'codigo': sac.codigo, 'estado': sac.estado,
                'estado_display': sac.get_estado_display()}

    def get_puede_generar_sac(self, obj):
        # Solo las No Conformidades generan SAC, y solo si no hay una activa.
        return obj.tipo in ('nc_mayor', 'nc_menor') and self._sac_activa(obj) is None


class HallazgoListaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Hallazgo
        fields = ['id', 'codigo', 'tipo', 'tipo_display', 'fuente_display', 'proceso',
                  'fecha_deteccion', 'estado', 'estado_display', 'responsable_nombre',
                  'requiere_ac', 'is_active']

    def get_responsable_nombre(self, obj):
        u = obj.responsable
        return (u.get_full_name() or u.username) if u else None


# ============================================================
# M9 — SOLICITUDES DE ACCIÓN CORRECTIVA
# ============================================================
from .models import AccionSAC, SolicitudAC  # noqa: E402


class AccionSACSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    evidencia_url = serializers.SerializerMethodField()

    class Meta:
        model = AccionSAC
        fields = ['id', 'tipo', 'tipo_display', 'descripcion', 'fecha_propuesta',
                  'responsable', 'responsable_nombre', 'estado', 'estado_display',
                  'fecha_completada', 'verificacion', 'evidencia_url']
        read_only_fields = ['estado', 'fecha_completada', 'verificacion']

    def get_responsable_nombre(self, obj):
        u = obj.responsable
        return (u.get_full_name() or u.username) if u else None

    def get_evidencia_url(self, obj):
        return obj.evidencia.url if obj.evidencia else None


class SolicitudACSerializer(serializers.ModelSerializer):
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    significancia_display = serializers.CharField(source='get_significancia_display', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    verificador_nombre = serializers.SerializerMethodField()
    registrado_por = serializers.SerializerMethodField()
    hallazgo_codigo = serializers.CharField(source='hallazgo.codigo', read_only=True)
    normas_display = serializers.SerializerMethodField()
    acciones = AccionSACSerializer(many=True, read_only=True)
    normas_aplicables = serializers.ListField(
        child=serializers.ChoiceField(choices=[c for c, _ in NORMAS_APLICABLES]),
        required=False, allow_empty=True)

    class Meta:
        model = SolicitudAC
        fields = ['id', 'codigo', 'hallazgo', 'hallazgo_codigo', 'fuente', 'fuente_display',
                  'fuente_detalle', 'normas_aplicables', 'normas_display', 'auditor',
                  'auditado', 'requisito_auditado', 'descripcion_nc', 'significancia',
                  'significancia_display', 'analisis_extension', 'requiere_ac',
                  'justificacion_evaluacion', 'porques', 'causa_raiz',
                  'aplica_cambios_sig', 'aplica_actualizar_riesgos',
                  'responsable', 'responsable_nombre', 'verificador', 'verificador_nombre',
                  'estado', 'estado_display', 'evaluacion_eficacia', 'resultado_eficaz',
                  'fecha_verificacion', 'fecha_cierre', 'is_active', 'registrado_por',
                  'acciones', 'created_at', 'updated_at']
        read_only_fields = ['codigo', 'estado', 'significancia', 'analisis_extension',
                            'requiere_ac', 'justificacion_evaluacion', 'porques', 'causa_raiz',
                            'aplica_cambios_sig', 'aplica_actualizar_riesgos', 'verificador',
                            'evaluacion_eficacia', 'resultado_eficaz', 'fecha_verificacion',
                            'fecha_cierre', 'is_active']

    def _nombre(self, u):
        return (u.get_full_name() or u.username) if u else None

    def get_responsable_nombre(self, obj):
        return self._nombre(obj.responsable)

    def get_verificador_nombre(self, obj):
        return self._nombre(obj.verificador)

    def get_registrado_por(self, obj):
        return self._nombre(obj.created_by)

    def get_normas_display(self, obj):
        mapa = dict(NORMAS_APLICABLES)
        return [mapa.get(n, n) for n in (obj.normas_aplicables or [])]


class SolicitudACListaSerializer(serializers.ModelSerializer):
    """Columnas del Seguimiento de acciones."""
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    hallazgo_codigo = serializers.CharField(source='hallazgo.codigo', read_only=True)
    avance_acciones = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudAC
        fields = ['id', 'codigo', 'fuente_display', 'descripcion_nc', 'responsable_nombre',
                  'estado', 'estado_display', 'significancia', 'requiere_ac', 'fecha_cierre',
                  'hallazgo_codigo', 'avance_acciones', 'is_active', 'created_at']

    def get_responsable_nombre(self, obj):
        u = obj.responsable
        return (u.get_full_name() or u.username) if u else None

    def get_avance_acciones(self, obj):
        total = obj.acciones.count()
        hechas = obj.acciones.filter(estado='completada').count()
        return f'{hechas}/{total}' if total else '—'


# ============================================================
# M10 — AUDITORÍAS INTERNAS
# ============================================================
from .models import (  # noqa: E402
    ActaAuditoria, Auditoria, EquipoAuditoria, ItemVerificacion,
    ListaVerificacion, ProgramaAuditoria, RequisitoNorma,
)


class RequisitoNormaSerializer(serializers.ModelSerializer):
    norma_display = serializers.CharField(source='get_norma_display', read_only=True)

    class Meta:
        model = RequisitoNorma
        fields = ['id', 'norma', 'norma_display', 'codigo', 'titulo', 'es_seccion', 'orden']


class ItemVerificacionSerializer(serializers.ModelSerializer):
    resultado_display = serializers.CharField(source='get_resultado_display', read_only=True)

    class Meta:
        model = ItemVerificacion
        fields = ['id', 'codigo', 'titulo', 'es_seccion', 'orden', 'resultado',
                  'resultado_display', 'evidencia', 'observacion']
        read_only_fields = ['codigo', 'titulo', 'es_seccion', 'orden']


class ListaVerificacionSerializer(serializers.ModelSerializer):
    norma_display = serializers.CharField(source='get_norma_display', read_only=True)
    items = ItemVerificacionSerializer(many=True, read_only=True)
    avance = serializers.SerializerMethodField()

    class Meta:
        model = ListaVerificacion
        fields = ['id', 'norma', 'norma_display', 'items', 'avance']

    def get_avance(self, obj):
        its = obj.items.filter(es_seccion=False)
        total = its.count()
        evaluados = its.exclude(resultado='pendiente').count()
        return f'{evaluados}/{total}' if total else '0/0'


class EquipoAuditoriaSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    nombre = serializers.SerializerMethodField()

    class Meta:
        model = EquipoAuditoria
        fields = ['id', 'usuario', 'nombre_externo', 'nombre', 'rol', 'rol_display', 'cargo']

    def get_nombre(self, obj):
        if obj.usuario:
            return obj.usuario.get_full_name() or obj.usuario.username
        return obj.nombre_externo


class ActaAuditoriaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = ActaAuditoria
        fields = ['id', 'tipo', 'tipo_display', 'participantes', 'contenido',
                  'observaciones_auditado', 'archivo_url', 'created_at']

    def get_archivo_url(self, obj):
        return obj.archivo.url if obj.archivo else None


class AuditoriaListaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    modalidad_display = serializers.CharField(source='get_modalidad_display', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    auditor_lider_nombre = serializers.SerializerMethodField()
    normas_display = serializers.SerializerMethodField()
    hallazgos_count = serializers.SerializerMethodField()

    class Meta:
        model = Auditoria
        fields = ['id', 'codigo', 'tipo', 'tipo_display', 'estado', 'estado_display',
                  'modalidad', 'modalidad_display', 'normas_display', 'areas_procesos',
                  'auditor_lider_nombre', 'fecha_programada', 'fecha_inicio', 'fecha_fin',
                  'mes_programado', 'hallazgos_count', 'is_active', 'created_at']

    def get_auditor_lider_nombre(self, obj):
        u = obj.auditor_lider
        return (u.get_full_name() or u.username) if u else None

    def get_normas_display(self, obj):
        mapa = dict(NORMAS_APLICABLES)
        return [mapa.get(n, n) for n in (obj.normas_aplicables or [])]

    def get_hallazgos_count(self, obj):
        return obj.hallazgos.filter(is_active=True).count()


class AuditoriaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    modalidad_display = serializers.CharField(source='get_modalidad_display', read_only=True)
    auditor_lider_nombre = serializers.SerializerMethodField()
    normas_display = serializers.SerializerMethodField()
    programa_anio = serializers.IntegerField(source='programa.anio', read_only=True)
    equipo = EquipoAuditoriaSerializer(many=True, read_only=True)
    actas = ActaAuditoriaSerializer(many=True, read_only=True)
    listas = ListaVerificacionSerializer(many=True, read_only=True)
    hallazgos = serializers.SerializerMethodField()
    normas_aplicables = serializers.ListField(
        child=serializers.ChoiceField(choices=[c for c, _ in NORMAS_APLICABLES]),
        required=False, allow_empty=True)

    class Meta:
        model = Auditoria
        fields = ['id', 'codigo', 'programa', 'programa_anio', 'tipo', 'tipo_display',
                  'normas_aplicables', 'normas_display', 'objetivo', 'alcance', 'criterios',
                  'documentos_referencia', 'areas_procesos', 'modalidad', 'modalidad_display',
                  'auditor_lider', 'auditor_lider_nombre', 'mes_programado', 'fecha_programada',
                  'fecha_inicio', 'fecha_fin', 'reprogramada', 'motivo_reprogramacion',
                  'estado', 'estado_display', 'fortalezas', 'debilidades', 'conclusiones',
                  'fecha_informe', 'equipo', 'actas', 'listas', 'hallazgos', 'is_active',
                  'created_at', 'updated_at']
        read_only_fields = ['codigo', 'estado', 'fecha_informe', 'is_active', 'reprogramada']

    def get_auditor_lider_nombre(self, obj):
        u = obj.auditor_lider
        return (u.get_full_name() or u.username) if u else None

    def get_normas_display(self, obj):
        mapa = dict(NORMAS_APLICABLES)
        return [mapa.get(n, n) for n in (obj.normas_aplicables or [])]

    def get_hallazgos(self, obj):
        return [{
            'id': h.id, 'codigo': h.codigo, 'tipo': h.tipo,
            'tipo_display': h.get_tipo_display(), 'estado': h.get_estado_display(),
            'descripcion': h.descripcion, 'requisito': h.requisito,
            'requiere_ac': h.requiere_ac,
        } for h in obj.hallazgos.filter(is_active=True).order_by('id')]


class ProgramaAuditoriaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    auditorias = AuditoriaListaSerializer(many=True, read_only=True)

    class Meta:
        model = ProgramaAuditoria
        fields = ['id', 'anio', 'estado', 'estado_display', 'observaciones',
                  'auditorias', 'is_active', 'created_at']
        read_only_fields = ['estado']


# ============================================================
# M13 — EQUIPOS
# ============================================================
from .models import (  # noqa: E402
    ActividadPrograma, CartaTrazabilidad, Equipo, InformeEquipo, MovimientoEquipo,
    RegistroEquipo,
)


class ActividadProgramaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = ActividadPrograma
        fields = ['id', 'tipo', 'tipo_display', 'anio', 'frecuencia', 'meses']


class MovimientoEquipoSerializer(serializers.ModelSerializer):
    motivo_display = serializers.CharField(source='get_motivo_display', read_only=True)
    estado_salida_display = serializers.CharField(source='get_estado_salida_display', read_only=True)
    estado_retorno_display = serializers.CharField(source='get_estado_retorno_display', read_only=True)

    class Meta:
        model = MovimientoEquipo
        fields = ['id', 'motivo', 'motivo_display', 'destino', 'solicitante',
                  'estado_salida', 'estado_salida_display', 'fecha_salida', 'responsable_salida',
                  'fecha_retorno', 'estado_retorno', 'estado_retorno_display',
                  'responsable_retorno', 'observaciones', 'created_at']


class InformeEquipoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = InformeEquipo
        fields = ['id', 'tipo', 'tipo_display', 'numero', 'solicitante', 'fecha_revision',
                  'fecha_emision', 'lugar', 'detalle', 'conclusiones', 'conforme',
                  'archivo_url', 'responsable', 'created_at']
        read_only_fields = ['numero']

    def get_archivo_url(self, obj):
        return obj.archivo.url if obj.archivo else None


class RegistroEquipoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = RegistroEquipo
        fields = ['id', 'tipo', 'tipo_display', 'frecuencia', 'numero_documento',
                  'descripcion', 'fecha', 'fecha_proxima', 'observaciones', 'vb',
                  'archivo_url', 'created_at']

    def get_archivo_url(self, obj):
        return obj.archivo.url if obj.archivo else None


class EquipoListaSerializer(serializers.ModelSerializer):
    magnitud_display = serializers.CharField(source='magnitud', read_only=True)
    clasificacion_display = serializers.CharField(source='clasificacion', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    calibracion_vigente = serializers.BooleanField(read_only=True)
    es_patron = serializers.BooleanField(read_only=True)

    class Meta:
        model = Equipo
        # Columnas del Inventario
        fields = ['id', 'codigo', 'nombre', 'magnitud', 'magnitud_display', 'clasificacion',
                  'clasificacion_display', 'marca', 'modelo', 'serie', 'cantidad',
                  'clase_exactitud', 'resolucion', 'laboratorio',
                  'estado', 'estado_display', 'requiere_calibracion', 'n_certificado',
                  'proveedor_calibracion', 'periodicidad_dias', 'fecha_ultima_calibracion',
                  'fecha_proxima_calibracion', 'calibracion_vigente', 'es_patron',
                  'observaciones', 'is_active']


class EquipoSerializer(serializers.ModelSerializer):
    magnitud_display = serializers.CharField(source='magnitud', read_only=True)
    clasificacion_display = serializers.CharField(source='clasificacion', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    calibracion_vigente = serializers.BooleanField(read_only=True)
    es_patron = serializers.BooleanField(read_only=True)
    certificado_url = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()
    actualizado_por = serializers.SerializerMethodField()
    actividades = ActividadProgramaSerializer(many=True, read_only=True)
    movimientos = MovimientoEquipoSerializer(many=True, read_only=True)
    informes = InformeEquipoSerializer(many=True, read_only=True)
    registros = RegistroEquipoSerializer(many=True, read_only=True)

    class Meta:
        model = Equipo
        fields = ['id', 'codigo', 'magnitud', 'magnitud_display', 'clasificacion',
                  'clasificacion_display', 'nombre', 'marca', 'modelo', 'serie', 'procedencia',
                  'intervalo_indicacion', 'division_escala', 'clase_exactitud', 'resolucion',
                  'cantidad', 'cantidad_unidades', 'material', 'tipo_indicacion', 'laboratorio', 'instructivo', 'manual',
                  'criterio_aceptacion', 'exactitud_asignada', 'inicio_servicio',
                  'estado', 'estado_display', 'motivo_inoperativo', 'fecha_fuera_servicio',
                  'requiere_calibracion', 'n_certificado', 'proveedor_calibracion',
                  'fecha_ultima_calibracion', 'fecha_proxima_calibracion', 'periodicidad_dias',
                  'certificado_url', 'imagen', 'imagen_url', 'observaciones',
                  'calibracion_vigente', 'es_patron', 'actividades', 'movimientos', 'informes',
                  'registros', 'actualizado_por', 'is_active', 'created_at', 'updated_at']
        # 'codigo' ahora lo asigna el usuario al registrar el equipo.
        read_only_fields = ['estado', 'is_active']
        extra_kwargs = {'imagen': {'write_only': True, 'required': False}}

    def get_certificado_url(self, obj):
        return obj.certificado.url if obj.certificado else None

    def get_imagen_url(self, obj):
        return obj.imagen.url if obj.imagen else None

    def get_actualizado_por(self, obj):
        u = obj.updated_by or obj.created_by
        return (u.get_full_name() or u.username) if u else None


class CartaTrazabilidadSerializer(serializers.ModelSerializer):
    magnitud_display = serializers.CharField(source='magnitud', read_only=True)
    archivo_url = serializers.SerializerMethodField()

    nodos = serializers.SerializerMethodField()

    class Meta:
        model = CartaTrazabilidad
        fields = ['id', 'magnitud', 'magnitud_display', 'procedimiento_calibracion',
                  'contenido', 'archivo_url', 'fecha_actualizacion', 'is_active', 'created_at', 'nodos']
        read_only_fields = ['is_active']

    def get_archivo_url(self, obj):
        return obj.archivo.url if obj.archivo else None

    def get_nodos(self, obj):
        nodos = obj.nodos.filter(is_active=True).order_by('orden', 'id')
        return NodoTrazabilidadSerializer(nodos, many=True, context=self.context).data


class NodoTrazabilidadSerializer(serializers.ModelSerializer):
    """Eslabón del árbol de una carta de trazabilidad."""
    equipo_codigo = serializers.CharField(source='equipo.codigo', read_only=True, default='')
    equipo_nombre = serializers.CharField(source='equipo.nombre', read_only=True, default='')

    class Meta:
        from .models import NodoTrazabilidad
        model = NodoTrazabilidad
        fields = ['id', 'carta', 'padres', 'orden', 'equipo', 'equipo_codigo', 'equipo_nombre',
                  'entidad', 'descripcion', 'codigo', 'procedimiento', 'certificado',
                  'incertidumbre', 'nota', 'nivel', 'is_active']
        read_only_fields = ['is_active']


class ResultadoIntervaloSerializer(serializers.ModelSerializer):
    """Resultado anual de un punto (para el cálculo de deriva)."""
    class Meta:
        from .models import ResultadoIntervalo
        model = ResultadoIntervalo
        fields = ['id', 'punto', 'anio', 'resultado', 'incertidumbre', 'emp']


class PuntoIntervaloSerializer(serializers.ModelSerializer):
    """Punto nominal con sus resultados anuales y el cálculo OIML D10."""
    resultados = serializers.SerializerMethodField()
    calculo = serializers.SerializerMethodField()

    class Meta:
        from .models import PuntoIntervalo
        model = PuntoIntervalo
        fields = ['id', 'equipo', 'valor_nominal', 'orden',
                  'resultados', 'calculo', 'is_active']
        read_only_fields = ['is_active']

    def get_resultados(self, obj):
        rs = obj.resultados.order_by('anio', 'id')
        return ResultadoIntervaloSerializer(rs, many=True, context=self.context).data

    def get_calculo(self, obj):
        from .models import calcular_intervalo_punto
        datos = list(obj.resultados.values('anio', 'resultado', 'incertidumbre', 'emp'))
        return calcular_intervalo_punto(datos)


class MagnitudEquipoSerializer(serializers.ModelSerializer):
    """Catálogo gestionable de magnitudes (módulo Equipos)."""
    class Meta:
        from .models import MagnitudEquipo
        model = MagnitudEquipo
        fields = ['id', 'nombre', 'prefijo', 'orden', 'is_active']
        extra_kwargs = {'prefijo': {'required': False}}

    def create(self, validated_data):
        if not validated_data.get('prefijo'):
            nombre = validated_data.get('nombre', '')
            iniciales = ''.join(p[0] for p in str(nombre).split()[:2])
            validated_data['prefijo'] = (iniciales or str(nombre)[:2]).upper() or 'GEN'
        return super().create(validated_data)


class ClasificacionEquipoSerializer(serializers.ModelSerializer):
    """Catálogo gestionable de clasificaciones (módulo Equipos)."""
    es_patron = serializers.BooleanField(read_only=True)

    class Meta:
        from .models import ClasificacionEquipo
        model = ClasificacionEquipo
        fields = ['id', 'nombre', 'orden', 'is_active', 'es_patron']


class SolicitudCambioEquipoSerializer(serializers.ModelSerializer):
    """Solicitud de cambio de equipo pendiente de aprobación (solo lectura desde la API)."""
    entidad_display = serializers.CharField(source='get_entidad_display', read_only=True)
    operacion_display = serializers.CharField(source='get_operacion_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    equipo_codigo = serializers.CharField(source='equipo.codigo', read_only=True, default='')
    equipo_nombre = serializers.CharField(source='equipo.nombre', read_only=True, default='')
    solicitante = serializers.SerializerMethodField()
    aprobador = serializers.SerializerMethodField()
    archivo_url = serializers.SerializerMethodField()
    es_mio = serializers.SerializerMethodField()

    class Meta:
        from .models import SolicitudCambioEquipo
        model = SolicitudCambioEquipo
        fields = ['id', 'equipo', 'equipo_codigo', 'equipo_nombre', 'entidad', 'entidad_display',
                  'operacion', 'operacion_display', 'entidad_id', 'payload', 'archivo_url',
                  'resumen', 'estado', 'estado_display', 'observaciones', 'solicitante',
                  'aprobador', 'es_mio', 'resuelto_at', 'created_at']

    def get_es_mio(self, obj):
        req = self.context.get('request')
        return bool(req and obj.created_by_id and req.user.id == obj.created_by_id)

    def get_solicitante(self, obj):
        u = obj.created_by
        return (u.get_full_name() or u.username) if u else None

    def get_aprobador(self, obj):
        u = obj.resuelto_por
        return (u.get_full_name() or u.username) if u else None

    def get_archivo_url(self, obj):
        return obj.archivo.url if obj.archivo else None
