from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CambioViewSet

router = DefaultRouter()
router.register('cambios', CambioViewSet, basename='cambios')

urlpatterns = [path('', include(router.urls))]
