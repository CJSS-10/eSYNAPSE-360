"""Pendientes de trabajos y salidas no conformes para «Mis tareas»."""


def pendientes_tnc(usuario):
    from core.models import ModuloHabilitado

    from .models import TrabajoNoConforme
    from .views import puede_autorizar
    if 'trabajo_no_conforme' not in ModuloHabilitado.claves_habilitadas():
        return []
    try:
        t_usuario = usuario.trabajador
    except Exception:
        t_usuario = None
    tareas = []
    abiertos = TrabajoNoConforme.objects.filter(is_active=True).select_related('responsable_tratamiento')

    def tarea(t, titulo, estado):
        return {'tipo': 'tnc', 'modulo': 'Trabajo no conforme', 'ruta': '/trabajo-no-conforme', 'codigo': t.codigo,
                'titulo': f'{titulo}: {t.descripcion}'[:100], 'estado': estado,
                'fecha': t.fecha_deteccion.isoformat()}
    if t_usuario:
        for t in abiertos.filter(estado='tratamiento', responsable_tratamiento=t_usuario):
            tareas.append(tarea(t, 'Tratar', f'Nivel {t.get_nivel_riesgo_display()}'))
    if usuario.tiene_permiso('trabajo_no_conforme', 'aprobar'):
        for t in abiertos.filter(estado='registrado'):
            tareas.append(tarea(t, 'Asignar nivel de riesgo', 'Registrado'))
        for t in abiertos.filter(estado__in=('evaluacion', 'cierre')):
            tareas.append(tarea(t, 'Evaluar' if t.estado == 'evaluacion' else 'Cerrar', t.get_estado_display()))
    if usuario.tiene_permiso('trabajo_no_conforme', 'editar'):
        for t in abiertos.filter(estado='autorizacion'):
            if puede_autorizar(usuario, t) is None:
                tareas.append(tarea(t, 'Autorizar la reanudación', 'Por autorizar'))
    return tareas
