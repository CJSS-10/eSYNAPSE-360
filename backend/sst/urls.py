from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .comite_api import AcuerdoViewSet, ComiteViewSet, ProgramaSSOMAViewSet, ReunionViewSet
from .epp_api import CatalogoEPPViewSet, EntregaEPPViewSet, EvaluacionMedicaViewSet, PerfilEPPViewSet
from .eventos_api import EnfermedadViewSet, EstadisticasViewSet, EventoViewSet
from .inspecciones_api import (ElementoViewSet, InspeccionViewSet, MonitoreoViewSet, PlantillaViewSet,
                               ProgramaMonitoreoViewSet, RecomendacionViewSet)
from .views import ATSTipoViewSet, ATSViewSet, IPERCViewSet

router = DefaultRouter()
router.register('sst-iperc', IPERCViewSet, basename='sst-iperc')
router.register('sst-ats-tipo', ATSTipoViewSet, basename='sst-ats-tipo')
router.register('sst-ats', ATSViewSet, basename='sst-ats')
router.register('sst-eventos', EventoViewSet, basename='sst-eventos')
router.register('sst-enfermedades', EnfermedadViewSet, basename='sst-enfermedades')
router.register('sst-estadisticas', EstadisticasViewSet, basename='sst-estadisticas')
router.register('sst-elementos', ElementoViewSet, basename='sst-elementos')
router.register('sst-plantillas', PlantillaViewSet, basename='sst-plantillas')
router.register('sst-inspecciones', InspeccionViewSet, basename='sst-inspecciones')
router.register('sst-programa-monitoreos', ProgramaMonitoreoViewSet, basename='sst-programa-monitoreos')
router.register('sst-monitoreos', MonitoreoViewSet, basename='sst-monitoreos')
router.register('sst-recomendaciones', RecomendacionViewSet, basename='sst-recomendaciones')
router.register('sst-epp-catalogo', CatalogoEPPViewSet, basename='sst-epp-catalogo')
router.register('sst-epp-matriz', PerfilEPPViewSet, basename='sst-epp-matriz')
router.register('sst-epp-entregas', EntregaEPPViewSet, basename='sst-epp-entregas')
router.register('sst-emo', EvaluacionMedicaViewSet, basename='sst-emo')
router.register('sst-comite', ComiteViewSet, basename='sst-comite')
router.register('sst-comite-reuniones', ReunionViewSet, basename='sst-comite-reuniones')
router.register('sst-comite-acuerdos', AcuerdoViewSet, basename='sst-comite-acuerdos')
router.register('sst-programa-ssoma', ProgramaSSOMAViewSet, basename='sst-programa-ssoma')

urlpatterns = [path('', include(router.urls))]
