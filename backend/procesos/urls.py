from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AvisoViewSet, FichaViewSet, ProcesoViewSet, ResultadoViewSet

router = DefaultRouter()
router.register('procesos', ProcesoViewSet, basename='procesos')
router.register('fichas-proceso', FichaViewSet, basename='fichas-proceso')
router.register('avisos-proceso', AvisoViewSet, basename='avisos-proceso')
router.register('resultados-indicador', ResultadoViewSet, basename='resultados-indicador')

urlpatterns = [path('', include(router.urls))]
