from django.urls import include, path

from .panel import CalendarioView, MisTareasView
from rest_framework.routers import DefaultRouter

from .views import (
    AuditoriaViewSet,
    DocumentoViewSet,
    HallazgoViewSet,
    ProgramaAuditoriaViewSet,
    RequisitoNormaViewSet,
    SolicitudACViewSet,
    EquipoViewSet,
    CartaTrazabilidadViewSet,
)

router = DefaultRouter()
router.register('documentos', DocumentoViewSet, basename='documentos')
router.register('hallazgos', HallazgoViewSet, basename='hallazgos')
router.register('sac', SolicitudACViewSet, basename='sac')
router.register('auditorias', AuditoriaViewSet, basename='auditorias')
router.register('programas-auditoria', ProgramaAuditoriaViewSet, basename='programas-auditoria')
router.register('requisitos-norma', RequisitoNormaViewSet, basename='requisitos-norma')
router.register('equipos', EquipoViewSet, basename='equipos')
router.register('cartas-trazabilidad', CartaTrazabilidadViewSet, basename='cartas-trazabilidad')

urlpatterns = [
    path('mis-tareas/', MisTareasView.as_view(), name='mis-tareas'),
    path('calendario/', CalendarioView.as_view(), name='calendario'),
    path('', include(router.urls)),
]
