from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AspectoViewSet, ConsumoViewSet, DisposicionViewSet, PesajeViewSet

router = DefaultRouter()
router.register('amb-aspectos', AspectoViewSet, basename='amb-aspectos')
router.register('amb-consumos', ConsumoViewSet, basename='amb-consumos')
router.register('amb-pesajes', PesajeViewSet, basename='amb-pesajes')
router.register('amb-disposiciones', DisposicionViewSet, basename='amb-disposiciones')

urlpatterns = [path('', include(router.urls))]
