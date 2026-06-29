"""
eSYNAPSE 360 — Vistas del API (Fase 0).
CRUD de usuarios y roles con permisos granulares, soft delete obligatorio
y log de auditoría en cada acción (vía middleware + señales).
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from .constants import MODULOS, OPERACIONES
from .models import LogAuditoria, OpcionCatalogo, Permiso, Rol, RolUsuario, Usuario
from .permissions import PermisoModular, SoloAdministradores
from .serializers import (
    CambiarPasswordSerializer,
    LogAuditoriaSerializer,
    MeSerializer,
    OpcionCatalogoSerializer,
    PermisoSerializer,
    RolSerializer,
    RolUsuarioSerializer,
    UsuarioCreateSerializer,
    UsuarioSerializer,
)


def invalidar_sesiones(usuario):
    """
    Invalida todas las sesiones JWT activas del usuario (flujo 0.1:
    'Invalida todas las sesiones activas del usuario inmediatamente').
    """
    for token in OutstandingToken.objects.filter(user=usuario):
        BlacklistedToken.objects.get_or_create(token=token)


class UsuarioViewSet(viewsets.ModelViewSet):
    """
    CRUD de usuarios. Regla: nunca se elimina físicamente — destroy
    desactiva (is_active=False) e invalida las sesiones del usuario.
    """
    queryset = Usuario.objects.all().order_by('username')
    permission_classes = [PermisoModular]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    modulo = 'usuarios'

    def get_serializer_class(self):
        if self.action == 'create':
            return UsuarioCreateSerializer
        return UsuarioSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # Por defecto solo activos; ?incluir_inactivos=1 muestra todos
        if self.request.query_params.get('incluir_inactivos') != '1':
            qs = qs.filter(is_active=True)
        area = self.request.query_params.get('area')
        laboratorio = self.request.query_params.get('laboratorio')
        buscar = self.request.query_params.get('buscar')
        if area:
            qs = qs.filter(area__iexact=area)
        if laboratorio:
            qs = qs.filter(laboratorio__iexact=laboratorio)
        if buscar:
            from django.db.models import Q
            qs = qs.filter(
                Q(username__icontains=buscar) | Q(first_name__icontains=buscar) |
                Q(last_name__icontains=buscar) | Q(email__icontains=buscar) |
                Q(cargo__icontains=buscar)
            )
        return qs

    def destroy(self, request, *args, **kwargs):
        """Soft delete: desactiva el usuario e invalida sus sesiones."""
        usuario = self.get_object()
        if usuario == request.user:
            return Response(
                {'detail': 'No puede desactivarse a sí mismo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if usuario.is_superuser:
            return Response(
                {'detail': 'Un superusuario no puede desactivarse desde el API.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        usuario.is_active = False
        usuario.save()
        invalidar_sesiones(usuario)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        """Reactiva un usuario desactivado."""
        usuario = self.get_object()
        usuario.is_active = True
        usuario.save()
        return Response(UsuarioSerializer(usuario).data)
    activar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def asignar_roles(self, request, pk=None):
        """
        Reemplaza los roles del usuario: {"roles": [1, 2]}.
        Los permisos se aplican inmediatamente (flujo 0.2).
        """
        usuario = self.get_object()
        ids = request.data.get('roles', [])
        roles = Rol.objects.filter(id__in=ids, is_active=True)
        if len(roles) != len(set(ids)):
            return Response(
                {'detail': 'Uno o más roles no existen o están inactivos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        actuales = {ru.rol_id: ru for ru in usuario.roles_asignados.all()}
        deseados = {rol.id for rol in roles}
        for rol_id, ru in actuales.items():
            nuevo_estado = rol_id in deseados
            if ru.is_active != nuevo_estado:
                ru.is_active = nuevo_estado
                ru.save()
        for rol in roles:
            if rol.id not in actuales:
                RolUsuario.objects.create(usuario=usuario, rol=rol)
        return Response(UsuarioSerializer(usuario).data)
    asignar_roles.operacion = 'editar'


class RolViewSet(viewsets.ModelViewSet):
    """
    CRUD de roles con su matriz de permisos anidada.
    El rol 'Administrador del Sistema' no puede modificarse ni eliminarse.
    """
    queryset = Rol.objects.all().order_by('nombre')
    serializer_class = RolSerializer
    permission_classes = [PermisoModular]
    modulo = 'usuarios'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('incluir_inactivos') != '1':
            qs = qs.filter(is_active=True)
        return qs

    def _proteger_admin(self, rol):
        # El propietario (superusuario) sí puede editar/eliminar el rol de
        # administrador; para el resto queda protegido contra cambios y escalada.
        es_super = bool(getattr(self.request, 'user', None) and self.request.user.is_superuser)
        if rol.es_admin_sistema and not es_super:
            return Response(
                {'detail': 'Solo el propietario del sistema puede modificar el rol de Administrador de Sistema.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def update(self, request, *args, **kwargs):
        bloqueo = self._proteger_admin(self.get_object())
        if bloqueo:
            return bloqueo
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Soft delete del rol."""
        rol = self.get_object()
        bloqueo = self._proteger_admin(rol)
        if bloqueo:
            return bloqueo
        rol.is_active = False
        rol.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PermisoViewSet(viewsets.ModelViewSet):
    """Gestión directa de permisos individuales (alternativa al anidado en Rol)."""
    queryset = Permiso.objects.all().select_related('rol')
    serializer_class = PermisoSerializer
    permission_classes = [PermisoModular]
    modulo = 'usuarios'

    def get_queryset(self):
        qs = super().get_queryset()
        rol_id = self.request.query_params.get('rol')
        if rol_id:
            qs = qs.filter(rol_id=rol_id)
        return qs


class RolUsuarioViewSet(viewsets.ModelViewSet):
    """Asignaciones individuales de rol a usuario."""
    queryset = RolUsuario.objects.all().select_related('usuario', 'rol')
    serializer_class = RolUsuarioSerializer
    permission_classes = [PermisoModular]
    modulo = 'usuarios'


class OpcionCatalogoViewSet(viewsets.ModelViewSet):
    """
    Catálogo gestionable de Áreas y Laboratorios para los desplegables.
    Filtros: ?tipo=area | ?tipo=laboratorio · ?incluir_inactivos=1
    """
    queryset = OpcionCatalogo.objects.all()
    serializer_class = OpcionCatalogoSerializer
    permission_classes = [PermisoModular]
    modulo = 'usuarios'

    def get_queryset(self):
        qs = super().get_queryset()
        tipo = self.request.query_params.get('tipo')
        if tipo:
            qs = qs.filter(tipo=tipo)
        if self.request.query_params.get('incluir_inactivos') != '1':
            qs = qs.filter(is_active=True)
        return qs

    def destroy(self, request, *args, **kwargs):
        """Soft delete: desactiva la opción (no se borra para conservar referencias)."""
        opcion = self.get_object()
        opcion.is_active = False
        opcion.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogAuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Log de auditoría: SOLO lectura y SOLO administradores (sección 0.3).
    Filtros: ?modulo= &accion= &usuario= &entidad= &desde= &hasta=
    """
    queryset = LogAuditoria.objects.all().order_by('-timestamp')
    serializer_class = LogAuditoriaSerializer
    permission_classes = [SoloAdministradores]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('modulo'):
            qs = qs.filter(modulo=p['modulo'])
        if p.get('accion'):
            qs = qs.filter(accion=p['accion'])
        if p.get('usuario'):
            qs = qs.filter(usuario_id=p['usuario'])
        if p.get('entidad'):
            qs = qs.filter(entidad=p['entidad'])
        if p.get('desde'):
            qs = qs.filter(timestamp__date__gte=p['desde'])
        if p.get('hasta'):
            qs = qs.filter(timestamp__date__lte=p['hasta'])
        return qs


class MeView(APIView):
    """GET /api/auth/me/ — usuario autenticado con sus permisos efectivos."""

    def get(self, request):
        return Response(MeSerializer(request.user, context={'request': request}).data)


class CambiarPasswordView(APIView):
    """POST /api/auth/cambiar-password/ — el usuario cambia su propia contraseña."""

    def post(self, request):
        serializer = CambiarPasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['password_nueva'])
        request.user.save()
        # Invalidar sesiones previas: deberá iniciar sesión con la nueva contraseña
        invalidar_sesiones(request.user)
        return Response({'detail': 'Contraseña actualizada. Vuelva a iniciar sesión.'})


class CatalogoView(APIView):
    """
    GET /api/configuracion/catalogo/ — módulos y operaciones del sistema.
    El frontend lo usa para renderizar la matriz de permisos de un rol.
    """

    def get(self, request):
        return Response({
            'modulos': [{'clave': clave, 'nombre': nombre} for clave, nombre in MODULOS],
            'operaciones': [{'clave': clave, 'nombre': nombre} for clave, nombre in OPERACIONES],
        })
