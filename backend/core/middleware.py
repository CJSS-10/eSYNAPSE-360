"""
eSYNAPSE 360 — Middleware de auditoría automática.

Captura el usuario y la request actual en un contexto thread-local para que
las señales (signals.py) puedan registrar cada acción con: usuario, acción,
módulo, entidad, valor anterior, valor nuevo, timestamp e IP.

También registra automáticamente los intentos de acceso bloqueados (403/401).
"""
import threading

_thread_locals = threading.local()


def get_current_request():
    """Devuelve la request activa del hilo actual (o None)."""
    return getattr(_thread_locals, 'request', None)


def get_current_user():
    """Devuelve el usuario autenticado de la request activa (o None)."""
    request = get_current_request()
    if request is None:
        return None
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        return user
    return None


def get_client_ip(request):
    """Obtiene la IP real del cliente considerando proxies."""
    if request is None:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_user_agent(request):
    """Obtiene el user-agent (dispositivo/navegador) de la request."""
    if request is None:
        return ''
    return request.META.get('HTTP_USER_AGENT', '')[:255]


# Mapeo de prefijos de URL de API → módulo del sistema
URL_MODULO_MAP = {
    '/api/usuarios': 'usuarios',
    '/api/roles': 'usuarios',
    '/api/permisos': 'usuarios',
    '/api/auth': 'usuarios',
    '/api/auditoria': 'configuracion',
    '/api/configuracion': 'configuracion',
}


def resolver_modulo(path: str) -> str:
    """Deduce el módulo del sistema a partir de la ruta de la request."""
    for prefijo, modulo in URL_MODULO_MAP.items():
        if path.startswith(prefijo):
            return modulo
    return ''


class AuditoriaMiddleware:
    """
    Middleware de auditoría del eSYNAPSE 360.

    1. Publica la request en thread-local para que las señales de modelos
       (post_save / pre_save) registren quién hizo cada cambio y desde qué IP.
    2. Asigna created_by / updated_by automáticamente vía señales.
    3. Registra intentos de acceso bloqueados (401/403) en el log.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            response = self.get_response(request)
            self._registrar_acceso_bloqueado(request, response)
            return response
        finally:
            # Limpieza obligatoria: evita fugas de contexto entre requests
            _thread_locals.request = None

    def _registrar_acceso_bloqueado(self, request, response):
        """Registra en el log los intentos de acceso sin permiso (0.3 del documento de flujos)."""
        if response.status_code not in (401, 403):
            return
        # Evitar ruido: no registrar archivos estáticos ni favicon
        if not request.path.startswith('/api'):
            return
        from .models import LogAuditoria  # import diferido para evitar ciclos
        user = get_current_user()
        try:
            LogAuditoria.objects.create(
                usuario=user,
                usuario_nombre=(user.get_full_name() or user.username) if user else 'Anónimo',
                rol=', '.join(
                    ru.rol.nombre for ru in user.roles_asignados.filter(is_active=True).select_related('rol')
                ) if user else '',
                ip=get_client_ip(request),
                dispositivo=get_user_agent(request),
                modulo=resolver_modulo(request.path),
                accion='ACCESO_BLOQUEADO',
                entidad=request.path,
                valor_nuevo=f'HTTP {response.status_code} — {request.method}',
            )
        except Exception:
            # El log nunca debe tumbar la request
            pass
