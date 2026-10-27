"""Pendientes de la revisión por la dirección para «Mis tareas»: acuerdos del plan de acción a mi cargo sin cerrar."""
from django.utils import timezone


def acuerdos_pendientes(usuario):
    from core.models import ModuloHabilitado

    from .models import AcuerdoRevision
    if 'revision_direccion' not in ModuloHabilitado.claves_habilitadas():
        return []
    hoy = timezone.localdate()
    tareas = []
    for a in AcuerdoRevision.objects.filter(is_active=True, revision__is_active=True, revision__estado='cerrada',
                                            responsable__usuario=usuario).exclude(estado='cerrado') \
            .select_related('revision').order_by('fecha_compromiso'):
        vencido = bool(a.fecha_compromiso and a.fecha_compromiso < hoy)
        tareas.append({
            'tipo': 'acuerdo_rd', 'modulo': 'Revisión por la dirección', 'ruta': '/revision-direccion',
            'codigo': f'{a.revision.codigo} · {a.numero}', 'titulo': (a.descripcion or '')[:100],
            'estado': 'Vencido' if vencido else a.get_estado_display(),
            'fecha': a.fecha_compromiso.isoformat() if a.fecha_compromiso else None,
        })
    return tareas
