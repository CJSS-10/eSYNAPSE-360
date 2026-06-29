"""
eSYNAPSE 360 — Rutas del API de la app core.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .configuracion import (
    ConfigPublicaView, ConfigSistemaView, ModuloToggleView, ModulosView,
)

from .views import (
    CambiarPasswordView,
    CatalogoView,
    LogAuditoriaViewSet,
    MeView,
    OpcionCatalogoViewSet,
    PermisoViewSet,
    RolUsuarioViewSet,
    RolViewSet,
    UsuarioViewSet,
)

router = DefaultRouter()
router.register('usuarios', UsuarioViewSet, basename='usuarios')
router.register('roles', RolViewSet, basename='roles')
router.register('permisos', PermisoViewSet, basename='permisos')
router.register('roles-usuarios', RolUsuarioViewSet, basename='roles-usuarios')
router.register('auditoria', LogAuditoriaViewSet, basename='auditoria')
router.register('opciones-catalogo', OpcionCatalogoViewSet, basename='opciones-catalogo')

urlpatterns = [
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/cambiar-password/', CambiarPasswordView.as_view(), name='cambiar_password'),
    path('configuracion/catalogo/', CatalogoView.as_view(), name='catalogo'),
    path('configuracion/publica/', ConfigPublicaView.as_view(), name='config-publica'),
    path('configuracion/sistema/', ConfigSistemaView.as_view(), name='config-sistema'),
    path('configuracion/modulos/', ModulosView.as_view(), name='config-modulos'),
    path('configuracion/modulos/<str:clave>/toggle/', ModuloToggleView.as_view(), name='config-modulo-toggle'),
    path('', include(router.urls)),
]
