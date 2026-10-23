from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EvaluacionViewSet, ObligacionViewSet, RequisitoViewSet

router = DefaultRouter()
router.register('requisitos-legales', RequisitoViewSet, basename='requisitos-legales')
router.register('obligaciones-legales', ObligacionViewSet, basename='obligaciones-legales')
router.register('evaluaciones-legales', EvaluacionViewSet, basename='evaluaciones-legales')

urlpatterns = [path('', include(router.urls))]
