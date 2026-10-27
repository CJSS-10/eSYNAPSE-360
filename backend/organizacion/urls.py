from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AreaViewSet, NivelViewSet, PuestoViewSet, SedeViewSet, SuministroViewSet, TrabajadorViewSet

router = DefaultRouter()
router.register('org-sedes', SedeViewSet, basename='org-sedes')
router.register('org-niveles', NivelViewSet, basename='org-niveles')
router.register('org-suministros', SuministroViewSet, basename='org-suministros')
router.register('org-areas', AreaViewSet, basename='org-areas')
router.register('org-puestos', PuestoViewSet, basename='org-puestos')
router.register('org-trabajadores', TrabajadorViewSet, basename='org-trabajadores')

urlpatterns = [path('', include(router.urls))]
