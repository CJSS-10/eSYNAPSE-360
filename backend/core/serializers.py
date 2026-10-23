"""
eSYNAPSE 360 — Serializers de la app core (Fase 0).
"""
from django.utils.crypto import get_random_string
from rest_framework import serializers

from .constants import MODULOS, OPERACIONES
from .models import LogAuditoria, OpcionCatalogo, Permiso, Rol, RolUsuario, Usuario


def _foto_url(obj, context):
    """URL absoluta de la foto de perfil (o None)."""
    foto = getattr(obj, 'foto', None)
    if not foto:
        return None
    request = context.get('request') if context else None
    return request.build_absolute_uri(foto.url) if request else foto.url


class PermisoSerializer(serializers.ModelSerializer):
    modulo_display = serializers.CharField(source='get_modulo_display', read_only=True)
    operacion_display = serializers.CharField(source='get_operacion_display', read_only=True)

    class Meta:
        model = Permiso
        fields = ['id', 'rol', 'modulo', 'modulo_display', 'operacion', 'operacion_display', 'permitido']


class PermisoInlineSerializer(serializers.ModelSerializer):
    """Permiso anidado dentro de un rol (sin el campo rol)."""

    class Meta:
        model = Permiso
        fields = ['modulo', 'operacion', 'permitido']


class RolSerializer(serializers.ModelSerializer):
    permisos = PermisoInlineSerializer(many=True, required=False)
    total_usuarios = serializers.SerializerMethodField()

    class Meta:
        model = Rol
        fields = ['id', 'nombre', 'descripcion', 'es_admin_sistema', 'is_active',
                  'permisos', 'total_usuarios', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_total_usuarios(self, obj):
        return obj.usuarios_asignados.filter(is_active=True).count()

    def validate_es_admin_sistema(self, value):
        # Solo el propietario (superusuario) puede marcar/quitar el rol de
        # 'Administrador del sistema'. Un administrador de empresa no escala.
        request = self.context.get('request')
        es_super = bool(request and getattr(request, 'user', None) and request.user.is_superuser)
        if not es_super:
            return self.instance.es_admin_sistema if self.instance else False
        return value

    def create(self, validated_data):
        permisos = validated_data.pop('permisos', [])
        rol = Rol.objects.create(**validated_data)
        for p in permisos:
            Permiso.objects.create(rol=rol, **p)
        return rol

    def update(self, instance, validated_data):
        permisos = validated_data.pop('permisos', None)
        instance = super().update(instance, validated_data)
        if permisos is not None:
            # Reemplaza la matriz de permisos del rol (queda auditado vía señales)
            instance.permisos.all().delete()
            for p in permisos:
                Permiso.objects.create(rol=instance, **p)
        return instance


class RolUsuarioSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source='rol.nombre', read_only=True)
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = RolUsuario
        fields = ['id', 'usuario', 'usuario_username', 'rol', 'rol_nombre', 'is_active']


def _trabajador_info(obj):
    t = getattr(obj, 'trabajador', None) if obj and obj.pk else None
    if not t:
        return None
    a = t.area_efectiva
    return {'id': t.id, 'nombre': t.nombre_completo, 'puesto': t.puesto.nombre, 'sigla': t.puesto.sigla,
            'area': a.nombre if a else None, 'estado': t.estado}


def _trabajadores_qs():
    from organizacion.models import Trabajador
    return Trabajador.objects.filter(is_active=True)


def _vincular(usuario, trabajador):
    """Vincula (o desvincula, con None) el usuario a su trabajador; el cargo y el área salen del puesto."""
    from organizacion.models import Trabajador, sincronizar_usuario
    Trabajador.objects.filter(usuario=usuario).exclude(pk=getattr(trabajador, 'pk', None)).update(usuario=None)
    if trabajador:
        if trabajador.usuario_id and trabajador.usuario_id != usuario.pk:
            raise serializers.ValidationError({'trabajador': ['Ese trabajador ya tiene otro usuario.']})
        trabajador.usuario = usuario
        trabajador.save(update_fields=['usuario'])
        sincronizar_usuario(trabajador)


class UsuarioSerializer(serializers.ModelSerializer):
    """Lectura y edición de usuarios. La contraseña nunca se expone."""
    roles = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()
    foto = serializers.FileField(write_only=True, required=False, allow_null=True)
    foto_url = serializers.SerializerMethodField()
    trabajador = serializers.PrimaryKeyRelatedField(queryset=_trabajadores_qs(), write_only=True, required=False,
                                                    allow_null=True)
    trabajador_info = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'nombre_completo',
                  'area', 'laboratorio', 'cargo', 'sigla_cargo', 'telefono', 'foto', 'foto_url',
                  'is_active', 'is_superuser', 'roles', 'last_login', 'created_at', 'updated_at', 'trabajador',
                  'trabajador_info']
        read_only_fields = ['is_superuser', 'last_login', 'created_at', 'updated_at']

    def get_trabajador_info(self, obj):
        return _trabajador_info(obj)

    def update(self, instance, validated_data):
        enviado = 'trabajador' in validated_data
        trabajador = validated_data.pop('trabajador', None)
        instance = super().update(instance, validated_data)
        if enviado:
            _vincular(instance, trabajador)
        elif getattr(instance, 'trabajador', None):
            from organizacion.models import sincronizar_usuario
            sincronizar_usuario(instance.trabajador)
        return instance

    def get_roles(self, obj):
        return [
            {'id': ru.rol.id, 'nombre': ru.rol.nombre}
            for ru in obj.roles_asignados.filter(is_active=True, rol__is_active=True).select_related('rol')
        ]

    def get_nombre_completo(self, obj):
        return obj.get_full_name() or obj.username

    def get_foto_url(self, obj):
        return _foto_url(obj, self.context)


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """
    Creación de usuarios (flujo 0.1):
    - Valida email único (error "Email ya registrado")
    - Si no se envía contraseña, genera una temporal y la retorna UNA sola vez
    - Permite asignar roles en el mismo request
    """
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    roles = serializers.PrimaryKeyRelatedField(
        queryset=Rol.objects.filter(is_active=True), many=True, required=False, write_only=True
    )
    password_temporal = serializers.CharField(read_only=True)
    trabajador = serializers.PrimaryKeyRelatedField(queryset=_trabajadores_qs(), write_only=True, required=False,
                                                    allow_null=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'area', 'laboratorio', 'cargo', 'sigla_cargo', 'telefono',
                  'password', 'password_temporal', 'roles', 'trabajador']
        extra_kwargs = {'area': {'required': False, 'allow_blank': True},
                        'cargo': {'required': False, 'allow_blank': True}}

    def validate(self, data):
        t = data.get('trabajador')
        if t and t.usuario_id:
            raise serializers.ValidationError({'trabajador': ['Ese trabajador ya tiene un usuario.']})
        if not t:
            faltan = {c: ['Este campo es requerido si el usuario no se vincula a un trabajador.']
                      for c in ('area', 'cargo') if not (data.get(c) or '').strip()}
            if faltan:
                raise serializers.ValidationError(faltan)
        return data

    def validate_email(self, value):
        if Usuario.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Email ya registrado')
        return value

    def create(self, validated_data):
        roles = validated_data.pop('roles', [])
        trabajador = validated_data.pop('trabajador', None)
        if trabajador:
            a = trabajador.area_efectiva
            validated_data.setdefault('area', a.nombre if a else '')
            validated_data['area'] = validated_data['area'] or (a.nombre if a else '')
            validated_data['cargo'] = trabajador.puesto.nombre
        password = validated_data.pop('password', '') or None
        password_temporal = None
        if password is None:
            password_temporal = get_random_string(12)
            password = password_temporal

        usuario = Usuario.objects.create_user(password=password, **validated_data)
        for rol in roles:
            RolUsuario.objects.create(usuario=usuario, rol=rol)
        if trabajador:
            _vincular(usuario, trabajador)

        # Se expone la contraseña temporal solo en esta respuesta.
        # TODO Fase 0+: enviar correo de bienvenida en lugar de retornarla.
        usuario.password_temporal = password_temporal
        return usuario


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nueva = serializers.CharField(write_only=True, min_length=8)

    def validate_password_actual(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta')
        return value


class LogAuditoriaSerializer(serializers.ModelSerializer):
    accion_display = serializers.CharField(source='get_accion_display', read_only=True)

    class Meta:
        model = LogAuditoria
        fields = ['id', 'timestamp', 'usuario', 'usuario_nombre', 'rol', 'ip', 'dispositivo',
                  'modulo', 'accion', 'accion_display', 'entidad', 'entidad_id', 'campo',
                  'valor_anterior', 'valor_nuevo', 'referencia', 'detalle']


class MeSerializer(serializers.ModelSerializer):
    """
    Datos del usuario autenticado + sus permisos efectivos.
    El frontend lo usa para armar el sidebar y ocultar acciones sin permiso.
    """
    roles = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()
    foto_url = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'nombre_completo',
                  'area', 'laboratorio', 'cargo', 'sigla_cargo', 'telefono', 'foto_url', 'is_superuser', 'roles', 'permisos']

    def get_nombre_completo(self, obj):
        return obj.get_full_name() or obj.username

    def get_foto_url(self, obj):
        return _foto_url(obj, self.context)

    def get_roles(self, obj):
        return [
            ru.rol.nombre
            for ru in obj.roles_asignados.filter(is_active=True, rol__is_active=True).select_related('rol')
        ]

    def get_permisos(self, obj):
        """Diccionario {modulo: [operaciones]} — unión de todos los roles."""
        if obj.is_superuser:
            return {clave: [op[0] for op in OPERACIONES] for clave, _ in MODULOS}
        permisos = {}
        qs = Permiso.objects.filter(
            rol__usuarios_asignados__usuario=obj,
            rol__usuarios_asignados__is_active=True,
            rol__is_active=True,
            permitido=True,
        ).values_list('modulo', 'operacion').distinct()
        for modulo, operacion in qs:
            permisos.setdefault(modulo, []).append(operacion)
        return permisos


class OpcionCatalogoSerializer(serializers.ModelSerializer):
    """Opción de catálogo (Área o Laboratorio), gestionable desde la UI."""

    class Meta:
        model = OpcionCatalogo
        fields = ['id', 'tipo', 'nombre', 'is_active', 'orden']
