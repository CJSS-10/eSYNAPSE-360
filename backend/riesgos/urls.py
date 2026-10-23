from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ContextoViewSet, OportunidadMejoraViewSet, RevisionMatrizViewSet, RiesgoViewSet

router = DefaultRouter()
router.register('riesgos', RiesgoViewSet, basename='riesgos')
router.register('oportunidades-mejora', OportunidadMejoraViewSet, basename='oportunidades-mejora')
router.register('contexto-riesgos', ContextoViewSet, basename='contexto-riesgos')
router.register('revisiones-riesgos', RevisionMatrizViewSet, basename='revisiones-riesgos')

urlpatterns = [path('', include(router.urls))]
