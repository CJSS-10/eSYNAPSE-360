from django.utils import timezone
from datetime import date

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from core.permissions import PermisoModular

from .models import (CAMPOS_PERFIL, MODALIDADES_SUMINISTRO, TENENCIAS, TIPOS_AREA, TIPOS_PUESTO, TIPOS_SUMINISTRO,
                     Area, Nivel, Puesto, Sede, Suministro, Trabajador, _hist, sincronizar_usuario)
from .serializers import (AreaSerializer, NivelSerializer, PuestoSerializer, SedeSerializer, SuministroSerializer,
                          TrabajadorSerializer)


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


class SedeViewSet(_Base):
    """Sedes de la organización, con sus niveles y suministros."""
    queryset = Sede.objects.all().select_related('responsable').prefetch_related('niveles')
    serializer_class = SedeSerializer

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._unica_principal(serializer.instance)

    def perform_update(self, serializer):
        obj = serializer.instance
        cambios = self._cambios(obj, serializer.validated_data)
        obj = serializer.save(updated_by=self.request.user)
        if cambios:
            _hist(obj, self.request.user, 'Actualización', campos=', '.join(cambios))
            obj.save(update_fields=['historial'])
        self._unica_principal(obj)

    def _unica_principal(self, sede):
        """Solo una sede es la principal (domicilio fiscal): marcar una desmarca las demás."""
        if not sede.principal:
            return
        for otra in Sede.objects.filter(principal=True).exclude(pk=sede.pk):
            otra.principal = False
            _hist(otra, self.request.user, 'Deja de ser la sede principal', motivo=f'ahora lo es {sede.nombre}')
            otra.save(update_fields=['principal', 'historial'])

    def destroy(self, request, *args, **kwargs):
        s = self.get_object()
        if s.areas.filter(is_active=True).exists():
            return self._error('La sede tiene áreas activas: muévalas a otra sede o desactívelas primero.')
        if s.suministros.filter(is_active=True).exists():
            return self._error('La sede tiene suministros activos: desactívelos primero.')
        s.is_active = False
        _hist(s, request.user, 'Desactivación')
        s.updated_by = request.user
        s.save(update_fields=['is_active', 'historial', 'updated_by', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'tenencias': TENENCIAS, 'tipos_suministro': TIPOS_SUMINISTRO,
                         'modalidades': MODALIDADES_SUMINISTRO})


class NivelViewSet(_Base):
    queryset = Nivel.objects.all().select_related('sede')
    serializer_class = NivelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('sede'):
            qs = qs.filter(sede_id=self.request.query_params['sede'])
        return qs

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(obj.sede, self.request.user, 'Nuevo nivel', campos=obj.nombre)
        obj.sede.save(update_fields=['historial'])

    def perform_update(self, serializer):
        antes = serializer.instance.nombre
        obj = serializer.save(updated_by=self.request.user)
        if obj.nombre != antes:
            _hist(obj.sede, self.request.user, 'Nivel renombrado', de=antes, a=obj.nombre)
            obj.sede.save(update_fields=['historial'])

    def destroy(self, request, *args, **kwargs):
        n = self.get_object()
        if n.areas.filter(is_active=True).exists():
            return self._error('El nivel tiene áreas activas: cámbielas de nivel primero.')
        if n.suministros.filter(is_active=True).exists():
            return self._error('El nivel tiene suministros activos: desactívelos primero.')
        n.is_active, n.updated_by = False, request.user
        n.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        _hist(n.sede, request.user, 'Nivel desactivado', campos=n.nombre)
        n.sede.save(update_fields=['historial'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def reactivar(self, request, pk=None):
        n = self.get_object()
        n.is_active, n.updated_by = True, request.user
        n.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return Response(self.get_serializer(n).data)
    reactivar.operacion = 'editar'


class SuministroViewSet(_Base):
    queryset = Suministro.objects.all().select_related('sede', 'nivel', 'responsable', 'sede__responsable')
    serializer_class = SuministroSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('sede'):
            qs = qs.filter(sede_id=p['sede'])
        if p.get('tipo'):
            qs = qs.filter(tipo=p['tipo'])
        return qs

    def perform_update(self, serializer):
        obj = serializer.instance
        cambios = self._cambios(obj, serializer.validated_data)
        obj = serializer.save(updated_by=self.request.user)
        if cambios:
            _hist(obj, self.request.user, 'Actualización', campos=', '.join(cambios))
            obj.save(update_fields=['historial'])

    def destroy(self, request, *args, **kwargs):
        """Se desactiva (deja de pedir registros); sus consumos se conservan."""
        s = self.get_object()
        s.is_active = False
        _hist(s, request.user, 'Desactivación')
        s.updated_by = request.user
        s.save(update_fields=['is_active', 'historial', 'updated_by', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AreaViewSet(_Base):
    queryset = Area.objects.all().select_related('padre', 'proceso', 'responsable', 'sede', 'nivel')
    serializer_class = AreaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('tipo'):
            qs = qs.filter(tipo=self.request.query_params['tipo'])
        if self.request.query_params.get('sede'):
            qs = qs.filter(sede_id=self.request.query_params['sede'])
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
            fecha = date.fromisoformat(request.data.get('fecha') or '') if request.data.get('fecha') else timezone.localdate()
        except ValueError:
            return self._error('Fecha de cese no válida.')
        if t.fecha_ingreso and fecha < t.fecha_ingreso:
            return self._error('La fecha de cese es anterior al ingreso.')
        t.estado, t.fecha_cese, t.motivo_cese = 'cesado', fecha, motivo
        datos = {'motivo': motivo}
        if t.usuario and request.data.get('desactivar_usuario', True) not in (False, 'false', '0'):
            u = t.usuario
            if u == request.user:
                return self._error('No puede registrar su propio cese con desactivación de su usuario.')
            if u.is_superuser and not request.user.is_superuser:
                return self._error('El usuario del propietario del sistema no se desactiva desde aquí.')
            if not request.user.tiene_permiso('usuarios', 'editar'):
                return self._error('Desactivar el usuario del sistema requiere el permiso de editar usuarios '
                                   '(registre el cese sin desactivarlo o pídalo a quien administra usuarios).')
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
            fecha = date.fromisoformat(request.data.get('fecha') or '') if request.data.get('fecha') else timezone.localdate()
        except ValueError:
            return self._error('Fecha de reingreso no válida.')
        _hist(t, request.user, 'Reingreso', cese_anterior=str(t.fecha_cese), motivo=t.motivo_cese)
        t.estado, t.fecha_ingreso, t.fecha_cese, t.motivo_cese = 'activo', fecha, None, ''
        t.updated_by = request.user
        t.save()
        return Response(self.get_serializer(t).data)
    reingresar.operacion = 'editar'
