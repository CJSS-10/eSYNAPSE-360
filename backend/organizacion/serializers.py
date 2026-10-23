from rest_framework import serializers

from .models import CAMPOS_PERFIL, Area, Puesto, Trabajador


def _proceso_principal(valor):
    if valor is not None and valor.padre_id:
        raise serializers.ValidationError(f'Elija el proceso principal ({valor.padre.nombre}), no el subproceso.')
    return valor


class AreaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    padre_nombre = serializers.CharField(source='padre.nombre', read_only=True, default=None)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    responsable_nombre = serializers.CharField(source='responsable.nombre', read_only=True, default=None)
    n_puestos = serializers.SerializerMethodField()
    n_trabajadores = serializers.SerializerMethodField()

    class Meta:
        model = Area
        fields = ['id', 'nombre', 'tipo', 'tipo_display', 'padre', 'padre_nombre', 'proceso', 'proceso_nombre', 'sede',
                  'piso', 'responsable', 'responsable_nombre', 'descripcion', 'orden', 'is_active', 'n_puestos',
                  'n_trabajadores', 'historial']
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
