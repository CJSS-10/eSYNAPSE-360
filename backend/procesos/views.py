from datetime import date

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular

from .models import (EN_CURSO, ESTADOS_RESULTADO, FRECUENCIAS, TIPOS_PROCESO, Actividad, Aviso, DocumentoFicha,
                     Ficha, Indicador, Proceso, RegistroFicha, ResultadoIndicador)
from .serializers import (AvisoSerializer, FichaListaSerializer, FichaSerializer, ProcesoSerializer,
                          ResultadoSerializer)


def _error(mensaje, codigo=status.HTTP_400_BAD_REQUEST):
    return Response({'detail': mensaje}, status=codigo)


def _si(valor, defecto=None):
    if valor is None:
        return defecto
    return str(valor).strip().lower() in ('1', 'true', 'si', 'sí', 'yes', 'on')


def vinculados(proceso):
    """Lo que el sistema tiene registrado contra el proceso (y sus subprocesos)."""
    from esynapse_sig.models import Auditoria, Documento, Hallazgo, SolicitudAC
    ids = proceso.ids_con_subprocesos()
    hallazgos = Hallazgo.objects.filter(is_active=True, proceso_catalogo_id__in=ids)
    abiertos = hallazgos.exclude(estado__in=['cerrado', 'derivado'])
    sacs = SolicitudAC.objects.filter(Q(hallazgo__proceso_catalogo_id__in=ids)
                                      | Q(hallazgos_vinculados__proceso_catalogo_id__in=ids)).distinct()
    try:
        from quejas.models import Queja
        quejas = Queja.objects.filter(is_active=True, hallazgo__proceso_catalogo_id__in=ids)
        quejas_abiertas = quejas.exclude(estado='cerrada').count()
        quejas_total = quejas.count()
    except Exception:   # la app de quejas puede no estar instalada
        quejas_abiertas = quejas_total = 0
    anio = timezone.localdate().year
    nombres = [proceso.nombre] + list(proceso.subprocesos.filter(is_active=True).values_list('nombre', flat=True))
    q_aud = Q()
    for n in nombres:
        q_aud |= Q(areas_procesos__icontains=n)
    auditorias = Auditoria.objects.filter(q_aud).filter(
        Q(programa__anio=anio) | Q(fecha_inicio__year=anio)).distinct() if nombres else Auditoria.objects.none()
    documentos = Documento.objects.filter(is_active=True, archivado=False, proceso_catalogo_id__in=ids)
    return {
        'documentos': [{'id': d.id, 'codigo': d.codigo, 'titulo': d.titulo} for d in documentos],
        'nc_abiertas': abiertos.filter(tipo__in=['nc_mayor', 'nc_menor']).count(),
        'hallazgos_abiertos': [{'id': h.id, 'codigo': h.codigo, 'tipo': h.get_tipo_display(),
                                'estado': h.get_estado_display()} for h in abiertos[:20]],
        'sac_en_curso': sacs.exclude(estado__startswith='cerrada').count(),
        'quejas_abiertas': quejas_abiertas,
        'quejas_total': quejas_total,
        'auditorias_anio': auditorias.count(),
    }


class ProcesoViewSet(viewsets.ModelViewSet):
    """Catálogo oficial de procesos y su mapa."""
    queryset = Proceso.objects.all().select_related('padre', 'responsable')
    serializer_class = ProcesoSerializer
    permission_classes = [PermisoModular]
    modulo = 'procesos'

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list' and p.get('todos') != '1':
            qs = qs.filter(is_active=True)
        if p.get('tipo'):
            qs = qs.filter(tipo=p['tipo'])
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        anterior = serializer.instance.nombre
        p = serializer.save(updated_by=self.request.user)
        if p.nombre != anterior:
            # El texto que imprimen los formatos sigue al nombre del catálogo.
            from esynapse_sig.models import Documento, Hallazgo
            Hallazgo.objects.filter(proceso_catalogo=p).update(proceso=p.nombre[:100])
            Documento.objects.filter(proceso_catalogo=p).update(proceso=p.nombre[:100])

    def destroy(self, request, *args, **kwargs):
        """Desactiva el proceso (nunca se borra)."""
        p = self.get_object()
        if p.subprocesos.filter(is_active=True).exists():
            return _error('Desactive antes sus subprocesos o muévalos a otro proceso.')
        p.is_active = False
        p.updated_by = request.user
        p.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def reactivar(self, request, pk=None):
        p = self.get_object()
        p.is_active = True
        p.updated_by = request.user
        p.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return Response(ProcesoSerializer(p).data)
    reactivar.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'tipos': TIPOS_PROCESO, 'frecuencias': FRECUENCIAS, 'estados_resultado': ESTADOS_RESULTADO})
    catalogos.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def mapa(self, request):
        """Procesos activos por tipo, con su ficha, su indicador y lo pendiente."""
        bandas = {t: [] for t, _ in TIPOS_PROCESO}
        for p in Proceso.objects.filter(is_active=True, padre__isnull=True).select_related('responsable'):
            datos = ProcesoSerializer(p).data
            datos['subprocesos'] = ProcesoSerializer(p.subprocesos.filter(is_active=True), many=True).data
            datos['vinculados'] = vinculados(p)
            datos['semaforo'] = self._semaforo(p)
            bandas[p.tipo].append(datos)
        return Response({'bandas': [{'tipo': t, 'nombre': n, 'procesos': bandas[t]} for t, n in TIPOS_PROCESO]})
    mapa.operacion = 'leer'

    @staticmethod
    def _semaforo(proceso):
        """Peor estado de los últimos resultados de sus indicadores (None si no hay)."""
        ficha = proceso.ficha_vigente or proceso.ficha_en_curso
        if not ficha:
            return None
        peor = None
        orden = {'cumple': 0, 'en_riesgo': 1, 'no_cumple': 2}
        for ind in ficha.indicadores.all():
            r = ResultadoIndicador.objects.filter(proceso=proceso, indicador=ind.nombre, is_active=True).first()
            if r and (peor is None or orden[r.estado] > orden[peor]):
                peor = r.estado
        return peor

    @action(detail=True, methods=['get'])
    def vinculados(self, request, pk=None):
        return Response(vinculados(self.get_object()))
    vinculados.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def mapa_pdf(self, request):
        from .pdf import generar_mapa_pdf
        resp = HttpResponse(generar_mapa_pdf(), content_type='application/pdf')
        resp['Content-Disposition'] = 'inline; filename="mapa_de_procesos.pdf"'
        return resp
    mapa_pdf.operacion = 'leer'


class FichaViewSet(viewsets.ModelViewSet):
    """
    Ficha de caracterización por versiones: elaboración → revisión →
    aprobación → vigente. Solo la versión en elaboración se edita.
    """
    queryset = Ficha.objects.all().select_related('proceso', 'elaborado_por', 'revisado_por', 'aprobado_por')
    permission_classes = [PermisoModular]
    modulo = 'procesos'
    http_method_names = ['get', 'post', 'patch', 'put', 'head', 'options']

    def get_serializer_class(self):
        return FichaListaSerializer if self.action == 'list' else FichaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('proceso'):
            qs = qs.filter(proceso_id=p['proceso'])
        if p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        return qs

    def _respuesta(self, ficha, codigo=status.HTTP_200_OK):
        ficha = Ficha.objects.get(pk=ficha.pk)
        return Response(FichaSerializer(ficha, context={'request': self.request}).data, status=codigo)

    def create(self, request, *args, **kwargs):
        """Primera ficha de un proceso (versión 01). Las siguientes se crean con «nueva versión»."""
        proceso = Proceso.objects.filter(pk=request.data.get('proceso'), is_active=True).first()
        if not proceso:
            return _error('Indique un proceso activo del catálogo.')
        if proceso.fichas.exists():
            return _error('El proceso ya tiene ficha: para cambiarla cree una nueva versión.')
        ser = FichaSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        ficha = ser.save(version='01', created_by=request.user, updated_by=request.user)
        return self._respuesta(ficha, status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        f = self.get_object()
        if not f.editable:
            return _error(f'La ficha versión {f.version} está {f.get_estado_display().lower()}: la etapa de '
                          'elaboración está cerrada y su contenido es de solo lectura.')
        if 'proceso' in request.data and int(request.data['proceso']) != f.proceso_id:
            return _error('No se cambia el proceso de una ficha.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    # --- firmas ---
    def _firmar(self, request, ficha, rol):
        password = request.data.get('password') or ''
        if not password:
            return _error('Confirme con su contraseña para firmar.')
        if not request.user.check_password(password):
            return _error('Contraseña incorrecta. La firma no se aplicó.')
        u = request.user
        ficha.firmas = [x for x in (ficha.firmas or []) if x.get('rol') != rol] + [{
            'rol': rol, 'usuario_id': u.pk, 'nombre': u.get_full_name() or u.username, 'cargo': u.cargo,
            'sigla': u.sigla_cargo, 'fecha': timezone.localtime().isoformat(timespec='seconds'),
            'ip': get_client_ip(request), 'hash': ficha.calcular_hash()}]
        return None

    @action(detail=True, methods=['post'])
    def enviar(self, request, pk=None):
        """Elaboración → revisión, con la firma de quien elabora."""
        f = self.get_object()
        if f.estado != 'borrador':
            return _error('Solo se envía a revisión una ficha en elaboración.')
        falta = []
        if not f.objetivo.strip():
            falta.append('el objetivo')
        if not f.responsable.strip():
            falta.append('el responsable')
        if not f.alcance.strip():
            falta.append('el alcance')
        if not f.actividades.exists():
            falta.append('al menos una actividad')
        if f.version != '01' and not f.motivo_cambio.strip():
            falta.append('el motivo de la versión')
        if falta:
            return _error('Para enviar a revisión complete ' + ', '.join(falta) + '.')
        err = self._firmar(request, f, 'elaborado')
        if err:
            return err
        f.elaborado_por = request.user
        f.fecha_elaboracion = timezone.now()
        f.estado = 'en_revision'
        f.updated_by = request.user
        f.save()
        return self._respuesta(f)
    enviar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def revisar(self, request, pk=None):
        """Revisión conforme → aprobación (firma). Quien revisa no es quien elaboró."""
        f = self.get_object()
        if f.estado != 'en_revision':
            return _error('La ficha no está en revisión.')
        if f.elaborado_por_id == request.user.pk and not request.user.is_superuser:
            return _error('Quien elabora la ficha no puede revisarla.')
        err = self._firmar(request, f, 'revisado')
        if err:
            return err
        f.revisado_por = request.user
        f.fecha_revision = timezone.now()
        f.estado = 'en_aprobacion'
        f.updated_by = request.user
        f.save()
        return self._respuesta(f)
    revisar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def devolver(self, request, pk=None):
        """Revisión o aprobación → vuelve a elaboración con observaciones."""
        f = self.get_object()
        if f.estado not in ('en_revision', 'en_aprobacion'):
            return _error('Solo se devuelve una ficha en revisión o en aprobación.')
        comentarios = (request.data.get('comentarios') or '').strip()
        if not comentarios:
            return _error('Indique las observaciones para devolver la ficha.')
        f.devoluciones = list(f.devoluciones or []) + [{
            'fecha': timezone.localtime().isoformat(timespec='minutes'), 'etapa': f.get_estado_display(),
            'usuario': request.user.get_full_name() or request.user.username, 'comentarios': comentarios}]
        f.firmas = []
        f.elaborado_por = f.revisado_por = None
        f.fecha_elaboracion = f.fecha_revision = None
        f.estado = 'borrador'
        f.updated_by = request.user
        f.save()
        return self._respuesta(f)
    devolver.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        """Aprobación → vigente. La vigente anterior pasa a obsoleta y se atienden los avisos."""
        f = self.get_object()
        if f.estado != 'en_aprobacion':
            return _error('La ficha no está en aprobación.')
        if f.revisado_por_id == request.user.pk and not request.user.is_superuser:
            return _error('Quien revisó la ficha no puede aprobarla.')
        err = self._firmar(request, f, 'aprobado')
        if err:
            return err
        ahora = timezone.localtime()
        with transaction.atomic():
            Ficha.objects.filter(proceso=f.proceso, estado='vigente').update(estado='obsoleta', updated_by=request.user)
            f.aprobado_por = request.user
            f.fecha_aprobacion = ahora
            f.estado = 'vigente'
            f.hash_contenido = f.calcular_hash()
            f.updated_by = request.user
            f.save()
            Aviso.objects.filter(proceso=f.proceso, atendido=False).update(
                atendido=True, ficha_atencion=f, fecha_atencion=ahora, updated_by=request.user)
            if f.responsable and f.proceso.responsable_cargo != f.responsable:
                f.proceso.responsable_cargo = f.responsable
                f.proceso.save(update_fields=['responsable_cargo', 'updated_at'])
        return self._respuesta(f)
    aprobar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def nueva_version(self, request, pk=None):
        """Copia la ficha vigente en una nueva versión en elaboración, con su motivo."""
        f = self.get_object()
        if f.estado != 'vigente':
            return _error('La nueva versión se crea a partir de la ficha vigente.')
        if f.proceso.fichas.filter(estado__in=EN_CURSO).exists():
            return _error('Ya hay una versión en curso de esta ficha.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return _error('Indique el motivo de la nueva versión.')
        u = request.user
        with transaction.atomic():
            nueva = Ficha.objects.create(
                proceso=f.proceso, version=Ficha.siguiente_version(f.proceso), motivo_cambio=motivo,
                **{c: getattr(f, c) for c in Ficha.CAMPOS_CONTENIDO if c != 'motivo_cambio'},
                created_by=u, updated_by=u)
            for a in f.actividades.all():
                n = Actividad.objects.create(
                    ficha=nueva, orden=a.orden, seccion=a.seccion, proveedor_otro=a.proveedor_otro, entrada=a.entrada,
                    actividad=a.actividad, control=a.control, cliente_otro=a.cliente_otro, salida=a.salida,
                    created_by=u, updated_by=u)
                n.proveedores.set(a.proveedores.all())
                n.clientes.set(a.clientes.all())
            for d in f.documentos.all():
                DocumentoFicha.objects.create(ficha=nueva, orden=d.orden, documento=d.documento,
                                              descripcion=d.descripcion, created_by=u, updated_by=u)
            for r in f.registros.all():
                RegistroFicha.objects.create(ficha=nueva, orden=r.orden, descripcion=r.descripcion,
                                             created_by=u, updated_by=u)
            for i in f.indicadores.all():
                Indicador.objects.create(ficha=nueva, orden=i.orden, nombre=i.nombre, calculo=i.calculo, meta=i.meta,
                                         frecuencia=i.frecuencia, responsable=i.responsable, created_by=u,
                                         updated_by=u)
        return self._respuesta(nueva, status.HTTP_201_CREATED)
    nueva_version.operacion = 'crear'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf import generar_ficha_pdf
        f = self.get_object()
        resp = HttpResponse(generar_ficha_pdf(f), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="Ficha {f.proceso.nombre} v{f.version}.pdf"'
        return resp
    pdf.operacion = 'leer'


class AvisoViewSet(viewsets.ModelViewSet):
    """Avisos de «ficha por revisar»."""
    queryset = Aviso.objects.all().select_related('proceso', 'ficha_atencion', 'created_by')
    serializer_class = AvisoSerializer
    permission_classes = [PermisoModular]
    modulo = 'procesos'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('proceso'):
            qs = qs.filter(proceso_id=p['proceso'])
        if p.get('pendientes') == '1':
            qs = qs.filter(atendido=False)
        return qs

    def perform_create(self, serializer):
        if not (serializer.validated_data.get('motivo') or '').strip():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'motivo': ['Indique qué cambió en el proceso.']})
        serializer.save(origen='manual', created_by=self.request.user, updated_by=self.request.user)

    @action(detail=True, methods=['post'])
    def descartar(self, request, pk=None):
        """La ficha no requiere cambio: se cierra el aviso con su motivo."""
        a = self.get_object()
        if a.atendido:
            return _error('El aviso ya fue atendido.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return _error('Indique por qué la ficha no requiere cambios.')
        a.atendido = True
        a.descartado_motivo = motivo
        a.fecha_atencion = timezone.now()
        a.updated_by = request.user
        a.save()
        return Response(AvisoSerializer(a).data)
    descartar.operacion = 'editar'


class ResultadoViewSet(viewsets.ModelViewSet):
    """Resultados de los indicadores por periodo."""
    queryset = ResultadoIndicador.objects.filter(is_active=True).select_related('created_by')
    serializer_class = ResultadoSerializer
    permission_classes = [PermisoModular]
    modulo = 'procesos'

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('proceso'):
            qs = qs.filter(proceso_id=p['proceso'])
        if p.get('indicador'):
            qs = qs.filter(indicador=p['indicador'])
        return qs

    def perform_create(self, serializer):
        periodo = serializer.validated_data['periodo']
        if periodo > timezone.localdate().replace(day=1):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'periodo': ['No se registran resultados de periodos futuros.']})
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.updated_by = self.request.user
        instance.save(update_fields=['is_active', 'updated_by', 'updated_at'])
