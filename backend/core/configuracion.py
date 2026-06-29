"""
eSYNAPSE 360 — Configuración del sistema (marca white-label + licenciamiento).

- ConfigPublicaView   (público): marca + módulos habilitados; lo consume el
  frontend al arrancar, incluida la pantalla de login.
- ConfigSistemaView   (admin):   editar nombre, subtítulo, logo, color.
- ModulosView         (admin):   listar módulos y su estado.
- ModuloToggleView    (admin):   activar/desactivar un módulo respetando
  dependencias (al activar, activa sus dependencias; al desactivar, bloquea
  si otro módulo habilitado depende de él).
"""
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ConfiguracionSistema, ModuloHabilitado
from .permissions import SoloAdministradores, SoloPropietario


def _abs(url, request):
    if url and request is not None:
        return request.build_absolute_uri(url)
    return url


def _config_dict(cfg, request):
    return {
        'nombre_sistema': cfg.nombre_sistema,
        'nombre_corto': cfg.nombre_corto or cfg.nombre_sistema,
        'subtitulo': cfg.subtitulo,
        'logo_url': _abs(cfg.logo.url if cfg.logo else None, request),
        'logo_empresa_url': _abs(cfg.logo_empresa.url if cfg.logo_empresa else None, request),
        'color_primario': cfg.color_primario,
    }


class ConfigPublicaView(APIView):
    """Marca + módulos habilitados. Accesible sin autenticación (login)."""
    permission_classes = [AllowAny]

    def get(self, request):
        cfg = ConfiguracionSistema.cargar()
        data = _config_dict(cfg, request)
        data['modulos_habilitados'] = sorted(ModuloHabilitado.claves_habilitadas())
        return Response(data)


class ConfigSistemaView(APIView):
    """Edición de la marca (solo administradores)."""
    permission_classes = [SoloAdministradores]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        cfg = ConfiguracionSistema.cargar()
        data = _config_dict(cfg, request)
        data.update({
            'formato_hv_codigo': cfg.formato_hv_codigo,
            'formato_hv_elaborado': cfg.formato_hv_elaborado,
            'formato_hv_revisado': cfg.formato_hv_revisado,
            'formato_hv_aprobado': cfg.formato_hv_aprobado,
        })
        return Response(data)

    def patch(self, request):
        cfg = ConfiguracionSistema.cargar()
        es_propietario = bool(request.user and request.user.is_superuser)
        # Identidad del PRODUCTO (nombre del sistema, sigla, logo, color):
        # solo el propietario del sistema la modifica.
        if es_propietario:
            for campo in ('nombre_sistema', 'nombre_corto', 'color_primario'):
                if campo in request.data:
                    setattr(cfg, campo, request.data.get(campo) or '')
            if request.FILES.get('logo'):
                cfg.logo = request.FILES['logo']
        # Datos de la EMPRESA cliente (subtítulo y su logo): los ajusta el
        # administrador de sistema del cliente; se replican en sus formatos.
        if 'subtitulo' in request.data:
            cfg.subtitulo = request.data.get('subtitulo') or ''
        if request.FILES.get('logo_empresa'):
            cfg.logo_empresa = request.FILES['logo_empresa']
        # Formato de Hoja de Vida (Equipos): documento vinculado + siglas de firmas.
        for campo in ('formato_hv_codigo', 'formato_hv_elaborado',
                      'formato_hv_revisado', 'formato_hv_aprobado'):
            if campo in request.data:
                setattr(cfg, campo, request.data.get(campo) or '')
        if not cfg.nombre_sistema.strip():
            cfg.nombre_sistema = 'eSYNAPSE 360°'
        cfg.save()
        return Response(_config_dict(cfg, request))


def _modulo_dict(m):
    return {
        'clave': m.clave, 'nombre': m.nombre, 'habilitado': m.habilitado,
        'dependencias': m.dependencias or [], 'orden': m.orden,
    }


class ModulosView(APIView):
    """Lista de módulos y su estado de licenciamiento (solo el propietario)."""
    permission_classes = [SoloPropietario]

    def get(self, request):
        modulos = ModuloHabilitado.objects.all()
        return Response({'modulos': [_modulo_dict(m) for m in modulos]})


class ModuloToggleView(APIView):
    """Activa/desactiva un módulo respetando dependencias (solo el propietario)."""
    permission_classes = [SoloPropietario]

    def post(self, request, clave):
        try:
            m = ModuloHabilitado.objects.get(clave=clave)
        except ModuloHabilitado.DoesNotExist:
            return Response({'detail': 'Módulo no encontrado.'}, status=404)

        habilitar = str(request.data.get('habilitado', '')).strip().lower() in ('1', 'true', 'si', 'sí', 'yes', 'on')

        if habilitar:
            # Al activar, activa también sus dependencias (en cascada).
            activados = self._activar_con_dependencias(m)
            return Response({
                'modulos': [_modulo_dict(x) for x in ModuloHabilitado.objects.all()],
                'activados_en_cascada': activados,
            })

        # Al desactivar, bloquea si otro módulo habilitado depende de éste.
        dependientes = [
            x.nombre for x in ModuloHabilitado.objects.filter(habilitado=True)
            if clave in (x.dependencias or [])
        ]
        if dependientes:
            return Response(
                {'detail': f'No se puede desactivar "{m.nombre}": lo necesitan '
                           f'{", ".join(dependientes)}. Desactive primero esos módulos.'},
                status=400)
        m.habilitado = False
        m.save()
        return Response({'modulos': [_modulo_dict(x) for x in ModuloHabilitado.objects.all()]})

    def _activar_con_dependencias(self, modulo, _activados=None):
        if _activados is None:
            _activados = []
        if not modulo.habilitado:
            modulo.habilitado = True
            modulo.save()
        for dep in (modulo.dependencias or []):
            try:
                dm = ModuloHabilitado.objects.get(clave=dep)
            except ModuloHabilitado.DoesNotExist:
                continue
            if not dm.habilitado:
                _activados.append(dm.nombre)
                self._activar_con_dependencias(dm, _activados)
        return _activados
