from django.db.models import Max, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular

from .models import (AMBITOS, MEDIOS, RESULTADOS, ActualizacionAmbito, ComunicacionRequisito, Evaluacion, Obligacion,
                     Requisito, ResultadoEvaluacion)
from .serializers import (EvaluacionSerializer, ObligacionSerializer, RequisitoSerializer, ResultadoSerializer)

DIAS_EVALUACION = 183       # evaluación semestral


def _nombre(u):
    return u.get_full_name() or u.username


class _Base:
    permission_classes = [PermisoModular]
    modulo = 'legal'
    pagination_class = None
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def _error(self, mensaje, codigo=status.HTTP_400_BAD_REQUEST):
        return Response({'detail': mensaje}, status=codigo)

    def _pdf(self, contenido, nombre):
        resp = HttpResponse(contenido, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{nombre}.pdf"'
        return resp


def _hist(obj, request, accion, **datos):
    obj.historial = list(obj.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                  'usuario': _nombre(request.user), 'accion': accion, **datos}]


class RequisitoViewSet(_Base, viewsets.ModelViewSet):
    """Lista de requisitos legales y otros requisitos, por ámbito."""
    queryset = Requisito.objects.all().prefetch_related('procesos')
    serializer_class = RequisitoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action in ('list', 'lista_pdf'):
            qs = qs.filter(is_active=True)
        for campo in ('ambito', 'estado', 'tema'):
            if p.get(campo):
                qs = qs.filter(**{campo: p[campo]})
        if p.get('proceso'):
            qs = qs.filter(procesos__id=p['proceso'])
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(nombre__icontains=b) | Q(tipo__icontains=b)
                           | Q(modificatorias__icontains=b))
        return qs.distinct()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['lista'] = self.action == 'list'
        return ctx

    def _respuesta(self, r, codigo=status.HTTP_200_OK):
        return Response(RequisitoSerializer(Requisito.objects.get(pk=r.pk)).data, status=codigo)

    def perform_create(self, serializer):
        ambito = serializer.validated_data['ambito']
        orden = (Requisito.objects.filter(ambito=ambito).aggregate(m=Max('orden'))['m'] or 0) + 1
        r = serializer.save(orden=orden, created_by=self.request.user, updated_by=self.request.user)
        _hist(r, self.request, 'Identificación')
        r.save(update_fields=['historial'])
        ActualizacionAmbito.tocar(ambito, lista=True)

    def update(self, request, *args, **kwargs):
        r = self.get_object()
        if r.estado == 'derogada':
            return self._error('La norma está derogada: queda como registro y no se modifica.')
        if 'ambito' in request.data and request.data['ambito'] != r.ambito:
            return self._error('El ámbito no cambia; registre la norma en el ámbito correcto.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        r = serializer.save(updated_by=self.request.user)
        ActualizacionAmbito.tocar(r.ambito, lista=True)

    def destroy(self, request, *args, **kwargs):
        """Anula una norma registrada por error (sin obligaciones). Una norma que dejó de regir se deroga."""
        r = self.get_object()
        if r.obligaciones.filter(is_active=True).exists():
            return self._error('La norma tiene obligaciones: si dejó de regir, regístrela como derogada.')
        r.is_active = False
        r.updated_by = request.user
        r.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        ActualizacionAmbito.tocar(r.ambito, lista=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        temas = {}
        for amb, tema in Requisito.objects.filter(is_active=True).exclude(tema='') \
                .values_list('ambito', 'tema').order_by().distinct():
            temas.setdefault(amb, []).append(tema)
        temas_obl = {}
        for amb, tema in Obligacion.objects.filter(is_active=True).exclude(tema='') \
                .values_list('ambito', 'tema').order_by().distinct():
            temas_obl.setdefault(amb, []).append(tema)
        return Response({'ambitos': AMBITOS, 'resultados': RESULTADOS, 'medios': MEDIOS,
                         'temas': temas, 'temas_obligaciones': temas_obl})
    catalogos.operacion = 'leer'

    @action(detail=True, methods=['post'])
    def registrar_modificacion(self, request, pk=None):
        """Cambio normativo: modificatoria de la norma. Body: {descripcion, fecha}"""
        r = self.get_object()
        if r.estado == 'derogada':
            return self._error('La norma está derogada.')
        descripcion = (request.data.get('descripcion') or '').strip()
        if not descripcion:
            return self._error('Indique la norma modificatoria.')
        fecha = parse_date(request.data.get('fecha') or '') or timezone.localdate()
        linea = f'{descripcion} ({fecha.isoformat()})'
        r.modificatorias = '\n'.join(x for x in (r.modificatorias, linea) if x)
        _hist(r, request, 'Modificatoria', descripcion=descripcion, fecha_norma=fecha.isoformat())
        r.updated_by = request.user
        r.save(update_fields=['modificatorias', 'historial', 'updated_by', 'updated_at'])
        ActualizacionAmbito.tocar(r.ambito, lista=True)
        return self._respuesta(r)
    registrar_modificacion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def derogar(self, request, pk=None):
        """La norma deja de regir: sus obligaciones salen de las próximas evaluaciones. Body: {fecha, motivo}"""
        r = self.get_object()
        if r.estado == 'derogada':
            return self._error('La norma ya está derogada.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique la norma que la deroga o el motivo.')
        fecha = parse_date(request.data.get('fecha') or '') or timezone.localdate()
        r.estado, r.fecha_derogacion = 'derogada', fecha
        _hist(r, request, 'Derogación', motivo=motivo, fecha_norma=fecha.isoformat())
        r.updated_by = request.user
        r.save()
        for o in r.obligaciones.filter(is_active=True, estado='vigente'):
            o.estado = 'derogada'
            o.observaciones = '\n'.join(x for x in (o.observaciones, f'Derogado: {motivo}') if x)
            o.updated_by = request.user
            o.save(update_fields=['estado', 'observaciones', 'updated_by', 'updated_at'])
            o.resultados.filter(evaluacion__estado='en_curso', resultado='pendiente').update(
                resultado='no_aplica', observaciones=f'Norma derogada: {motivo}')
        ActualizacionAmbito.tocar(r.ambito, lista=True, matriz=True)
        return self._respuesta(r)
    derogar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def comunicar(self, request, pk=None):
        """Comunicación del requisito a las áreas. Body: {fecha, medio, destinatarios, resumen}"""
        r = self.get_object()
        medio = request.data.get('medio')
        if medio not in dict(MEDIOS):
            return self._error('Indique el medio.')
        destinatarios = (request.data.get('destinatarios') or '').strip()
        resumen = (request.data.get('resumen') or '').strip()
        if not destinatarios or not resumen:
            return self._error('Indique a quién se comunicó y qué (obligaciones, impactos y acciones requeridas).')
        fecha = parse_date(request.data.get('fecha') or '') or timezone.localdate()
        if fecha > timezone.localdate():
            return self._error('La fecha no puede ser futura.')
        ComunicacionRequisito.objects.create(requisito=r, fecha=fecha, medio=medio, destinatarios=destinatarios,
                                             resumen=resumen, created_by=request.user, updated_by=request.user)
        return self._respuesta(r, status.HTTP_201_CREATED)
    comunicar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def solicitar_cambio(self, request, pk=None):
        """Abre una solicitud de cambio (origen externo: requisitos legales) para adecuarse a la norma."""
        from cambios.models import Cambio
        from procesos.models import Proceso
        r = self.get_object()
        u = request.user
        if not (u.is_superuser or u.tiene_permiso('cambios', 'crear')):
            return self._error('No tiene permiso para registrar solicitudes de cambio.', status.HTTP_403_FORBIDDEN)
        proceso = r.procesos.first() or Proceso.objects.filter(nombre='Requisitos Legales').first()
        c = Cambio.objects.create(
            solicitante=u, proceso_solicitante=proceso, origen='externo', motivo_origen='Requisitos legales',
            descripcion=f'Adecuación a {r.denominacion}: {r.nombre}', justificacion=(request.data.get('justificacion')
                                                                                   or '').strip(),
            created_by=u, updated_by=u)
        _hist(r, request, 'Solicitud de cambio', cambio=c.codigo)
        r.save(update_fields=['historial'])
        return Response({'cambio_id': c.id, 'cambio_codigo': c.codigo}, status=status.HTTP_201_CREATED)
    solicitar_cambio.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def indicadores(self, request):
        from .indicadores import indicadores
        return Response(indicadores())
    indicadores.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def lista_pdf(self, request):
        from .pdf import generar_lista_pdf
        ambito = request.query_params.get('ambito') or 'sst'
        if ambito not in dict(AMBITOS):
            return self._error('Ámbito no válido.')
        reqs = list(Requisito.objects.filter(is_active=True, ambito=ambito).order_by('orden', 'id'))
        return self._pdf(generar_lista_pdf(ambito, reqs), f'Lista de requisitos legales - {ambito}')
    lista_pdf.operacion = 'leer'


class ObligacionViewSet(_Base, viewsets.ModelViewSet):
    """Obligaciones (artículos a cumplir) de la matriz de evaluación."""
    queryset = Obligacion.objects.all().select_related('requisito').prefetch_related('procesos')
    serializer_class = ObligacionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list':
            qs = qs.filter(is_active=True)
        for campo in ('ambito', 'estado', 'tema', 'requisito'):
            if p.get(campo):
                qs = qs.filter(**{campo: p[campo]})
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(documento_legal__icontains=b) | Q(articulo__icontains=b) | Q(extracto__icontains=b)
                           | Q(evidencia_documento__icontains=b) | Q(requisito__codigo__icontains=b))
        return qs

    def perform_create(self, serializer):
        ambito = serializer.validated_data['ambito']
        orden = (Obligacion.objects.filter(ambito=ambito).aggregate(m=Max('orden'))['m'] or 0) + 1
        o = serializer.save(orden=orden, created_by=self.request.user, updated_by=self.request.user)
        abierta = Evaluacion.objects.filter(ambito=ambito, estado='en_curso', is_active=True).first()
        if abierta:
            ResultadoEvaluacion.objects.create(evaluacion=abierta, obligacion=o, created_by=self.request.user,
                                               updated_by=self.request.user)
        ActualizacionAmbito.tocar(ambito, matriz=True)

    def update(self, request, *args, **kwargs):
        o = self.get_object()
        if o.estado == 'derogada':
            return self._error('La obligación está derogada: queda como registro.')
        if 'ambito' in request.data and request.data['ambito'] != o.ambito:
            return self._error('El ámbito no cambia.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        o = serializer.save(updated_by=self.request.user)
        ActualizacionAmbito.tocar(o.ambito, matriz=True)

    def destroy(self, request, *args, **kwargs):
        o = self.get_object()
        if o.resultados.filter(evaluacion__estado='cerrada').exists():
            return self._error('La obligación ya se evaluó: si dejó de aplicar, désela de baja con motivo.')
        if o.resultados.filter(evaluacion__estado='en_curso').exclude(resultado='pendiente').exists() or \
                o.resultados.filter(evaluacion__estado='en_curso').exclude(observaciones='').exists():
            return self._error('La obligación ya tiene un resultado registrado en la evaluación en curso: désela de '
                               'baja con motivo.')
        o.is_active = False
        o.updated_by = request.user
        o.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        # Solo quedan casillas pendientes y vacías de la evaluación en curso: se retiran (quedan en el log).
        o.resultados.filter(evaluacion__estado='en_curso', resultado='pendiente', observaciones='').delete()
        ActualizacionAmbito.tocar(o.ambito, matriz=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def dar_de_baja(self, request, pk=None):
        """La obligación deja de aplicar (queda como registro). Body: {motivo}"""
        o = self.get_object()
        if o.estado == 'derogada':
            return self._error('La obligación ya está dada de baja.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo.')
        o.estado = 'derogada'
        o.observaciones = '\n'.join(x for x in (o.observaciones, f'Baja: {motivo}') if x)
        o.updated_by = request.user
        o.save(update_fields=['estado', 'observaciones', 'updated_by', 'updated_at'])
        o.resultados.filter(evaluacion__estado='en_curso', resultado='pendiente').update(
            resultado='no_aplica', observaciones=f'Dada de baja: {motivo}')
        ActualizacionAmbito.tocar(o.ambito, matriz=True)
        return Response(ObligacionSerializer(o).data)
    dar_de_baja.operacion = 'editar'


class EvaluacionViewSet(_Base, viewsets.ModelViewSet):
    """Evaluación periódica del cumplimiento legal, por ámbito."""
    queryset = Evaluacion.objects.filter(is_active=True).select_related('cerrada_por').prefetch_related('resultados')
    serializer_class = EvaluacionSerializer
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get('ambito'):
            qs = qs.filter(ambito=p['ambito'])
        if p.get('anio'):
            qs = qs.filter(anio=p['anio'])
        return qs

    def create(self, request, *args, **kwargs):
        ambito = request.data.get('ambito')
        if ambito not in dict(AMBITOS):
            return self._error('Indique el ámbito.')
        if Evaluacion.objects.filter(ambito=ambito, estado='en_curso', is_active=True).exists():
            return self._error('Ya hay una evaluación en curso de este ámbito: ciérrela primero.')
        try:
            anio = int(request.data.get('anio') or timezone.localdate().year)
        except ValueError:
            return self._error('Año no válido.')
        periodo = (request.data.get('periodo') or '').strip()
        if not periodo:
            periodo = 'Semestre 1' if timezone.localdate().month <= 6 else 'Semestre 2'
        if Evaluacion.objects.filter(ambito=ambito, anio=anio, periodo__iexact=periodo, is_active=True).exists():
            return self._error(f'Ya existe la evaluación {anio} · {periodo} de este ámbito.')
        obligaciones = list(Obligacion.objects.filter(ambito=ambito, is_active=True, estado='vigente'))
        if not obligaciones:
            return self._error('El ámbito no tiene obligaciones vigentes que evaluar.')
        # Orden de las columnas de la matriz: el número del periodo («Semestre 2» → 2), o el siguiente.
        import re
        numero = re.search(r'(\d+)\s*$', periodo)
        orden = int(numero.group(1)) if numero else (Evaluacion.objects.filter(
            ambito=ambito, anio=anio, is_active=True).aggregate(m=Max('orden'))['m'] or 0) + 1
        u = request.user
        e = Evaluacion.objects.create(ambito=ambito, anio=anio, periodo=periodo, orden=orden, created_by=u,
                                      updated_by=u)
        ResultadoEvaluacion.objects.bulk_create([ResultadoEvaluacion(evaluacion=e, obligacion=o, created_by=u,
                                                                     updated_by=u) for o in obligaciones])
        return Response(EvaluacionSerializer(e).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Anula una evaluación abierta por error (sin resultados registrados)."""
        e = self.get_object()
        if e.estado != 'en_curso' or e.resultados.exclude(resultado='pendiente').exists():
            return self._error('Solo se anula una evaluación en curso sin resultados registrados.')
        e.is_active = False
        e.updated_by = request.user
        e.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def resultados(self, request, pk=None):
        e = self.get_object()
        qs = e.resultados.select_related('obligacion', 'obligacion__requisito', 'evaluado_por', 'hallazgo')
        p = request.query_params
        if p.get('resultado'):
            qs = qs.filter(resultado=p['resultado'])
        if p.get('tema'):
            qs = qs.filter(obligacion__tema=p['tema'])
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(obligacion__extracto__icontains=b) | Q(obligacion__documento_legal__icontains=b)
                           | Q(obligacion__articulo__icontains=b) | Q(obligacion__evidencia_documento__icontains=b))
        return Response(ResultadoSerializer(qs, many=True).data)
    resultados.operacion = 'leer'

    @action(detail=True, methods=['post'])
    def evaluar(self, request, pk=None):
        """Multipart: {resultado_id, resultado, observaciones, evidencia}"""
        e = self.get_object()
        if e.estado != 'en_curso':
            return self._error('La evaluación está cerrada: sus resultados no se modifican.')
        r = e.resultados.filter(pk=request.data.get('resultado_id')).first()
        if not r:
            return self._error('Resultado no encontrado.')
        resultado = request.data.get('resultado')
        if resultado not in ('cumple', 'no_cumple', 'no_aplica'):
            return self._error('Indique si cumple, no cumple o no aplica.')
        obs = (request.data.get('observaciones') or '').strip()
        if resultado in ('no_cumple', 'no_aplica') and not obs:
            return self._error('Explique el incumplimiento o por qué no aplica.')
        r.resultado, r.evaluado_por, r.fecha = resultado, request.user, timezone.localdate()
        if 'observaciones' in request.data:
            r.observaciones = obs
        if request.FILES.get('evidencia'):
            r.evidencia = request.FILES['evidencia']
        r.updated_by = request.user
        r.save()
        ActualizacionAmbito.tocar(e.ambito, matriz=True)
        return Response(ResultadoSerializer(r).data)
    evaluar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """Cierra la evaluación con firma; cada incumplimiento se registra como hallazgo. Body: {password}"""
        from esynapse_sig.models import Hallazgo
        e = self.get_object()
        if e.estado != 'en_curso':
            return self._error('La evaluación ya está cerrada.')
        pendientes = e.resultados.filter(resultado='pendiente').count()
        if pendientes:
            return self._error(f'Faltan evaluar {pendientes} obligación(es).')
        password = request.data.get('password') or ''
        if not password:
            return self._error('Confirme con su contraseña para firmar el cierre.')
        if not request.user.check_password(password):
            return self._error('Contraseña incorrecta. La evaluación no se cerró.')
        u, ahora = request.user, timezone.localtime()
        for r in e.resultados.filter(resultado='no_cumple', hallazgo=None).select_related('obligacion'):
            o = r.obligacion
            proceso = o.procesos.first()
            r.hallazgo = Hallazgo.objects.create(
                tipo='nc_menor', fuente='seguimiento',
                proceso=proceso.nombre if proceso else 'Requisitos Legales',
                descripcion=f'Incumplimiento legal ({e}): {o.documento} {o.articulo}. {o.extracto[:300]} '
                            f'— {r.observaciones}',
                requisito=f'{o.documento} {o.articulo}'.strip()[:200],
                fecha_deteccion=r.fecha or timezone.localdate(), created_by=u, updated_by=u)
            r.save(update_fields=['hallazgo'])
        e.estado, e.fecha_cierre, e.cerrada_por = 'cerrada', ahora, u
        e.firma = {'usuario_id': u.pk, 'nombre': _nombre(u), 'cargo': getattr(u, 'cargo', ''),
                   'sigla': getattr(u, 'sigla_cargo', ''), 'fecha': ahora.isoformat(timespec='seconds'),
                   'ip': get_client_ip(request)}
        e.updated_by = u
        e.save()
        return Response(EvaluacionSerializer(e).data)
    cerrar.operacion = 'aprobar'

    @action(detail=False, methods=['get'])
    def matriz_pdf(self, request):
        from .pdf import generar_matriz_pdf
        ambito = request.query_params.get('ambito') or 'sst'
        if ambito not in dict(AMBITOS):
            return self._error('Ámbito no válido.')
        try:
            anio = int(request.query_params.get('anio') or 0)
        except ValueError:
            anio = 0
        if not anio:
            ultima = Evaluacion.objects.filter(ambito=ambito, is_active=True).first()
            anio = ultima.anio if ultima else timezone.localdate().year
        return self._pdf(generar_matriz_pdf(ambito, anio), f'Matriz de evaluacion legal - {ambito} {anio}')
    matriz_pdf.operacion = 'leer'
