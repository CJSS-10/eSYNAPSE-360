from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InduccionViewSet, PlantillaViewSet, ProgramaViewSet, SesionViewSet

router = DefaultRouter()
router.register('cap-programas', ProgramaViewSet, basename='cap-programas')
router.register('cap-sesiones', SesionViewSet, basename='cap-sesiones')
router.register('cap-inducciones', InduccionViewSet, basename='cap-inducciones')
router.register('cap-plantillas', PlantillaViewSet, basename='cap-plantillas')

urlpatterns = [path('', include(router.urls))]
