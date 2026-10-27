from rest_framework import serializers

from .models import CAMPOS_PERFIL, Area, Nivel, Puesto, Sede, Suministro, Trabajador


def _proceso_principal(valor):
    if valor is not None and valor.padre_id:
        raise serializers.ValidationError(f'Elija el proceso principal ({valor.padre.nombre}), no el subproceso.')
    return valor


def _nombre_unico(modelo, valor, instancia, texto, **filtro):
    valor = ' '.join((valor or '').split())
    if not valor:
        raise serializers.ValidationError('Este dato es obligatorio.')
    otros = modelo.objects.filter(**filtro).exclude(pk=getattr(instancia, 'pk', None)).values_list('nombre', flat=True)
    if any(n.casefold() == valor.casefold() for n in otros):
        raise serializers.ValidationError(texto)
    return valor


class NivelSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    n_areas = serializers.SerializerMethodField()

    class Meta:
        model = Nivel
        fields = ['id', 'sede', 'sede_nombre', 'nombre', 'orden', 'is_active', 'n_areas']
        read_only_fields = ['is_active']

    def get_n_areas(self, obj):
        return obj.areas.filter(is_active=True).count()

    def validate(self, data):
        sede = data.get('sede', getattr(self.instance, 'sede', None))
        if self.instance and 'sede' in data and data['sede'] != self.instance.sede:
            raise serializers.ValidationError({'sede': ['Un nivel no cambia de sede: desactívelo y créelo en la otra.']})
        if 'nombre' in data or not self.instance:
            data['nombre'] = _nombre_unico(Nivel, data.get('nombre'), self.instance,
                                           'La sede ya tiene un nivel con ese nombre.', sede=sede)
        return data


class SuministroSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    nivel_nombre = serializers.CharField(source='nivel.nombre', read_only=True, default=None)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    modalidad_display = serializers.CharField(source='get_modalidad_display', read_only=True)
    responsable_nombre = serializers.CharField(source='responsable.nombre', read_only=True, default=None)
    unidad = serializers.CharField(read_only=True)
    nombre = serializers.CharField(read_only=True)

    class Meta:
        model = Suministro
        fields = ['id', 'sede', 'sede_nombre', 'nivel', 'nivel_nombre', 'tipo', 'tipo_display', 'modalidad',
                  'modalidad_display', 'numero', 'empresa_prestadora', 'ubicacion', 'responsable',
                  'responsable_nombre', 'unidad', 'nombre', 'is_active', 'historial']
        read_only_fields = ['is_active', 'historial']

    def validate(self, data):
        inst = self.instance
        sede = data.get('sede', getattr(inst, 'sede', None))
        nivel = data.get('nivel', getattr(inst, 'nivel', None))
        if inst and 'sede' in data and data['sede'] != inst.sede:
            raise serializers.ValidationError({'sede': ['Un suministro no cambia de sede: desactívelo y regístrelo en '
                                                         'la otra.']})
        if inst and 'tipo' in data and data['tipo'] != inst.tipo and inst.consumos.filter(is_active=True).exists():
            raise serializers.ValidationError({'tipo': ['El suministro ya tiene consumos registrados: no cambia de '
                                                         'servicio.']})
        if nivel and nivel.sede_id != getattr(sede, 'pk', None):
            raise serializers.ValidationError({'nivel': ['El nivel no pertenece a esa sede.']})
        if sede and not sede.is_active:
            raise serializers.ValidationError({'sede': ['La sede está desactivada.']})
        return data


class SedeSerializer(serializers.ModelSerializer):
    tenencia_display = serializers.CharField(source='get_tenencia_display', read_only=True)
    responsable_nombre = serializers.CharField(source='responsable.nombre', read_only=True, default=None)
    niveles = serializers.SerializerMethodField()
    suministros = serializers.SerializerMethodField()
    n_areas = serializers.SerializerMethodField()

    class Meta:
        model = Sede
        fields = ['id', 'nombre', 'codigo', 'direccion', 'ubigeo', 'distrito', 'provincia', 'departamento', 'tenencia',
                  'tenencia_display', 'principal', 'responsable', 'responsable_nombre', 'descripcion', 'orden',
                  'is_active', 'historial', 'niveles', 'suministros', 'n_areas']
        read_only_fields = ['is_active', 'historial', 'distrito', 'provincia', 'departamento']

    def validate(self, data):
        # Distrito, provincia y departamento salen del ubigeo elegido (catálogo INEI), nunca escritos a mano.
        if 'ubigeo' in data:
            u = data['ubigeo']
            data['distrito'], data['provincia'], data['departamento'] = (
                (u.distrito, u.provincia, u.departamento) if u else ('', '', ''))
        return data

    def get_niveles(self, obj):
        return NivelSerializer(obj.niveles.all(), many=True).data

    def get_suministros(self, obj):
        return SuministroSerializer(obj.suministros.select_related('sede', 'nivel', 'responsable'), many=True).data

    def get_n_areas(self, obj):
        return obj.areas.filter(is_active=True).count()

    def validate_nombre(self, valor):
        return _nombre_unico(Sede, valor, self.instance, 'Ya existe una sede con ese nombre.')

    def validate_codigo(self, valor):
        return (valor or '').strip().upper()


class AreaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    padre_nombre = serializers.CharField(source='padre.nombre', read_only=True, default=None)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    responsable_nombre = serializers.CharField(source='responsable.nombre', read_only=True, default=None)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default=None)
    nivel_nombre = serializers.CharField(source='nivel.nombre', read_only=True, default=None)
    n_puestos = serializers.SerializerMethodField()
    n_trabajadores = serializers.SerializerMethodField()

    class Meta:
        model = Area
        fields = ['id', 'nombre', 'tipo', 'tipo_display', 'padre', 'padre_nombre', 'proceso', 'proceso_nombre', 'sede',
                  'sede_nombre', 'nivel', 'nivel_nombre', 'responsable', 'responsable_nombre', 'descripcion', 'orden',
                  'is_active', 'n_puestos', 'n_trabajadores', 'historial']
        read_only_fields = ['is_active', 'historial']

    def get_n_puestos(self, obj):
        return obj.puestos.filter(is_active=True).count()

    def get_n_trabajadores(self, obj):
        return Trabajador.objects.filter(is_active=True, estado='activo').filter(
            area=obj).count() + Trabajador.objects.filter(is_active=True, estado='activo', area__isnull=True,
                                                          puesto__area=obj).count()

    def validate_proceso(self, valor):
        return _proceso_principal(valor)

    def validate_nombre(self, valor):
        valor = valor.strip()
        otros = Area.objects.exclude(pk=getattr(self.instance, 'pk', None)).values_list('nombre', flat=True)
        if any(n.casefold() == valor.casefold() for n in otros):
            raise serializers.ValidationError('Ya existe un área con ese nombre.')
        return valor

    def validate(self, data):
        padre = data.get('padre')
        if self.instance and padre and (padre.pk == self.instance.pk or padre.pk in self.instance.descendientes()):
            raise serializers.ValidationError({'padre': ['Un área no puede depender de sí misma ni de una de sus '
                                                         'subáreas.']})
        sede = data['sede'] if 'sede' in data else getattr(self.instance, 'sede', None)
        nivel = data['nivel'] if 'nivel' in data else getattr(self.instance, 'nivel', None)
        if nivel and not sede:
            data['sede'] = sede = nivel.sede
        if nivel and nivel.sede_id != sede.pk:
            if 'sede' in data and 'nivel' not in data:
                data['nivel'] = None  # cambió de sede: el nivel de la sede anterior ya no aplica
            else:
                raise serializers.ValidationError({'nivel': ['El nivel no pertenece a la sede elegida.']})
        for campo, obj in (('sede', data.get('sede')), ('nivel', data.get('nivel'))):
            if obj is not None and not obj.is_active and obj != getattr(self.instance, campo, None):
                raise serializers.ValidationError({campo: ['Está desactivado.']})
        return data


class PuestoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True, default=None)
    reporta_a_nombre = serializers.CharField(source='reporta_a.nombre', read_only=True, default=None)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    tiene_perfil = serializers.BooleanField(read_only=True)
    n_trabajadores = serializers.SerializerMethodField()

    class Meta:
        model = Puesto
        fields = ['id', 'nombre', 'sigla', 'area', 'area_nombre', 'reporta_a', 'reporta_a_nombre', 'tipo',
                  'tipo_display', 'proceso', 'proceso_nombre', *CAMPOS_PERFIL, 'version_perfil', 'tiene_perfil',
                  'is_active', 'n_trabajadores', 'historial']
        read_only_fields = ['version_perfil', 'is_active', 'historial']

    def get_n_trabajadores(self, obj):
        return obj.trabajadores.filter(is_active=True, estado='activo').count()

    def validate_proceso(self, valor):
        return _proceso_principal(valor)

    def validate_sigla(self, valor):
        return (valor or '').strip().upper()

    def validate_nombre(self, valor):
        valor = valor.strip()
        otros = Puesto.objects.exclude(pk=getattr(self.instance, 'pk', None)).values_list('nombre', flat=True)
        if any(n.casefold() == valor.casefold() for n in otros):
            raise serializers.ValidationError('Ya existe un puesto con ese nombre.')
        return valor

    def validate(self, data):
        jefe = data.get('reporta_a')
        if self.instance and jefe:
            actual, vistos = jefe, set()
            while actual and actual.pk not in vistos:
                if actual.pk == self.instance.pk:
                    raise serializers.ValidationError({'reporta_a': ['La línea de reporte no puede volver a este '
                                                                     'puesto.']})
                vistos.add(actual.pk)
                actual = actual.reporta_a
        return data


class TrabajadorSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    puesto_nombre = serializers.CharField(source='puesto.nombre', read_only=True)
    puesto_sigla = serializers.CharField(source='puesto.sigla', read_only=True)
    puesto_tipo = serializers.CharField(source='puesto.tipo', read_only=True)
    area_nombre = serializers.SerializerMethodField()
    area_efectiva = serializers.SerializerMethodField()
    usuario_username = serializers.CharField(source='usuario.username', read_only=True, default=None)

    class Meta:
        model = Trabajador
        fields = ['id', 'nombres', 'apellidos', 'nombre_completo', 'documento', 'puesto', 'puesto_nombre',
                  'puesto_sigla', 'puesto_tipo', 'area', 'area_nombre', 'area_efectiva', 'empresa', 'correo',
                  'telefono', 'fecha_ingreso', 'fecha_cese', 'motivo_cese', 'estado', 'usuario', 'usuario_username',
                  'historial', 'is_active']
        read_only_fields = ['fecha_cese', 'motivo_cese', 'estado', 'historial', 'is_active']

    def get_area_nombre(self, obj):
        a = obj.area_efectiva
        return a.nombre if a else None

    def get_area_efectiva(self, obj):
        a = obj.area_efectiva
        return a.pk if a else None

    def validate_puesto(self, valor):
        if not valor.is_active:
            raise serializers.ValidationError('El puesto está desactivado.')
        return valor

    def validate_usuario(self, valor):
        actual = getattr(self.instance, 'usuario', None)
        if valor != actual:
            # Vincular o desvincular un usuario del sistema es gestión de usuarios: exige ese permiso, y la cuenta del
            # propietario solo la toca él.
            request = self.context.get('request')
            u = getattr(request, 'user', None)
            if not (u and u.tiene_permiso('usuarios', 'editar')):
                raise serializers.ValidationError('Vincular un usuario del sistema requiere el permiso de editar '
                                                  'usuarios.')
            if any(x is not None and x.is_superuser for x in (valor, actual)) and not u.is_superuser:
                raise serializers.ValidationError('La cuenta del propietario del sistema solo la vincula él.')
        if valor is None:
            return valor
        otro = Trabajador.objects.filter(usuario=valor).exclude(pk=getattr(self.instance, 'pk', None)).first()
        if otro:
            raise serializers.ValidationError(f'El usuario ya está vinculado a {otro.nombre_completo}.')
        return valor

    def to_representation(self, obj):
        datos = super().to_representation(obj)
        # El documento de identidad solo lo ve quien gestiona la organización.
        if not self.context.get('ver_documento'):
            datos.pop('documento', None)
        return datos
