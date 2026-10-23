from rest_framework import serializers

from .models import (Actividad, Aviso, DocumentoFicha, Ficha, Indicador, Proceso, RegistroFicha,
                     ResultadoIndicador)


def _nombre(u):
    return (u.get_full_name() or u.username) if u else None


class ProcesoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    padre_nombre = serializers.CharField(source='padre.nombre', read_only=True, default=None)
    responsable_nombre = serializers.SerializerMethodField()
    ficha_vigente = serializers.SerializerMethodField()
    ficha_en_curso = serializers.SerializerMethodField()
    avisos_pendientes = serializers.SerializerMethodField()

    class Meta:
        model = Proceso
        fields = ['id', 'nombre', 'tipo', 'tipo_display', 'padre', 'padre_nombre', 'responsable_cargo',
                  'responsable', 'responsable_nombre', 'detalle_mapa', 'orden', 'is_active', 'ficha_vigente',
                  'ficha_en_curso', 'avisos_pendientes']
        read_only_fields = ['is_active']

    def get_responsable_nombre(self, obj):
        return _nombre(obj.responsable)

    def get_ficha_vigente(self, obj):
        f = obj.ficha_vigente
        return {'id': f.id, 'version': f.version, 'fecha_aprobacion': f.fecha_aprobacion} if f else None

    def get_ficha_en_curso(self, obj):
        f = obj.ficha_en_curso
        return {'id': f.id, 'version': f.version, 'estado': f.estado,
                'estado_display': f.get_estado_display()} if f else None

    def get_avisos_pendientes(self, obj):
        return obj.avisos.filter(atendido=False).count()

    def validate(self, data):
        padre = data.get('padre', getattr(self.instance, 'padre', None))
        if padre:
            if self.instance and padre.pk == self.instance.pk:
                raise serializers.ValidationError({'padre': ['Un proceso no puede ser su propio padre.']})
            if padre.padre_id:
                raise serializers.ValidationError({'padre': ['Solo hay un nivel de subprocesos.']})
            if not padre.is_active:
                raise serializers.ValidationError({'padre': ['El proceso padre está desactivado.']})
        return data


class ActividadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    proveedores_nombres = serializers.SerializerMethodField()
    clientes_nombres = serializers.SerializerMethodField()

    class Meta:
        model = Actividad
        fields = ['id', 'orden', 'seccion', 'proveedores', 'proveedores_nombres', 'proveedor_otro', 'entrada',
                  'actividad', 'control', 'clientes', 'clientes_nombres', 'cliente_otro', 'salida']

    def get_proveedores_nombres(self, obj):
        return [p.nombre for p in obj.proveedores.all()]

    def get_clientes_nombres(self, obj):
        return [p.nombre for p in obj.clientes.all()]


class DocumentoFichaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    documento_codigo = serializers.CharField(source='documento.codigo', read_only=True, default=None)
    documento_titulo = serializers.CharField(source='documento.titulo', read_only=True, default=None)
    texto = serializers.CharField(read_only=True)

    class Meta:
        model = DocumentoFicha
        fields = ['id', 'orden', 'documento', 'documento_codigo', 'documento_titulo', 'descripcion', 'texto']


class RegistroFichaSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = RegistroFicha
        fields = ['id', 'orden', 'descripcion']


class IndicadorSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    frecuencia_display = serializers.CharField(source='get_frecuencia_display', read_only=True)
    ultimo_resultado = serializers.SerializerMethodField()

    class Meta:
        model = Indicador
        fields = ['id', 'orden', 'nombre', 'calculo', 'meta', 'frecuencia', 'frecuencia_display', 'responsable',
                  'ultimo_resultado']

    def get_ultimo_resultado(self, obj):
        r = ResultadoIndicador.objects.filter(proceso_id=obj.ficha.proceso_id, indicador=obj.nombre,
                                              is_active=True).first()
        return ResultadoSerializer(r).data if r else None


class FichaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True)
    proceso_tipo = serializers.CharField(source='proceso.tipo', read_only=True)
    proceso_tipo_display = serializers.CharField(source='proceso.get_tipo_display', read_only=True)
    elaborado_por_nombre = serializers.SerializerMethodField()
    revisado_por_nombre = serializers.SerializerMethodField()
    aprobado_por_nombre = serializers.SerializerMethodField()
    etapas_abiertas = serializers.SerializerMethodField()
    actividades = ActividadSerializer(many=True, required=False)
    documentos = DocumentoFichaSerializer(many=True, required=False)
    registros = RegistroFichaSerializer(many=True, required=False)
    indicadores = IndicadorSerializer(many=True, required=False)

    class Meta:
        model = Ficha
        fields = ['id', 'proceso', 'proceso_nombre', 'proceso_tipo', 'proceso_tipo_display', 'version', 'estado',
                  'estado_display', 'motivo_cambio', 'objetivo', 'responsable', 'alcance', 'recurso_humano',
                  'recurso_economico', 'recurso_tecnologico', 'elaborado_por', 'elaborado_por_nombre',
                  'fecha_elaboracion', 'revisado_por', 'revisado_por_nombre', 'fecha_revision', 'aprobado_por',
                  'aprobado_por_nombre', 'fecha_aprobacion', 'firmas', 'hash_contenido', 'devoluciones',
                  'etapas_abiertas', 'actividades', 'documentos', 'registros', 'indicadores', 'created_at']
        read_only_fields = ['version', 'estado', 'elaborado_por', 'fecha_elaboracion', 'revisado_por',
                            'fecha_revision', 'aprobado_por', 'fecha_aprobacion', 'firmas', 'hash_contenido',
                            'devoluciones']

    def get_elaborado_por_nombre(self, obj):
        return _nombre(obj.elaborado_por)

    def get_revisado_por_nombre(self, obj):
        return _nombre(obj.revisado_por)

    def get_aprobado_por_nombre(self, obj):
        return _nombre(obj.aprobado_por)

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas()

    def validate_actividades(self, filas):
        for i, f in enumerate(filas, 1):
            if not (f.get('actividad') or '').strip():
                raise serializers.ValidationError(f'La actividad {i} no tiene descripción.')
        return filas

    def validate_documentos(self, filas):
        for i, f in enumerate(filas, 1):
            if not f.get('documento') and not (f.get('descripcion') or '').strip():
                raise serializers.ValidationError(f'El documento {i} no está vinculado ni descrito.')
        return filas

    def validate_registros(self, filas):
        for i, f in enumerate(filas, 1):
            if not (f.get('descripcion') or '').strip():
                raise serializers.ValidationError(f'El registro {i} está vacío.')
        return filas

    def validate_indicadores(self, filas):
        for i, f in enumerate(filas, 1):
            if not (f.get('nombre') or '').strip():
                raise serializers.ValidationError(f'El indicador {i} no tiene nombre.')
        return filas

    def _guardar_filas(self, ficha, modelo, filas, m2m=()):
        """Reemplaza la lista: actualiza las que vienen con id, crea las nuevas y da de baja las que faltan."""
        usuario = self.context['request'].user
        actuales = {x.pk: x for x in modelo.objects.filter(ficha=ficha)}
        vistos = set()
        for i, datos in enumerate(filas):
            datos = dict(datos)
            relaciones = {c: datos.pop(c, None) for c in m2m}
            pk = datos.pop('id', None)
            datos['orden'] = i + 1
            obj = actuales.get(pk)
            if obj:
                for k, v in datos.items():
                    setattr(obj, k, v)
                obj.updated_by = usuario
                obj.save()
                vistos.add(pk)
            else:
                obj = modelo.objects.create(ficha=ficha, created_by=usuario, updated_by=usuario, **datos)
            for c, valor in relaciones.items():
                if valor is not None:
                    getattr(obj, c).set(valor)
        for pk, obj in actuales.items():
            if pk not in vistos:
                obj.is_active = False
                obj.updated_by = usuario
                obj.save(update_fields=['is_active', 'updated_by', 'updated_at'])

    def _listas(self, ficha, listas):
        if 'actividades' in listas:
            self._guardar_filas(ficha, Actividad, listas['actividades'], m2m=('proveedores', 'clientes'))
        if 'documentos' in listas:
            self._guardar_filas(ficha, DocumentoFicha, listas['documentos'])
        if 'registros' in listas:
            self._guardar_filas(ficha, RegistroFicha, listas['registros'])
        if 'indicadores' in listas:
            self._guardar_filas(ficha, Indicador, listas['indicadores'])

    def create(self, validated_data):
        listas = {k: validated_data.pop(k) for k in ('actividades', 'documentos', 'registros', 'indicadores')
                  if k in validated_data}
        ficha = super().create(validated_data)
        self._listas(ficha, listas)
        return ficha

    def update(self, instance, validated_data):
        listas = {k: validated_data.pop(k) for k in ('actividades', 'documentos', 'registros', 'indicadores')
                  if k in validated_data}
        ficha = super().update(instance, validated_data)
        self._listas(ficha, listas)
        return ficha


class FichaListaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True)

    class Meta:
        model = Ficha
        fields = ['id', 'proceso', 'proceso_nombre', 'version', 'estado', 'estado_display', 'motivo_cambio',
                  'fecha_elaboracion', 'fecha_revision', 'fecha_aprobacion', 'created_at']


class ResultadoSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    registrado_por = serializers.SerializerMethodField()

    class Meta:
        model = ResultadoIndicador
        fields = ['id', 'proceso', 'indicador', 'periodo', 'valor', 'estado', 'estado_display', 'comentario',
                  'registrado_por']

    def get_registrado_por(self, obj):
        return _nombre(obj.created_by)

    def validate_periodo(self, v):
        return v.replace(day=1)

    def validate(self, data):
        proceso = data.get('proceso', getattr(self.instance, 'proceso', None))
        indicador = data.get('indicador', getattr(self.instance, 'indicador', None))
        periodo = data.get('periodo', getattr(self.instance, 'periodo', None))
        if proceso and indicador and periodo:
            qs = ResultadoIndicador.objects.filter(proceso=proceso, indicador=indicador, periodo=periodo,
                                                   is_active=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('Ese indicador ya tiene resultado en ese periodo: edítelo.')
        return data


class AvisoSerializer(serializers.ModelSerializer):
    origen_display = serializers.CharField(source='get_origen_display', read_only=True)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True)
    registrado_por = serializers.SerializerMethodField()
    version_atencion = serializers.CharField(source='ficha_atencion.version', read_only=True, default=None)

    class Meta:
        model = Aviso
        fields = ['id', 'proceso', 'proceso_nombre', 'origen', 'origen_display', 'motivo', 'atendido',
                  'version_atencion', 'descartado_motivo', 'fecha_atencion', 'registrado_por', 'created_at']
        read_only_fields = ['origen', 'atendido', 'descartado_motivo', 'fecha_atencion']

    def get_registrado_por(self, obj):
        return _nombre(obj.created_by)
