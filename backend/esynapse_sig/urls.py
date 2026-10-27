from django.urls import include, path

from .panel import BuscarView, CalendarioView, MisTareasView
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
    NodoTrazabilidadViewSet,
    MagnitudEquipoViewSet,
    ClasificacionEquipoViewSet,
    SolicitudCambioEquipoViewSet,
    PuntoIntervaloViewSet,
    ResultadoIntervaloViewSet,
    MetodoCalibracionViewSet,
    ControlValidezViewSet,
    AutorizacionViewSet,
    ProcesoEntrenamientoViewSet,
    EvaluacionSeguimientoViewSet,
    SolicitudCambioCompetenciaViewSet,
    SolicitudCambioAuditoriaViewSet,
    FormatoImpresoViewSet,
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
router.register('nodos-trazabilidad', NodoTrazabilidadViewSet, basename='nodos-trazabilidad')
router.register('magnitudes-equipo', MagnitudEquipoViewSet, basename='magnitudes-equipo')
router.register('clasificaciones-equipo', ClasificacionEquipoViewSet, basename='clasificaciones-equipo')
router.register('solicitudes-cambio-equipo', SolicitudCambioEquipoViewSet, basename='solicitudes-cambio-equipo')
router.register('puntos-intervalo', PuntoIntervaloViewSet, basename='puntos-intervalo')
router.register('resultados-intervalo', ResultadoIntervaloViewSet, basename='resultados-intervalo')
router.register('metodos-calibracion', MetodoCalibracionViewSet, basename='metodos-calibracion')
router.register('controles-validez', ControlValidezViewSet, basename='controles-validez')
router.register('autorizaciones', AutorizacionViewSet, basename='autorizaciones')
router.register('procesos-entrenamiento', ProcesoEntrenamientoViewSet, basename='procesos-entrenamiento')
router.register('evaluaciones-seguimiento', EvaluacionSeguimientoViewSet, basename='evaluaciones-seguimiento')
router.register('solicitudes-competencia', SolicitudCambioCompetenciaViewSet, basename='solicitudes-competencia')
router.register('solicitudes-auditoria', SolicitudCambioAuditoriaViewSet, basename='solicitudes-auditoria')
router.register('formatos-impresos', FormatoImpresoViewSet, basename='formatos-impresos')

urlpatterns = [
    path('mis-tareas/', MisTareasView.as_view(), name='mis-tareas'),
    path('calendario/', CalendarioView.as_view(), name='calendario'),
    path('buscar/', BuscarView.as_view(), name='buscar'),
    path('', include(router.urls)),
]
