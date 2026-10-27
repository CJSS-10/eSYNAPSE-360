from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AcuerdoViewSet, ProgramaViewSet, RevisionViewSet

router = DefaultRouter()
router.register('rd-programas', ProgramaViewSet, basename='rd-programas')
router.register('rd-revisiones', RevisionViewSet, basename='rd-revisiones')
router.register('rd-acuerdos', AcuerdoViewSet, basename='rd-acuerdos')

urlpatterns = [path('', include(router.urls))]
