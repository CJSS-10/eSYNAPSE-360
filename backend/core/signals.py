"""
eSYNAPSE 360 — Señales de auditoría automática.

Trabajan junto con AuditoriaMiddleware (middleware.py):
- pre_save:  captura valores anteriores y asigna created_by/updated_by
- post_save: registra CREAR/EDITAR con diff campo a campo
- pre_delete: registra ELIMINAR (los modelos del SIGE usan soft delete,
  pero si algo se borra físicamente, queda registrado)
- user_logged_in / user_logged_out / user_login_failed: sesiones
"""
from django.apps import apps
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db import transaction
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from .middleware import (
    get_client_ip,
    get_current_request,
    get_current_user,
    get_user_agent,
)

# Entidades core → módulo del sistema al que pertenecen
ENTIDAD_MODULO = {
    'Usuario': 'usuarios',
    'Rol': 'usuarios',
    'Permiso': 'usuarios',
    'RolUsuario': 'usuarios',
    'ConfiguracionSistema': 'configuracion',
    'ModuloHabilitado': 'configuracion',
    'Documento': 'documentos',
    'VersionDocumento': 'documentos',
    'VerificacionExterna': 'documentos',
    'Hallazgo': 'hallazgos',
    'SolicitudAC': 'acciones_correctivas',
    'AccionSAC': 'acciones_correctivas',
    'FirmaVersion': 'documentos',
    'ObservacionVersion': 'documentos',
    'ArchivoVersion': 'documentos',
    'Auditoria': 'auditorias',
    'ProgramaAuditoria': 'auditorias',
    'EquipoAuditoria': 'auditorias',
    'ActaAuditoria': 'auditorias',
    'ListaVerificacion': 'auditorias',
    'ItemVerificacion': 'auditorias',
    'RequisitoNorma': 'auditorias',
    'Equipo': 'equipos',
    'RegistroEquipo': 'equipos',
    'ActividadPrograma': 'equipos',
    'MovimientoEquipo': 'equipos',
    'InformeEquipo': 'equipos',
    'CartaTrazabilidad': 'equipos',
    'Area': 'organizacion',
    'Puesto': 'organizacion',
    'Trabajador': 'organizacion',
}

# Apps auditadas y módulo por defecto de sus entidades (regla 4: log en cada acción del sistema)
APP_MODULO = {
    'core': '', 'esynapse_sig': '', 'organizacion': 'organizacion', 'quejas': 'quejas', 'procesos': 'procesos',
    'cambios': 'cambios', 'riesgos': 'riesgos', 'legal': 'legal', 'sst': 'sst', 'capacitacion': 'capacitacion', 'ambiente': 'medio_ambiente',
    'revision': 'revision_direccion', 'tnc': 'trabajo_no_conforme', 'cumplimiento': 'cumplimiento',
}

# Campos que nunca se registran en el log (sensibles o ruido)
CAMPOS_EXCLUIDOS = {'password', 'pin', 'last_login', 'updated_at', 'created_at', 'created_by', 'updated_by'}

# Cache temporal de valores anteriores por instancia (pre_save → post_save)
_valores_anteriores = {}


def _log_model():
    return apps.get_model('core', 'LogAuditoria')


def _crear_log(**datos):
    """Registra en el log dentro de su propio punto de guardado: si falla, no deja abortada la transacción de la
    operación principal (PostgreSQL)."""
    with transaction.atomic():
        _log_model().objects.create(**datos)


def _modulo(instance):
    return ENTIDAD_MODULO.get(instance.__class__.__name__) or APP_MODULO.get(instance._meta.app_label, '')


def _es_auditable(instance) -> bool:
    """Solo se auditan modelos de las apps del SIGE, nunca el propio log."""
    if instance.__class__.__name__ == 'LogAuditoria':
        return False
    return instance._meta.app_label in APP_MODULO


def _datos_usuario():
    user = get_current_user()
    request = get_current_request()
    if user:
        roles = ', '.join(
            ru.rol.nombre
            for ru in user.roles_asignados.filter(is_active=True).select_related('rol')
        )
        nombre = user.get_full_name() or user.username
    else:
        roles, nombre = '', 'Sistema'
    return {
        'usuario': user,
        'usuario_nombre': nombre,
        'rol': roles,
        'ip': get_client_ip(request),
        'dispositivo': get_user_agent(request),
    }


def _serializar(valor):
    if valor is None:
        return None
    return str(valor)


@receiver(pre_save)
def auditoria_pre_save(sender, instance, **kwargs):
    if not _es_auditable(instance):
        return

    user = get_current_user()

    # Asignación automática de created_by / updated_by (regla #2 del CLAUDE.md)
    if user is not None:
        if instance.pk is None and hasattr(instance, 'created_by') and instance.created_by is None:
            instance.created_by = user
        if hasattr(instance, 'updated_by'):
            instance.updated_by = user

    # Capturar valores anteriores para el diff
    if instance.pk is not None:
        try:
            anterior = sender._base_manager.get(pk=instance.pk)
            _valores_anteriores[(sender.__name__, instance.pk)] = model_to_dict(
                anterior, exclude=list(CAMPOS_EXCLUIDOS)
            )
        except sender.DoesNotExist:
            pass


@receiver(post_save)
def auditoria_post_save(sender, instance, created, **kwargs):
    if not _es_auditable(instance):
        return

    entidad = sender.__name__
    base = _datos_usuario()
    base.update(
        modulo=_modulo(instance),
        entidad=entidad,
        entidad_id=str(instance.pk),
        referencia=str(instance)[:100],
    )

    try:
        if created:
            _crear_log(
                accion='CREAR',
                valor_nuevo=str(model_to_dict(instance, exclude=list(CAMPOS_EXCLUIDOS)))[:2000],
                **base,
            )
            return

        # Edición: registrar una entrada por cada campo modificado
        anterior = _valores_anteriores.pop((entidad, instance.pk), None)
        if anterior is None:
            _crear_log(accion='EDITAR', **base)
            return

        actual = model_to_dict(instance, exclude=list(CAMPOS_EXCLUIDOS))
        for campo, valor_nuevo in actual.items():
            valor_anterior = anterior.get(campo)
            if _serializar(valor_anterior) != _serializar(valor_nuevo):
                accion = 'EDITAR'
                # Soft delete detectado: is_active pasó de True a False
                if campo in ('is_active', 'estado') and valor_anterior and not valor_nuevo:
                    accion = 'ELIMINAR'
                _crear_log(
                    accion=accion,
                    campo=campo,
                    valor_anterior=(_serializar(valor_anterior) or '')[:4000] if valor_anterior is not None else None,
                    valor_nuevo=(_serializar(valor_nuevo) or '')[:4000] if valor_nuevo is not None else None,
                    **base,
                )
    except Exception:
        # La auditoría nunca debe tumbar la operación principal
        pass


@receiver(pre_delete)
def auditoria_pre_delete(sender, instance, **kwargs):
    if not _es_auditable(instance):
        return
    base = _datos_usuario()
    try:
        _crear_log(
            accion='ELIMINAR',
            modulo=_modulo(instance),
            entidad=sender.__name__,
            entidad_id=str(instance.pk),
            valor_anterior=str(model_to_dict(instance, exclude=list(CAMPOS_EXCLUIDOS)))[:2000],
            referencia=str(instance)[:100],
            **base,
        )
    except Exception:
        pass


@receiver(user_logged_in)
def auditoria_login(sender, request, user, **kwargs):
    try:
        _crear_log(
            accion='LOGIN',
            usuario=user,
            usuario_nombre=user.get_full_name() or user.username,
            ip=get_client_ip(request),
            dispositivo=get_user_agent(request),
            modulo='usuarios',
            entidad='Sesion',
        )
    except Exception:
        pass


@receiver(user_logged_out)
def auditoria_logout(sender, request, user, **kwargs):
    try:
        _crear_log(
            accion='LOGOUT',
            usuario=user,
            usuario_nombre=(user.get_full_name() or user.username) if user else 'Desconocido',
            ip=get_client_ip(request),
            dispositivo=get_user_agent(request),
            modulo='usuarios',
            entidad='Sesion',
        )
    except Exception:
        pass


@receiver(user_login_failed)
def auditoria_login_fallido(sender, credentials, request=None, **kwargs):
    try:
        _crear_log(
            accion='LOGIN_FALLIDO',
            usuario_nombre=credentials.get('username', 'Desconocido'),
            ip=get_client_ip(request),
            dispositivo=get_user_agent(request),
            modulo='usuarios',
            entidad='Sesion',
        )
    except Exception:
        pass
