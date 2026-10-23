from datetime import date

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from core.permissions import PermisoModular

from .models import CAMPOS_PERFIL, TIPOS_AREA, TIPOS_PUESTO, Area, Puesto, Trabajador, _hist, sincronizar_usuario
from .serializers import AreaSerializer, PuestoSerializer, TrabajadorSerializer


class PermisoOrganizacion(BasePermission):
    """
    Datos maestros del núcleo: cualquier usuario activo los consulta (todos los módulos los usan);
    crearlos o modificarlos exige los permisos del módulo «organización».
    """
    message = PermisoModular.message

    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated or not u.is_active:
            return False
        if request.method in SAFE_METHODS:
            return True
        return PermisoModular().has_permission(request, view)


def _gestiona(user):
    return bool(user.is_superuser or user.tiene_permiso('organizacion', 'leer'))


class _Base(viewsets.ModelViewSet):
    permission_classes = [PermisoOrganizacion]
    modulo = 'organizacion'
    pagination_class = None

    def _error(self, mensaje):
        return Response({'detail': mensaje}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list' and self.request.query_params.get('todos') != '1':
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(obj, self.request.user, 'Registro')
        obj.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def _cambios(self, obj, nuevos):
        return [obj._meta.get_field(c).verbose_name for c, v in nuevos.items()
                if c in {f.name for f in obj._meta.concrete_fields} and getattr(obj, c) != v]

    @action(detail=True, methods=['post'])
    def reactivar(self, request, pk=None):
        obj = self.get_object()
        obj.is_active = True
        _hist(obj, request.user, 'Reactivación')
        obj.updated_by = request.user
        obj.save(update_fields=['is_active', 'historial', 'updated_by', 'updated_at'])
        return Response(self.get_serializer(obj).data)
    reactivar.operacion = 'editar'


class AreaViewSet(_Base):
    queryset = Area.objects.all().select_related('padre', 'proceso', 'responsable')
    serializer_class = AreaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('tipo'):
            qs = qs.filter(tipo=self.request.query_params['tipo'])
        return qs

    def perform_update(self, serializer):
        obj = serializer.instance
        cambios = self._cambios(obj, serializer.validated_data)
        nombre_antes = obj.nombre
        obj = serializer.save(updated_by=self.request.user)
        if cambios:
            _hist(obj, self.request.user, 'Actualización', campos=', '.join(cambios))
            obj.save(update_fields=['historial'])
        if obj.nombre != nombre_antes:
            for t in Trabajador.objects.filter(Q(area=obj) | Q(area__isnull=True, puesto__area=obj),
                                               usuario__isnull=False):
                sincronizar_usuario(t)

    def destroy(self, request, *args, **kwargs):
        a = self.get_object()
        if a.subareas.filter(is_active=True).exists():
            return self._error('El área tiene subáreas activas: muévalas o desactívelas primero.')
        if a.puestos.filter(is_active=True).exists():
            return self._error('El área tiene puestos activos: muévalos a otra área primero.')
        if a.trabajadores.filter(is_active=True, estado='activo').exists():
            return self._error('El área tiene trabajadores activos asignados.')
        a.is_active = False
        _hist(a, request.user, 'Desactivación')
        a.updated_by = request.user
        a.save(update_fields=['is_active', 'historial', 'updated_by', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'tipos_area': TIPOS_AREA, 'tipos_puesto': TIPOS_PUESTO})


class PuestoViewSet(_Base):
    queryset = Puesto.objects.all().select_related('area', 'reporta_a', 'proceso')
    serializer_class = PuestoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('area'):
            qs = qs.filter(area_id=p['area'])
        if p.get('tipo'):
            qs = qs.filter(tipo=p['tipo'])
        return qs

    def perform_update(self, serializer):
        obj = serializer.instance
        datos = serializer.validated_data
        perfil = [obj._meta.get_field(c).verbose_name for c in CAMPOS_PERFIL
                  if c in datos and (datos[c] or '') != (getattr(obj, c) or '')]
        otros = [c for c in self._cambios(obj, {k: v for k, v in datos.items() if k not in CAMPOS_PERFIL})]
        firma_antes = (obj.nombre, obj.sigla)
        obj = serializer.save(updated_by=self.request.user)
        if perfil:
            obj.version_perfil += 1
            _hist(obj, self.request.user, f'Perfil del puesto (versión {obj.version_perfil})', campos=', '.join(perfil))
        if otros:
            _hist(obj, self.request.user, 'Actualización', campos=', '.join(otros))
        if perfil or otros:
            obj.save(update_fields=['version_perfil', 'historial'])
        if (obj.nombre, obj.sigla) != firma_antes:
            for t in obj.trabajadores.filter(usuario__isnull=False):
                sincronizar_usuario(t)

    def destroy(self, request, *args, **kwargs):
        p = self.get_object()
        if p.trabajadores.filter(is_active=True, estado='activo').exists():
            return self._error('El puesto tiene trabajadores activos: cámbielos de puesto primero.')
        p.is_active = False
        _hist(p, request.user, 'Desactivación')
        p.updated_by = request.user
        p.save(update_fields=['is_active', 'historial', 'updated_by', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TrabajadorViewSet(_Base):
    queryset = Trabajador.objects.all().select_related('puesto', 'puesto__area', 'area', 'usuario')
    serializer_class = TrabajadorSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['ver_documento'] = _gestiona(self.request.user)
        return ctx

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list' and p.get('cesados') != '1':
            qs = qs.filter(estado='activo')
        if p.get('puesto'):
            qs = qs.filter(puesto_id=p['puesto'])
        if p.get('area'):
            qs = qs.filter(Q(area_id=p['area']) | Q(area__isnull=True, puesto__area_id=p['area']))
        if p.get('sin_usuario') == '1':
            qs = qs.filter(usuario__isnull=True)
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(nombres__icontains=b) | Q(apellidos__icontains=b) | Q(documento__icontains=b)
                           | Q(puesto__nombre__icontains=b))
        return qs

    def perform_create(self, serializer):
        super().perform_create(serializer)
        sincronizar_usuario(serializer.instance)

    def perform_update(self, serializer):
        obj = serializer.instance
        datos = serializer.validated_data
        cambios = self._cambios(obj, datos)
        puesto_antes = obj.puesto.nombre
        obj = serializer.save(updated_by=self.request.user)
        if cambios:
            extra = {'de': puesto_antes, 'a': obj.puesto.nombre} if obj.puesto.nombre != puesto_antes else {}
            _hist(obj, self.request.user, 'Cambio de puesto' if extra else 'Actualización',
                  campos=', '.join(cambios), **extra)
            obj.save(update_fields=['historial'])
        sincronizar_usuario(obj)

    def destroy(self, request, *args, **kwargs):
        return self._error('Un trabajador no se elimina: se registra su cese.')

    @action(detail=True, methods=['post'])
    def cesar(self, request, pk=None):
        """Cese del trabajador. Body: {fecha, motivo, desactivar_usuario (por defecto sí)}"""
        t = self.get_object()
        if t.estado == 'cesado':
            return self._error('El trabajador ya está cesado.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo del cese.')
        try:
            fecha = date.fromisoformat(request.data.get('fecha') or '') if request.data.get('fecha') else date.today()
        except ValueError:
            return self._error('Fecha de cese no válida.')
        if t.fecha_ingreso and fecha < t.fecha_ingreso:
            return self._error('La fecha de cese es anterior al ingreso.')
        t.estado, t.fecha_cese, t.motivo_cese = 'cesado', fecha, motivo
        datos = {'motivo': motivo}
        if t.usuario and request.data.get('desactivar_usuario', True) not in (False, 'false', '0'):
            u = t.usuario
            u.is_active = False
            u.save(update_fields=['is_active'])
            datos['usuario_sistema'] = f'{u.username} desactivado'
        _hist(t, request.user, 'Cese', **datos)
        t.updated_by = request.user
        t.save()
        return Response(self.get_serializer(t).data)
    cesar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def reingresar(self, request, pk=None):
        t = self.get_object()
        if t.estado != 'cesado':
            return self._error('El trabajador está activo.')
        try:
            fecha = date.fromisoformat(request.data.get('fecha') or '') if request.data.get('fecha') else date.today()
        except ValueError:
            return self._error('Fecha de reingreso no válida.')
        _hist(t, request.user, 'Reingreso', cese_anterior=str(t.fecha_cese), motivo=t.motivo_cese)
        t.estado, t.fecha_ingreso, t.fecha_cese, t.motivo_cese = 'activo', fecha, None, ''
        t.updated_by = request.user
        t.save()
        return Response(self.get_serializer(t).data)
    reingresar.operacion = 'editar'
