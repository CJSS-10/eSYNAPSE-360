"""eSYNAPSE 360 — Serializers de M6 Gestión Documental."""
from django.utils import timezone
from rest_framework import serializers

from .models import Documento, FormatoImpreso, VerificacionExterna, VersionDocumento
from .models import NORMAS_APLICABLES, NORMAS_LISTA


class FormatoImpresoSerializer(serializers.ModelSerializer):
    """Formato PDF del sistema y su vínculo con la lista maestra; incluye lo que
    imprimirá la caja de control para que la pantalla lo muestre."""
    documento_codigo = serializers.CharField(source='documento.codigo', read_only=True)
    documento_titulo = serializers.CharField(source='documento.titulo', read_only=True)
    control = serializers.SerializerMethodField()

    class Meta:
        model = FormatoImpreso
        fields = ['id', 'clave', 'nombre', 'modulo', 'codigo_sgc', 'documento',
                  'documento_codigo', 'documento_titulo', 'control', 'orden', 'is_active']
        read_only_fields = ['clave', 'nombre', 'modulo', 'codigo_sgc', 'orden', 'is_active']

    def get_control(self, obj):
        from .ficha_pdf import control_formato
        try:
            from core.models import ConfiguracionSistema
            cfg = ConfiguracionSistema.cargar()
        except Exception:
            cfg = None
        return control_formato(obj.codigo_sgc, cfg)

    def validate_documento(self, doc):
        if doc and not doc.is_active:
            raise serializers.ValidationError('El documento está inactivo.')
        return doc


def _baja(obj):
    """Quién dio de baja el registro y cuándo (su última modificación)."""
    u = getattr(obj, 'updated_by', None)
    return {'anulado_por': (u.get_full_name() or u.username) if u else '', 'anulado_en': obj.updated_at}


def _anulados(modelo, serializer, **filtro):
    return [{**serializer(o).data, **_baja(o)} for o in modelo.todos.filter(is_active=False, **filtro)
            .select_related('updated_by').order_by('-updated_at')]


class FirmaVersionSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    firmante = serializers.SerializerMethodField()

    class Meta:
        from .models import FirmaVersion
        model = FirmaVersion
        fields = ['id', 'rol', 'rol_display', 'firmante', 'cargo', 'ip', 'hash_archivo', 'created_at', 'vigente',
                  'anulada_en', 'motivo_anulacion']

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
    firmas_anuladas = serializers.SerializerMethodField()
    observaciones = ObservacionVersionSerializer(many=True, read_only=True)
    historial_archivos = ArchivoVersionSerializer(many=True, read_only=True)

    class Meta:
        model = VersionDocumento
        fields = ['id', 'version', 'archivo', 'archivo_url', 'archivo_publicado_url',
                  'hash_publicado', 'firmas', 'firmas_anuladas', 'observaciones', 'resumen_cambios', 'estado',
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

    def get_firmas_anuladas(self, obj):
        from .models import FirmaVersion
        return FirmaVersionSerializer(FirmaVersion.todos.filter(version=obj, vigente=False).select_related('usuario'),
                                      many=True).data

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
        fields = ['id', 'codigo', 'titulo', 'tipo', 'tipo_display', 'proceso', 'proceso_catalogo',
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
        no aprueba normas ajenas, solo las adopta y controla su vigencia.
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
                fecha_vigencia=fecha_aprob or timezone.localdate(),
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
        fields = ['id', 'codigo', 'titulo', 'tipo', 'tipo_display', 'proceso', 'proceso_catalogo', 'padre_codigo',
                  'padre_titulo',
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
        return timezone.localtime(v.fecha_aprobacion).date() if v and v.fecha_aprobacion else None

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


def responsable_tratamiento(h):
    """Responsable del tratamiento de un hallazgo: se designa donde se trata — al evaluar la solicitud de acción
    correctiva (no conformidades) o en Riesgos y oportunidades / mejora continua (observaciones y oportunidades de
    mejora). El campo propio del hallazgo solo se conserva para registros anteriores."""
    def nombre(u):
        return (u.get_full_name() or u.username) if u else None
    if h.sac_id and h.sac.responsable_id:
        return nombre(h.sac.responsable)
    for m in h.mejoras_derivadas.filter(is_active=True):
        if m.responsable_nombre:
            return m.responsable_nombre
    for r in h.riesgos_derivados.filter(is_active=True):
        nombres = [a.responsable_nombre for a in r.acciones.filter(is_active=True) if a.responsable_nombre]
        if nombres:
            return ', '.join(dict.fromkeys(nombres))
    return nombre(h.responsable)


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
    motivo_no_derivar = serializers.SerializerMethodField()
    etapas_abiertas = serializers.SerializerMethodField()
    registro_cerrado_motivo = serializers.SerializerMethodField()
    auditoria_codigo = serializers.SerializerMethodField()

    class Meta:
        model = Hallazgo
        fields = ['id', 'codigo', 'tipo', 'tipo_display', 'fuente', 'fuente_display',
                  'proceso', 'proceso_catalogo', 'descripcion', 'requisito', 'lugar', 'fecha_deteccion',
                  'evidencia', 'evidencia_url', 'responsable', 'responsable_nombre',
                  'estado', 'estado_display', 'analisis', 'correccion',
                  'comentarios_cierre', 'cerrado_por_nombre', 'fecha_cierre',
                  'requiere_ac', 'tratamiento', 'tratamiento_display', 'is_active', 'registrado_por',
                  'sac', 'puede_generar_sac', 'motivo_no_derivar', 'reclasificaciones', 'etapas_abiertas',
                  'registro_cerrado_motivo', 'auditoria', 'auditoria_codigo', 'created_at', 'updated_at']
        read_only_fields = ['codigo', 'estado', 'comentarios_cierre', 'fecha_cierre', 'analisis', 'correccion',
                            'requiere_ac', 'tratamiento', 'is_active', 'reclasificaciones', 'auditoria']
        extra_kwargs = {'evidencia': {'write_only': True, 'required': False}}

    def _nombre(self, u):
        return (u.get_full_name() or u.username) if u else None

    def get_responsable_nombre(self, obj):
        return responsable_tratamiento(obj)

    def get_cerrado_por_nombre(self, obj):
        return self._nombre(obj.cerrado_por)

    def get_registrado_por(self, obj):
        return self._nombre(obj.created_by)

    def get_evidencia_url(self, obj):
        return obj.evidencia.url if obj.evidencia else None

    tratamiento_display = serializers.CharField(source='get_tratamiento_display', read_only=True)

    def get_sac(self, obj):
        sac = obj.sac
        if not sac:
            return None
        return {'id': sac.id, 'codigo': sac.codigo, 'estado': sac.estado,
                'estado_display': sac.get_estado_display(),
                'es_origen': sac.hallazgo_id == obj.id}

    def get_motivo_no_derivar(self, obj):
        """Por qué la NC aún no puede derivarse a una solicitud (vacío = puede)."""
        if not obj.es_nc or obj.sac_id or obj.estado == 'cerrado':
            return ''
        a = obj.auditoria
        if a and a.estado not in ('en_informe', 'cerrada'):
            return f'En consolidación en la auditoría {a.codigo}: se deriva después de la reunión de cierre.'
        return ''

    def get_puede_generar_sac(self, obj):
        return obj.es_nc and not obj.sac_id and obj.estado != 'cerrado' and not self.get_motivo_no_derivar(obj)

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas()

    def get_registro_cerrado_motivo(self, obj):
        return '' if obj.registro_abierto() else obj.mensaje_registro_cerrado()

    def get_auditoria_codigo(self, obj):
        return obj.auditoria.codigo if obj.auditoria_id else None


class HallazgoListaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    sac_codigo = serializers.CharField(source='sac.codigo', read_only=True, default=None)

    class Meta:
        model = Hallazgo
        fields = ['id', 'codigo', 'tipo', 'tipo_display', 'fuente_display', 'proceso', 'proceso_catalogo',
                  'fecha_deteccion', 'estado', 'estado_display', 'responsable_nombre',
                  'requiere_ac', 'tratamiento', 'sac_codigo', 'is_active']

    def get_responsable_nombre(self, obj):
        return responsable_tratamiento(obj)


# ============================================================
# M9 — SOLICITUDES DE ACCIÓN CORRECTIVA
# ============================================================
from .models import AccionSAC, SolicitudAC  # noqa: E402


class AccionSACSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    evidencia_url = serializers.SerializerMethodField()
    editable = serializers.SerializerMethodField()
    reabrible = serializers.SerializerMethodField()

    class Meta:
        model = AccionSAC
        fields = ['id', 'tipo', 'tipo_display', 'descripcion', 'fecha_propuesta',
                  'responsable', 'responsable_nombre', 'estado', 'estado_display',
                  'fecha_completada', 'verificacion', 'evidencia_url', 'ciclo', 'editable',
                  'reabrible', 'reaperturas']
        read_only_fields = ['estado', 'fecha_completada', 'verificacion', 'ciclo', 'reaperturas']

    def get_responsable_nombre(self, obj):
        u = obj.responsable
        return (u.get_full_name() or u.username) if u else None

    def get_evidencia_url(self, obj):
        return obj.evidencia.url if obj.evidencia else None

    def get_editable(self, obj):
        return obj.editable() if obj.pk else False

    def get_reabrible(self, obj):
        return obj.reabrible() if obj.pk else False


class SolicitudACSerializer(serializers.ModelSerializer):
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    significancia_display = serializers.CharField(source='get_significancia_display', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    verificador_nombre = serializers.SerializerMethodField()
    registrado_por = serializers.SerializerMethodField()
    hallazgo_codigo = serializers.CharField(source='hallazgo.codigo', read_only=True)
    hallazgos_vinculados = serializers.SerializerMethodField()
    normas_display = serializers.SerializerMethodField()
    etapas_abiertas = serializers.SerializerMethodField()
    clasificacion = serializers.SerializerMethodField()
    acciones = serializers.SerializerMethodField()
    normas_aplicables = serializers.ListField(
        child=serializers.ChoiceField(choices=[c for c, _ in NORMAS_APLICABLES]),
        required=False, allow_empty=True)

    class Meta:
        model = SolicitudAC
        fields = ['id', 'codigo', 'hallazgo', 'hallazgo_codigo', 'fuente', 'fuente_display',
                  'fuente_detalle', 'normas_aplicables', 'normas_display', 'entidad_auditora', 'auditor',
                  'auditado', 'requisito_auditado', 'descripcion_nc', 'significancia',
                  'significancia_display', 'analisis_extension', 'requiere_ac',
                  'justificacion_evaluacion', 'porques', 'causa_raiz',
                  'aplica_cambios_sig', 'aplica_actualizar_riesgos',
                  'responsable', 'responsable_nombre', 'verificador', 'verificador_nombre',
                  'estado', 'estado_display', 'evaluacion_eficacia', 'resultado_eficaz',
                  'fecha_verificacion', 'fecha_cierre', 'is_active', 'registrado_por',
                  'acciones', 'hallazgos_vinculados', 'ciclo', 'ciclos_anteriores', 'etapas_abiertas',
                  'clasificacion', 'created_at', 'updated_at', 'fecha_registro',
                  'verificado_por', 'verificado_por_nombre', 'responsable_cierre_nombre']
        read_only_fields = ['codigo', 'estado', 'significancia', 'analisis_extension', 'ciclo', 'ciclos_anteriores',
                            'requiere_ac', 'justificacion_evaluacion', 'porques', 'causa_raiz',
                            'aplica_cambios_sig', 'aplica_actualizar_riesgos', 'verificador',
                            'evaluacion_eficacia', 'resultado_eficaz', 'fecha_verificacion',
                            'fecha_cierre', 'is_active', 'verificado_por']

    verificado_por_nombre = serializers.SerializerMethodField()
    responsable_cierre_nombre = serializers.SerializerMethodField()

    def validate_fecha_registro(self, valor):
        from django.utils import timezone
        if valor and valor > timezone.localdate():
            raise serializers.ValidationError('La fecha de registro no puede ser futura.')
        return valor

    def _nombre(self, u):
        return (u.get_full_name() or u.username) if u else None

    def get_verificado_por_nombre(self, obj):
        return self._nombre(obj.verificado_por or (obj.verificador if obj.fecha_verificacion else None))

    def get_responsable_cierre_nombre(self, obj):
        from .ficha_pdf import responsable_cierre_sac
        return responsable_cierre_sac(obj) or None

    def get_responsable_nombre(self, obj):
        return self._nombre(obj.responsable)

    def get_verificador_nombre(self, obj):
        return self._nombre(obj.verificador)

    def get_registrado_por(self, obj):
        return self._nombre(obj.created_by)

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas()

    def get_clasificacion(self, obj):
        return obj.clasificacion()

    def get_acciones(self, obj):
        return AccionSACSerializer(obj.acciones.filter(is_active=True).order_by('ciclo', 'fecha_propuesta', 'id'),
                                   many=True).data

    def get_hallazgos_vinculados(self, obj):
        """NC que trata la solicitud: la de origen y las ocurrencias sumadas."""
        return [{'id': h.id, 'codigo': h.codigo, 'tipo_display': h.get_tipo_display(),
                 'descripcion': h.descripcion, 'fecha_deteccion': h.fecha_deteccion,
                 'es_origen': h.id == obj.hallazgo_id}
                for h in obj.hallazgos_vinculados.filter(is_active=True).order_by('id')]

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
    clasificacion = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudAC
        fields = ['id', 'codigo', 'fuente_display', 'fuente_detalle', 'descripcion_nc', 'responsable_nombre',
                  'estado', 'estado_display', 'significancia', 'requiere_ac', 'fecha_cierre',
                  'hallazgo_codigo', 'clasificacion', 'avance_acciones', 'is_active', 'created_at']

    def get_clasificacion(self, obj):
        return obj.clasificacion()

    def get_responsable_nombre(self, obj):
        u = obj.responsable
        return (u.get_full_name() or u.username) if u else None

    def get_avance_acciones(self, obj):
        total = obj.acciones.filter(is_active=True).count()
        hechas = obj.acciones.filter(estado='completada', is_active=True).count()
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
        fields = ['id', 'norma', 'norma_display', 'codigo', 'titulo', 'es_seccion', 'bloque', 'orden']


class ItemVerificacionSerializer(serializers.ModelSerializer):
    resultado_display = serializers.CharField(source='get_resultado_display', read_only=True)
    hallazgo_codigo = serializers.SerializerMethodField()

    def get_hallazgo_codigo(self, obj):
        return obj.hallazgo.codigo if obj.hallazgo_id and obj.hallazgo.is_active else None

    class Meta:
        model = ItemVerificacion
        fields = ['id', 'codigo', 'titulo', 'es_seccion', 'bloque', 'formato', 'orden', 'resultado',
                  'resultado_display', 'documento_referencia', 'evidencia', 'observacion',
                  'hallazgo', 'hallazgo_codigo', 'motivo_descarte']
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


def _equipo_anulado(auditoria):
    return _anulados(EquipoAuditoria, EquipoAuditoriaSerializer, auditoria=auditoria)


class ActaAuditoriaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = ActaAuditoria
        fields = ['id', 'tipo', 'tipo_display', 'participantes', 'contenido', 'seccion3',
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
    programa_anio = serializers.IntegerField(source='programa.anio', read_only=True, default=None)
    programa_estado = serializers.CharField(source='programa.estado', read_only=True, default=None)

    class Meta:
        model = Auditoria
        fields = ['id', 'codigo', 'programa', 'programa_anio', 'programa_estado', 'tipo', 'tipo_display', 'estado', 'estado_display',
                  'modalidad', 'modalidad_display', 'normas_display', 'areas_procesos',
                  'auditor_lider_nombre', 'fecha_programada', 'fecha_inicio', 'fecha_fin',
                  'mes_programado', 'mes_reprogramado', 'clase', 'hallazgos_count', 'is_active', 'created_at']

    def get_auditor_lider_nombre(self, obj):
        return obj.nombre_lider() or None

    def get_normas_display(self, obj):
        mapa = dict(NORMAS_LISTA)
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
    programa_estado = serializers.CharField(source='programa.estado', read_only=True, default=None)
    equipo = EquipoAuditoriaSerializer(many=True, read_only=True)
    equipo_anulado = serializers.SerializerMethodField()
    actas = ActaAuditoriaSerializer(many=True, read_only=True)
    listas = ListaVerificacionSerializer(many=True, read_only=True)
    hallazgos = serializers.SerializerMethodField()
    # Qué etapas siguen abiertas (editables) según el estado: la pantalla
    # deshabilita las cerradas y el servidor rechaza cambios en ellas.
    etapas_abiertas = serializers.SerializerMethodField()
    plan_aprobado_por_nombre = serializers.SerializerMethodField()
    pendientes_clasificar = serializers.SerializerMethodField()
    normas_aplicables = serializers.ListField(
        child=serializers.ChoiceField(choices=[c for c, _ in NORMAS_LISTA]),
        required=False, allow_empty=True)

    class Meta:
        model = Auditoria
        fields = ['id', 'codigo', 'programa', 'programa_anio', 'programa_estado', 'tipo', 'tipo_display', 'clase',
                  'normas_aplicables', 'normas_display', 'requisitos_por_norma', 'observaciones_programa',
                  'objetivo', 'alcance', 'criterios',
                  'documentos_referencia', 'fecha_elaboracion_plan', 'areas_procesos', 'cronograma_entrevistas',
                  'observaciones_plan', 'lugar', 'personas_entrevistadas', 'modalidad', 'modalidad_display',
                  'auditor_lider', 'auditor_lider_nombre', 'mes_programado', 'mes_reprogramado', 'fecha_programada',
                  'fecha_inicio', 'fecha_fin', 'reprogramada', 'motivo_reprogramacion',
                  'estado', 'estado_display', 'fortalezas', 'debilidades', 'conclusiones',
                  'fecha_informe', 'equipo', 'equipo_anulado', 'actas', 'listas', 'hallazgos', 'etapas_abiertas', 'plan_aprobado_por', 'plan_aprobado_por_nombre',
                  'fecha_aprobacion_plan', 'pendientes_clasificar', 'is_active',
                  'created_at', 'updated_at']
        read_only_fields = ['codigo', 'estado', 'fecha_informe', 'is_active', 'reprogramada', 'mes_reprogramado',
                            'plan_aprobado_por', 'fecha_aprobacion_plan',
                            'auditor_lider']   # se define en el equipo auditor (rol líder)

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas()

    def get_auditor_lider_nombre(self, obj):
        return obj.nombre_lider() or None

    def get_normas_display(self, obj):
        mapa = dict(NORMAS_LISTA)
        return [mapa.get(n, n) for n in (obj.normas_aplicables or [])]

    def validate(self, data):
        """Una auditoría programada pertenece a un programa anual (si no, no
        aparece en ningún programa). Las extraordinarias pueden ir sin programa.
        No se mueve una auditoría a un programa aprobado (solo lectura)."""
        tipo = data['tipo'] if 'tipo' in data else (self.instance.tipo if self.instance else 'programada')
        programa = data['programa'] if 'programa' in data else (self.instance.programa if self.instance else None)
        # Se exige al crear o al cambiar programa/tipo; editar el plan de una
        # auditoría antigua sin programa no debe quedar bloqueado.
        toca_programa = not self.instance or 'programa' in data or 'tipo' in data
        if toca_programa and tipo == 'programada' and not programa:
            raise serializers.ValidationError({'programa': ['Una auditoría programada debe pertenecer a un programa anual.']})
        nuevo = data.get('programa')
        cambia = bool(nuevo) and bool(self.instance) and nuevo != self.instance.programa
        if nuevo and (not self.instance or cambia) and nuevo.bloqueado:
            raise serializers.ValidationError({'programa': [f'El programa {nuevo.anio} está aprobado (solo lectura); ábralo para modificación antes de agregarle auditorías.']})
        # El código lleva el año del programa; una vez en ejecución ya figura en
        # actas y listas, así que la auditoría no cambia de programa.
        if cambia and self.instance.estado not in ('programada', 'planificada'):
            raise serializers.ValidationError({'programa': [f'La auditoría {self.instance.codigo} ya está en ejecución o cerrada; no se puede cambiar de programa.']})
        # El sistema integrado ya contiene ISO 9001, 14001 y 45001: marcar
        # también una de ellas duplicaría preguntas en dos listas.
        normas = data.get('normas_aplicables') or []
        sueltas = [n for n in normas if n in ('iso_9001', 'iso_14001', 'iso_45001')]
        if 'sig_integrado' in normas and sueltas:
            raise serializers.ValidationError({'normas_aplicables': [
                'El Sistema Integrado ya incluye ISO 9001, ISO 14001 e ISO 45001. Marque el Sistema Integrado '
                'para auditar los tres sistemas juntos, o solo las normas que se auditen por separado.']})
        return data

    def get_equipo_anulado(self, obj):
        return _equipo_anulado(obj)

    def get_hallazgos(self, obj):
        return [{
            'id': h.id, 'codigo': h.codigo, 'tipo': h.tipo,
            'tipo_display': h.get_tipo_display(), 'estado': h.get_estado_display(),
            'descripcion': h.descripcion, 'requisito': h.requisito,
            'requiere_ac': h.requiere_ac,
            'tratamiento': h.tratamiento, 'tratamiento_display': h.get_tratamiento_display() if h.tratamiento else '',
            'items': [{'id': it.id, 'norma': it.lista.norma, 'codigo': it.codigo}
                      for it in h.items_lista.select_related('lista').order_by('lista__norma', 'orden')],
        } for h in obj.hallazgos.filter(is_active=True).order_by('id')]

    def get_pendientes_clasificar(self, obj):
        return [{'id': it.id, 'norma': it.lista.norma, 'codigo': it.codigo, 'bloque': it.bloque,
                 'referencia': it.referencia_texto(),
                 'titulo': it.titulo, 'resultado': it.resultado, 'resultado_display': it.get_resultado_display(),
                 'evidencia': it.evidencia} for it in obj.items_pendientes()]

    def get_plan_aprobado_por_nombre(self, obj):
        u = obj.plan_aprobado_por
        return (u.get_full_name() or u.username) if u else None


class ProgramaAuditoriaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    auditorias = AuditoriaListaSerializer(many=True, read_only=True)
    aprobado_por_nombre = serializers.SerializerMethodField()
    modificado_por_nombre = serializers.SerializerMethodField()
    bloqueado = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProgramaAuditoria
        fields = ['id', 'anio', 'estado', 'estado_display', 'bloqueado', 'revision',
                  'aprobado_por_nombre', 'fecha_aprobacion',
                  'modificado_por_nombre', 'fecha_modificacion', 'motivo_modificacion',
                  'observaciones', 'auditorias', 'is_active', 'created_at']
        read_only_fields = ['estado', 'revision', 'fecha_aprobacion', 'fecha_modificacion', 'motivo_modificacion']

    @staticmethod
    def _nombre(u):
        return (u.get_full_name() or u.username) if u else None

    def get_aprobado_por_nombre(self, obj):
        return self._nombre(obj.aprobado_por)

    def get_modificado_por_nombre(self, obj):
        return self._nombre(obj.modificado_por)


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
    registros_anulados = serializers.SerializerMethodField()
    actividades_anuladas = serializers.SerializerMethodField()

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
                  'registros', 'registros_anulados', 'actividades_anuladas', 'actualizado_por', 'is_active',
                  'created_at', 'updated_at']
        # 'codigo' ahora lo asigna el usuario al registrar el equipo.
        read_only_fields = ['estado', 'is_active']
        extra_kwargs = {'imagen': {'write_only': True, 'required': False}}

    def get_registros_anulados(self, obj):
        return _anulados(RegistroEquipo, RegistroEquipoSerializer, equipo=obj)

    def get_actividades_anuladas(self, obj):
        return _anulados(ActividadPrograma, ActividadProgramaSerializer, equipo=obj)

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


# ============================================================
# M12 — Competencia técnica y autorización del personal
# ============================================================

def _nombre_usuario(u):
    return (u.get_full_name() or u.username) if u else None


class MetodoCalibracionSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import MetodoCalibracion
        model = MetodoCalibracion
        fields = ['id', 'nombre', 'codigo', 'magnitud', 'orden', 'is_active']


class ControlValidezSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import ControlValidez
        model = ControlValidez
        fields = ['id', 'nombre', 'orden', 'is_active']


class AutorizacionSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    metodo_nombre = serializers.CharField(source='metodo.nombre', read_only=True, default='')
    autorizado_por_nombre = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    funciones_display = serializers.SerializerMethodField()
    fecha_proximo_seguimiento = serializers.DateField(read_only=True)
    estado_seguimiento = serializers.CharField(read_only=True)
    evidencia_url = serializers.SerializerMethodField()

    class Meta:
        from .models import Autorizacion
        model = Autorizacion
        fields = ['id', 'usuario', 'usuario_nombre', 'metodo', 'metodo_nombre', 'magnitud',
                  'funciones', 'funciones_display', 'alcance_firma', 'laboratorio',
                  'fecha_autorizacion', 'autorizado_por', 'autorizado_por_nombre',
                  'estado', 'estado_display', 'frecuencia_seguimiento_meses',
                  'fecha_ultimo_seguimiento', 'fecha_proximo_seguimiento', 'estado_seguimiento',
                  'evidencia_url', 'observaciones', 'exento_entrenamiento', 'sustento_exencion',
                  'suspendida_en', 'is_active']
        read_only_fields = ['suspendida_en']

    def get_usuario_nombre(self, obj):
        return _nombre_usuario(obj.usuario)

    def get_autorizado_por_nombre(self, obj):
        return _nombre_usuario(obj.autorizado_por)

    def get_funciones_display(self, obj):
        from .models import FUNCIONES_AUTORIZACION
        m = dict(FUNCIONES_AUTORIZACION)
        return [m.get(f, f) for f in (obj.funciones or [])]

    def validate(self, data):
        """Reglas de la autorización (valores finales: los enviados sobre los guardados)."""
        inst = self.instance

        def val(c, defecto=None):
            return data[c] if c in data else (getattr(inst, c) if inst else defecto)
        errores = {}
        usuario, metodo, estado = val('usuario'), val('metodo'), val('estado', 'en_entrenamiento')
        funciones = val('funciones', []) or []
        if not metodo:
            errores['metodo'] = ['La autorización es por método: indique el método.']
        if not funciones:
            errores['funciones'] = ['Indique al menos una función autorizada.']
        if 'firmar' in funciones:
            alcance = val('alcance_firma', '')
            if not alcance:
                errores['alcance_firma'] = ['Quien firma certificados debe tener alcance de firma (todos o un laboratorio).']
            elif alcance == 'laboratorio' and not (val('laboratorio', '') or '').strip():
                errores['laboratorio'] = ['Indique el laboratorio en el que puede firmar.']
        if estado == 'vigente' and not val('fecha_autorizacion'):
            errores['fecha_autorizacion'] = ['Una autorización vigente necesita su fecha de autorización.']
        from .models import es_gerente_tecnico, motivo_sin_entrenamiento
        exento = bool(val('exento_entrenamiento', False))
        if exento:
            if usuario and not es_gerente_tecnico(usuario):
                errores['exento_entrenamiento'] = ['Solo el Gerente Técnico puede ser eximido del entrenamiento '
                                                   '(según el cargo registrado en Usuarios).']
            if not (val('sustento_exencion', '') or '').strip():
                errores['sustento_exencion'] = ['Sustente la exención: formación, experiencia, conocimientos técnicos y '
                                                'desempeño previo (p. ej. ensayos de aptitud).']
        anterior = inst.estado if inst else None
        if estado == 'vigente' and usuario and metodo:
            cambia = (inst is None or anterior != 'vigente' or inst.metodo_id != metodo.pk
                      or inst.usuario_id != usuario.pk)
            if anterior == 'revocada':
                errores['estado'] = ['Una autorización revocada no se reactiva: registre una autorización nueva.']
            elif cambia and 'estado' not in errores:
                # Una suspensión (o revocación) de esta persona en este método exige re-entrenamiento posterior,
                # aunque se pase antes por «en entrenamiento» o se registre una autorización nueva.
                from .models import Autorizacion
                previa = inst if inst is not None and (anterior == 'suspendida' or inst.suspendida_en) else None
                if previa is None:
                    previa = (Autorizacion.objects.filter(usuario=usuario, metodo=metodo, is_active=True,
                                                          estado__in=('suspendida', 'revocada'))
                              .exclude(pk=getattr(inst, 'pk', None)).order_by('-suspendida_en', '-updated_at').first())
                motivo = motivo_sin_entrenamiento(usuario, metodo, previa, exento)
                if motivo:
                    errores['estado'] = [motivo]
        if usuario and metodo and estado in ('vigente', 'en_entrenamiento'):
            from .models import Autorizacion
            otra = (Autorizacion.objects.filter(usuario=usuario, metodo=metodo, is_active=True,
                                                estado__in=('vigente', 'en_entrenamiento'))
                    .exclude(pk=getattr(inst, 'pk', None)).first())
            if otra:
                errores['metodo'] = [f'Esta persona ya tiene una autorización {otra.get_estado_display().lower()} '
                                     f'para este método: edítela en lugar de crear otra.']
        if errores:
            raise serializers.ValidationError(errores)
        return data

    def get_evidencia_url(self, obj):
        return obj.evidencia.url if obj.evidencia else None


class ProcesoEntrenamientoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    metodo_nombre = serializers.CharField(source='metodo.nombre', read_only=True, default='')
    tutor_nombre = serializers.SerializerMethodField()
    tutor_supervision_nombre = serializers.SerializerMethodField()
    control_validez_nombre = serializers.CharField(source='control_validez.nombre', read_only=True, default='')
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    evidencia_url = serializers.SerializerMethodField()

    class Meta:
        from .models import ProcesoEntrenamiento
        model = ProcesoEntrenamiento
        fields = ['id', 'usuario', 'usuario_nombre', 'metodo', 'metodo_nombre', 'tipo', 'tipo_display',
                  'tutor', 'tutor_nombre', 'tutor_supervision', 'tutor_supervision_nombre',
                  'checklist_entrenamiento', 'periodo_supervision_dias',
                  'fecha_inicio_supervision', 'checklist_supervision', 'nota_teorica',
                  'control_validez', 'control_validez_nombre', 'resultado_control',
                  'estado', 'estado_display', 'comentarios', 'evidencia_url', 'is_active']

    def get_usuario_nombre(self, obj):
        return _nombre_usuario(obj.usuario)

    def get_tutor_nombre(self, obj):
        return _nombre_usuario(obj.tutor)

    def get_tutor_supervision_nombre(self, obj):
        return _nombre_usuario(obj.tutor_supervision)

    def validate(self, data):
        """Un entrenamiento es para un método, con tutor y al menos una actividad."""
        inst = self.instance

        def val(c, defecto=None):
            return data[c] if c in data else (getattr(inst, c) if inst else defecto)
        if inst is not None and inst.concluido:
            raise serializers.ValidationError({'detail': (
                f'Este entrenamiento ya concluyó como {"superado" if inst.estado == "completado" else "no conforme"} '
                'y es de solo lectura. '
                'Para un nuevo intento registre un re-entrenamiento.')})
        errores = {}
        if val('estado', 'en_proceso') == 'completado':
            from .models import faltantes_entrenamiento
            falta = faltantes_entrenamiento(val('checklist_entrenamiento', []), val('checklist_supervision', []),
                                            val('nota_teorica'), val('control_validez'), val('resultado_control', ''),
                                            val('tutor_supervision'))
            if falta:
                errores['estado'] = ['Para darlo por superado falta: ' + '; '.join(falta) + '.']
        if not val('metodo'):
            errores['metodo'] = ['Indique el método en que se entrena.']
        if not val('tutor'):
            errores['tutor'] = ['Indique el tutor del entrenamiento.']
        actividades = [a for a in (val('checklist_entrenamiento', []) or [])
                       if isinstance(a, dict) and str(a.get('actividad') or '').strip()]
        if not actividades:
            errores['checklist_entrenamiento'] = ['Registre al menos una actividad de entrenamiento.']
        if errores:
            raise serializers.ValidationError(errores)
        return data

    def get_evidencia_url(self, obj):
        return obj.evidencia.url if obj.evidencia else None


class EvaluacionSeguimientoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField()
    evaluador_nombre = serializers.SerializerMethodField()
    control_validez_nombre = serializers.CharField(source='control_validez.nombre', read_only=True, default='')
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    resultado_display = serializers.CharField(source='get_resultado_display', read_only=True)
    decision_display = serializers.CharField(source='get_decision_display', read_only=True)
    evidencia_url = serializers.SerializerMethodField()

    class Meta:
        from .models import EvaluacionSeguimiento
        model = EvaluacionSeguimiento
        fields = ['id', 'autorizacion', 'usuario', 'usuario_nombre', 'fecha', 'hora', 'area', 'tipo', 'tipo_display',
                  'control_validez', 'control_validez_nombre', 'tema', 'evaluador', 'evaluador_nombre',
                  'preguntas', 'puntaje_obtenido', 'puntaje_total', 'puntaje_minimo', 'puntaje_maximo',
                  'puntaje_por_pregunta', 'n_preguntas', 'resultado', 'resultado_display',
                  'decision', 'decision_display', 'conclusiones', 'observaciones', 'evidencia_url', 'is_active']

    def get_usuario_nombre(self, obj):
        return _nombre_usuario(obj.usuario)

    def get_evaluador_nombre(self, obj):
        return _nombre_usuario(obj.evaluador)

    def validate(self, data):
        """
        Los totales y el resultado de la entrevista se calculan aquí (fórmulas del
        formato), no en la pantalla; la decisión debe ser coherente con el resultado.
        """
        from .models import calcular_puntajes, motivo_sin_entrenamiento
        inst = self.instance

        def val(c, defecto=None):
            return data[c] if c in data else (getattr(inst, c) if inst else defecto)
        errores = {}
        preguntas = val('preguntas', []) or []
        for i, p in enumerate([p for p in preguntas if isinstance(p, dict)], start=1):
            try:
                est, obt = float(p.get('establecido') or 0), float(p.get('obtenido') or 0)
            except (TypeError, ValueError):
                errores['preguntas'] = [f'Pregunta {i}: los puntajes deben ser números.']
                break
            if obt < 0 or est < 0:
                errores['preguntas'] = [f'Pregunta {i}: los puntajes no pueden ser negativos.']
                break
            if obt > est:
                errores['preguntas'] = [f'Pregunta {i}: el puntaje obtenido ({obt:g}) supera al establecido ({est:g}).']
                break
        calc = calcular_puntajes(preguntas, val('puntaje_por_pregunta'))
        if calc['preguntas']:
            for k in ('preguntas', 'n_preguntas', 'puntaje_total', 'puntaje_maximo', 'puntaje_minimo',
                      'puntaje_por_pregunta'):
                data[k] = calc[k]
            if calc['resultado']:
                data['resultado'] = calc['resultado']
        else:
            for k in ('n_preguntas', 'puntaje_total', 'puntaje_maximo', 'puntaje_minimo'):
                data[k] = None
        resultado, decision = val('resultado', ''), val('decision', '')
        autorizacion = val('autorizacion')
        if decision and not resultado:
            errores['resultado'] = ['Registre el resultado antes de decidir.']
        elif resultado == 'no_satisfactorio' and decision in ('mantener', 'reautorizar'):
            errores['decision'] = ['Con resultado no satisfactorio no se mantiene ni se reautoriza: '
                                   'corresponde suspender la autorización y re-entrenar.']
        if decision in ('suspender', 'reautorizar') and not autorizacion:
            errores['autorizacion'] = ['Indique la autorización que se suspende o reautoriza.']
        if decision == 'reautorizar' and autorizacion and 'decision' not in errores:
            if autorizacion.estado != 'suspendida':
                errores['decision'] = ['Solo se reautoriza una autorización suspendida.']
            else:
                motivo = motivo_sin_entrenamiento(autorizacion.usuario, autorizacion.metodo, autorizacion)
                if motivo:
                    errores['decision'] = [motivo]
        if errores:
            raise serializers.ValidationError(errores)
        return data

    def get_evidencia_url(self, obj):
        return obj.evidencia.url if obj.evidencia else None
