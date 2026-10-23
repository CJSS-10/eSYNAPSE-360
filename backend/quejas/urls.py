from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import QuejaViewSet

router = DefaultRouter()
router.register('quejas', QuejaViewSet, basename='quejas')

urlpatterns = [path('', include(router.urls))]
