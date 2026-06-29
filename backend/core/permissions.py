"""
eSYNAPSE 360 — Permisos granulares para DRF.

Cada ViewSet declara su módulo con el atributo `modulo` (debe existir en
core.constants.MODULOS). La clase PermisoModular traduce la acción del
ViewSet a una operación y la valida contra los roles del usuario:

    list / retrieve      → leer
    create               → crear
    update / partial     → editar
    destroy              → eliminar

Acciones personalizadas (@action) pueden declarar su operación con el
atributo `operacion` en el decorador, o se asume 'leer'.

Este es el cimiento de autorización que reutilizarán los 37 módulos.
"""
from rest_framework.permissions import BasePermission

ACCION_OPERACION = {
    'list': 'leer',
    'retrieve': 'leer',
    'create': 'crear',
    'update': 'editar',
    'partial_update': 'editar',
    'destroy': 'eliminar',
}


class PermisoModular(BasePermission):
    """
    Valida permisos granulares por módulo y operación.
    Requiere usuario autenticado y activo. El superusuario pasa siempre.
    """
    message = 'No tiene permiso para realizar esta operación en este módulo.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False

        modulo = getattr(view, 'modulo', None)
        if modulo is None:
            # ViewSet sin módulo declarado: solo superusuario (fail-safe)
            return bool(user.is_superuser)

        # Licenciamiento: un módulo no habilitado en esta instalación queda
        # bloqueado para TODOS (incluido el superusuario), para que "apagado"
        # signifique realmente apagado al vender el sistema por módulos.
        from .models import ModuloHabilitado
        if modulo not in ModuloHabilitado.claves_habilitadas():
            return False

        if user.is_superuser:
            return True

        operacion = self._resolver_operacion(view)
        return user.tiene_permiso(modulo, operacion)

    @staticmethod
    def _resolver_operacion(view) -> str:
        accion = getattr(view, 'action', None)
        # @action personalizada puede declarar su operación:
        #   @action(detail=True, methods=['post'])
        #   def aprobar(self, ...):   → ver atributo 'operacion' en el handler
        if accion and accion not in ACCION_OPERACION:
            handler = getattr(view, accion, None)
            return getattr(handler, 'operacion', 'leer')
        return ACCION_OPERACION.get(accion, 'leer')


class SoloAdministradores(BasePermission):
    """
    Acceso exclusivo para superusuarios o usuarios con rol de administrador
    del sistema. Se usa para el log de auditoría (sección 0.3 de flujos).
    """
    message = 'Solo los administradores del sistema pueden acceder a este recurso.'

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.is_superuser:
            return True
        return user.roles_asignados.filter(
            is_active=True, rol__is_active=True, rol__es_admin_sistema=True
        ).exists()


class SoloPropietario(BasePermission):
    """
    Nivel propietario del sistema: solo el superusuario de Django.

    Controla el LICENCIAMIENTO (qué módulos están activos por instalación).
    El "administrador de empresa" del cliente NO llega a este nivel, para que
    no pueda activarse módulos que no compró. El estatus de superusuario solo
    se otorga por línea de comandos (lo controla el dueño del sistema).
    """
    message = 'Solo el propietario del sistema puede gestionar el licenciamiento de módulos.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_superuser)
