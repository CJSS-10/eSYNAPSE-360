"""
eSYNAPSE 360 — Rutas principales del proyecto.
"""
from django.contrib import admin
from django.urls import include, path, re_path
from core.media import MediaCookieView, servir_media
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # Autenticación JWT
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    # Acceso a los archivos subidos: solo usuarios del sistema (cookie firmada, ver core/media.py)
    path('api/auth/media/', MediaCookieView.as_view(), name='media_cookie'),
    re_path(r'^media/(?P<ruta>.+)$', servir_media, name='media'),
    # API core: usuarios, roles, permisos, auditoría
    path('api/', include('core.urls')),
    # API SIG Core: documentos (M6)
    path('api/', include('esynapse_sig.urls')),
    path('api/', include('quejas.urls')),
    path('api/', include('procesos.urls')),
    path('api/', include('cambios.urls')),
    path('api/', include('riesgos.urls')),
    path('api/', include('legal.urls')),
    path('api/', include('sst.urls')),
    path('api/', include('organizacion.urls')),
    path('api/', include('capacitacion.urls')),
    path('api/', include('ambiente.urls')),
    path('api/', include('revision.urls')),
    path('api/', include('tnc.urls')),
    path('api/', include('cumplimiento.urls')),
]

