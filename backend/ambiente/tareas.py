"""Pendientes de Medio ambiente para «Mis tareas»: el registro mensual del consumo de cada suministro activo."""
import calendar
from datetime import date

from django.utils import timezone

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre']
DIA_LIMITE = 5  # el consumo del mes se registra hasta el día 5 del mes siguiente


def lecturas_pendientes(usuario):
    """Suministros a cargo del puesto del usuario (o de la sede, si el suministro no tiene responsable) sin el consumo
    del mes anterior registrado."""
    from core.models import ModuloHabilitado
    from organizacion.models import Suministro

    from .models import ConsumoMensual
    if 'medio_ambiente' not in ModuloHabilitado.claves_habilitadas():
        return []
    try:
        trabajador = usuario.trabajador
    except Exception:
        trabajador = None
    if not trabajador or not trabajador.puesto_id or not usuario.tiene_permiso('medio_ambiente', 'crear'):
        return []
    hoy = timezone.localdate()
    anio, mes = (hoy.year, hoy.month - 1) if hoy.month > 1 else (hoy.year - 1, 12)
    fin_mes = date(anio, mes, calendar.monthrange(anio, mes)[1])
    tareas = []
    for s in Suministro.objects.filter(is_active=True, sede__is_active=True, created_at__date__lte=fin_mes) \
            .select_related('sede', 'nivel', 'responsable', 'sede__responsable'):
        resp = s.responsable_efectivo
        if not resp or resp.pk != trabajador.puesto_id:
            continue
        if ConsumoMensual.objects.filter(is_active=True, suministro=s, anio=anio, mes=mes).exists():
            continue
        tareas.append({
            'tipo': 'consumo', 'modulo': 'Medio ambiente', 'ruta': '/medio-ambiente',
            'codigo': s.numero or s.get_tipo_display(),
            'titulo': f'Registrar el consumo de {MESES[mes - 1]} {anio}: {s.nombre}'[:100],
            'estado': 'Vencido' if hoy.day > DIA_LIMITE else 'Pendiente',
            'fecha': date(hoy.year, hoy.month, DIA_LIMITE).isoformat(),
        })
    return tareas
