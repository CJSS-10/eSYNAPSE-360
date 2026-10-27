"""
Archivos subidos (/media) solo para usuarios del sistema (César, 2026-10-24).

El navegador pide los archivos (enlaces, imágenes, PDF adjuntos) sin la cabecera del token, así que al iniciar sesión
—y en cada renovación— el sistema entrega una cookie firmada, solo para /media, que identifica al usuario. Cada archivo
se sirve si la cookie es válida y el usuario sigue activo. Única excepción: los logos de la configuración, que se ven en
la pantalla de ingreso.
"""
import mimetypes
import os

from django.conf import settings
from django.core import signing
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils._os import safe_join
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

COOKIE = 'esynapse_media'
SAL = 'esynapse-media'
PUBLICOS = ('config/',)  # logos de la pantalla de ingreso


def _duracion():
    jwt = getattr(settings, 'SIMPLE_JWT', {})
    return int(jwt.get('REFRESH_TOKEN_LIFETIME').total_seconds()) if jwt.get('REFRESH_TOKEN_LIFETIME') else 86400


class MediaCookieView(APIView):
    """POST: entrega (o renueva) la cookie de acceso a archivos. DELETE: la retira al cerrar sesión."""
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # Retirar la cookie no requiere sesión válida (al expirar la sesión también se retira).
        return [AllowAny()] if self.request.method == 'DELETE' else [IsAuthenticated()]

    def post(self, request):
        r = Response({'ok': True})
        r.set_cookie(COOKIE, signing.dumps({'u': request.user.pk}, salt=SAL), max_age=_duracion(), path='/media/',
                     httponly=True, samesite='Lax', secure=not settings.DEBUG)
        return r

    def delete(self, request):
        r = Response({'ok': True})
        r.delete_cookie(COOKIE, path='/media/')
        return r


def _usuario_de_cookie(request):
    valor = request.COOKIES.get(COOKIE)
    if not valor:
        return None
    try:
        datos = signing.loads(valor, salt=SAL, max_age=_duracion())
    except signing.BadSignature:
        return None
    from .models import Usuario
    return Usuario.objects.filter(pk=datos.get('u'), is_active=True).first()


def servir_media(request, ruta):
    ruta = ruta.lstrip('/')
    if not ruta.startswith(PUBLICOS) and _usuario_de_cookie(request) is None:
        return HttpResponseForbidden('Archivo disponible solo para usuarios del sistema: inicie sesión.')
    try:
        completo = safe_join(str(settings.MEDIA_ROOT), ruta)
    except Exception:  # intento de salir de la carpeta de archivos
        raise Http404
    if not os.path.isfile(completo):
        raise Http404
    tipo, _ = mimetypes.guess_type(completo)
    respuesta = FileResponse(open(completo, 'rb'), content_type=tipo or 'application/octet-stream')
    respuesta['X-Content-Type-Options'] = 'nosniff'
    respuesta['Cache-Control'] = 'private, max-age=0'
    return respuesta
