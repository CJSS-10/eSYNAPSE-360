from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CumplimientoViewSet, RequisitoAdicionalViewSet

router = DefaultRouter()
router.register('cumplimiento', CumplimientoViewSet, basename='cumplimiento')
router.register('cumplimiento-otros', RequisitoAdicionalViewSet, basename='cumplimiento-otros')

urlpatterns = [path('', include(router.urls))]
