"""API de cumplimiento: matriz por norma, evaluación de requisitos (con reflejo entre normas), brecha → hallazgo,
otros requisitos, tablero y cortes."""
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular

from . import servicio
from .models import (ESTADOS, FUENTES_ADICIONAL, NORMAS, CorteCumplimiento, EvaluacionRequisito, EvaluacionSede,
                     RequisitoAdicional, normas_equivalentes)

NOMBRE_ESTADO = dict(ESTADOS)
NOMBRE_NORMA = dict(NORMAS)
TIPOS_HALLAZGO_BRECHA = [('nc_mayor', 'No conformidad mayor'), ('nc_menor', 'No conformidad menor'),
                         ('observacion', 'Observación')]


def _nombre(u):
    return (u.get_full_name() or u.username) if u else ''


def _error(mensaje, **extra):
    return Response({'detail': mensaje, **extra}, status=status.HTTP_400_BAD_REQUEST)


def _requisito(data):
    """Devuelve (RequisitoNorma o None, RequisitoAdicional o None, error)."""
    from esynapse_sig.models import RequisitoNorma
    if data.get('requisito'):
        r = RequisitoNorma.objects.filter(pk=data['requisito'], es_seccion=False).first()
        if not r or r.norma not in NOMBRE_NORMA or r.codigo.endswith('.'):
            return None, None, 'El requisito no existe o no se evalúa.'
        return r, None, None
    if data.get('adicional'):
        a = RequisitoAdicional.objects.filter(pk=data['adicional'], is_active=True).first()
        if not a:
            return None, None, 'El requisito no existe o está dado de baja.'
        return None, a, None
    return None, None, 'Indique el requisito.'


def _nombre_requisito(req, adic):
    if req:
        return f'{NOMBRE_NORMA[req.norma]} {"S" if req.bloque == "seguimiento" else ""}{req.codigo}'
    return f'{adic.referencia} {adic.codigo}'.strip()


class CumplimientoViewSet(viewsets.ViewSet):
    permission_classes = [PermisoModular]
    modulo = 'cumplimiento'

    @action(detail=False, methods=['get'])
    def opciones(self, request):
        from esynapse_sig.models import Documento
        from procesos.models import Proceso
        return Response({
            'normas': NORMAS, 'estados': ESTADOS, 'fuentes': FUENTES_ADICIONAL, 'tipos_hallazgo': TIPOS_HALLAZGO_BRECHA,
            'procesos': [{'id': p.id, 'nombre': p.nombre} for p in
                         Proceso.objects.filter(is_active=True, padre__isnull=True).order_by('orden', 'nombre')],
            'documentos': [{'id': d.id, 'codigo': d.codigo, 'titulo': d.titulo} for d in
                           Documento.objects.filter(is_active=True, archivado=False).order_by('codigo')],
            'sedes': [{'id': x.id, 'nombre': x.nombre, 'codigo': x.codigo} for x in servicio.sedes_activas()],
        })
    opciones.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def matriz(self, request):
        norma = request.query_params.get('norma') or 'iso_9001'
        if norma == 'otros':
            filas = servicio.filas_adicionales(list(RequisitoAdicional.objects.filter(is_active=True, norma='')))
        elif norma in NOMBRE_NORMA:
            filas = servicio.matriz(norma)
        else:
            return _error('Norma no reconocida.')
        return Response({'norma': norma, 'filas': filas, 'resumen': servicio.resumen(filas),
                         'resumen_sedes': {str(x.id): servicio.resumen(filas, x.id) for x in servicio.sedes_activas()}})
    matriz.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def tablero(self, request):
        datos = servicio.tablero()
        datos['cortes'] = [{'id': c.id, 'fecha': c.fecha, 'resultados': c.resultados, 'observaciones': c.observaciones,
                            'registrado_por': c.firma.get('nombre', '')}
                           for c in CorteCumplimiento.objects.all()[:24]]
        return Response(datos)
    tablero.operacion = 'leer'

    @action(detail=False, methods=['post'])
    def evaluar(self, request):
        """Registra la evaluación de un requisito. Body: {requisito | adicional, estado, justificacion, proceso,
        como_se_cumple, documentos: [ids], evidencia, reflejar: bool}. Con «reflejar», una cláusula común de la
        estructura de alto nivel se registra igual en las otras normas ISO."""
        from esynapse_sig.models import Documento, RequisitoNorma
        from procesos.models import Proceso
        d = request.data
        req, adic, err = _requisito(d)
        if err:
            return _error(err)
        estado = d.get('estado')
        if estado not in NOMBRE_ESTADO or estado == 'sin_evaluar':
            return _error('Indique el estado: cumple, parcial, no cumple o no aplica.')
        justificacion = str(d.get('justificacion') or '').strip()
        if estado == 'no_aplica' and not justificacion:
            return _error('Justifique por qué el requisito no aplica.')
        proceso = None
        if d.get('proceso'):
            proceso = Proceso.objects.filter(pk=d['proceso'], is_active=True, padre__isnull=True).first()
            if not proceso:
                return _error('El proceso debe ser un proceso principal del catálogo.')
        como = str(d.get('como_se_cumple') or '').strip()
        evidencia = str(d.get('evidencia') or '').strip()
        if estado in ('cumple', 'parcial') and not (como or evidencia):
            return _error('Indique cómo se cumple o la evidencia.')
        docs = list(Documento.objects.filter(pk__in=d.get('documentos') or [], is_active=True))
        sedes_validas = {x.id: x for x in servicio.sedes_activas()}
        por_sede = []
        for item in d.get('sedes') or []:
            sede = sedes_validas.get(int(item.get('sede') or 0))
            est = item.get('estado') or 'sin_evaluar'
            if not sede or est not in NOMBRE_ESTADO:
                return _error('Sede o estado por sede no válido.')
            obs = str(item.get('observacion') or '').strip()
            if est != 'sin_evaluar' and not obs:
                return _error(f'Indique cómo se cumple o la evidencia en {sede.nombre} (estado «{NOMBRE_ESTADO[est].lower()}»).')
            por_sede.append((sede, est, obs))
        destinos = [(req, adic)]
        if req and d.get('reflejar', True):
            for n in normas_equivalentes(req.norma, req.codigo):
                eq = RequisitoNorma.objects.filter(norma=n, bloque='requisitos', codigo=req.codigo,
                                                   es_seccion=False).first()
                if eq:
                    destinos.append((eq, None))
        hoy, u = timezone.localdate(), request.user
        origen = _nombre_requisito(req, adic)
        with transaction.atomic():
            for i, (r, a) in enumerate(destinos):
                ev, _ = EvaluacionRequisito.objects.get_or_create(
                    requisito=r, adicional=a, defaults={'created_by': u, 'updated_by': u})
                antes = ev.estado
                ev.estado, ev.justificacion = estado, justificacion if estado == 'no_aplica' else ''
                ev.proceso, ev.como_se_cumple, ev.evidencia = proceso, como, evidencia
                ev.fecha_evaluacion, ev.evaluado_por, ev.updated_by = hoy, u, u
                entrada = {'fecha': timezone.localtime().isoformat(timespec='minutes'), 'usuario': _nombre(u),
                           'accion': 'Evaluación', 'de': NOMBRE_ESTADO.get(antes, antes),
                           'a': NOMBRE_ESTADO[estado], 'ip': get_client_ip(request)}
                if i:
                    entrada['reflejada_desde'] = origen
                ev.historial = list(ev.historial or []) + [entrada]
                ev.save()
                ev.documentos.set(docs)
                for sede, est, obs in por_sede:
                    es, _ = EvaluacionSede.objects.get_or_create(evaluacion=ev, sede=sede,
                                                                 defaults={'created_by': u, 'updated_by': u})
                    if (es.estado, es.observacion) != (est, obs):
                        ev.historial = list(ev.historial) + [{
                            'fecha': entrada['fecha'], 'usuario': _nombre(u), 'accion': f'Evaluación en {sede.nombre}',
                            'de': NOMBRE_ESTADO.get(es.estado), 'a': NOMBRE_ESTADO[est]}]
                    es.estado, es.observacion, es.fecha_evaluacion = est, obs, hoy
                    es.evaluado_por, es.updated_by = u, u
                    es.save()
                if por_sede:
                    ev.save(update_fields=['historial'])
        return Response({'reflejada_en': [_nombre_requisito(r, a) for r, a in destinos[1:]],
                         'evaluacion': servicio.evaluacion_dict(
                             EvaluacionRequisito.objects.get(requisito=req, adicional=adic))})
    evaluar.operacion = 'editar'

    @action(detail=False, methods=['post'])
    def hallazgo(self, request):
        """Registra la brecha de un requisito parcial o no cumplido como hallazgo. Body: {requisito | adicional,
        tipo, descripcion}"""
        from esynapse_sig.models import Hallazgo
        d = request.data
        req, adic, err = _requisito(d)
        if err:
            return _error(err)
        ev = EvaluacionRequisito.objects.filter(requisito=req, adicional=adic).select_related('hallazgo').first()
        sede = None
        if d.get('sede'):
            sede = next((x for x in servicio.sedes_activas() if str(x.id) == str(d['sede'])), None)
            if not sede:
                return _error('La sede no existe.')
        if sede:
            es = ev.sedes.filter(sede=sede).first() if ev else None
            estado = es.estado if es else 'sin_evaluar'
        else:
            estado = ev.estado if ev else 'sin_evaluar'
        if estado not in ('parcial', 'no_cumple'):
            donde = f' en {sede.nombre}' if sede else ' para el SIG completo'
            return _error(f'Solo se registra como hallazgo un requisito evaluado como parcial o no cumple{donde}.')
        if ev.hallazgo_id and ev.hallazgo.estado != 'cerrado':
            return _error(f'El requisito ya tiene el hallazgo {ev.hallazgo.codigo} abierto.')
        tipo = d.get('tipo')
        if tipo not in dict(TIPOS_HALLAZGO_BRECHA):
            return _error('Elija el tipo de hallazgo.')
        descripcion = str(d.get('descripcion') or '').strip()
        if not descripcion:
            return _error('Describa la brecha encontrada.')
        u = request.user
        nombre = _nombre_requisito(req, adic)
        with transaction.atomic():
            h = Hallazgo.objects.create(lugar=sede.nombre[:150] if sede else '',
                tipo=tipo, fuente='seguimiento',
                proceso=ev.proceso.nombre if ev.proceso_id else 'Sistema Integrado de Gestión',
                proceso_catalogo=ev.proceso, descripcion=f'Evaluación de cumplimiento ({nombre}): {descripcion}',
                requisito=nombre[:200], fecha_deteccion=timezone.localdate(), created_by=u, updated_by=u)
            ev.hallazgo, ev.updated_by = h, u
            ev.historial = list(ev.historial or []) + [{
                'fecha': timezone.localtime().isoformat(timespec='minutes'), 'usuario': _nombre(u),
                'accion': 'Brecha registrada como hallazgo', 'hallazgo': h.codigo}]
            ev.save()
        return Response({'hallazgo': h.id, 'codigo': h.codigo, 'evaluacion': servicio.evaluacion_dict(ev)},
                        status=status.HTTP_201_CREATED)
    hallazgo.operacion = 'crear'

    @action(detail=False, methods=['get'])
    def pdf(self, request):
        """Matriz de evaluación del cumplimiento. Query: norma (clave o «todas»), sede (id; vacío = SIG completo)."""
        from django.http import HttpResponse
        from .pdf import generar_matriz_pdf
        norma = request.query_params.get('norma') or 'todas'
        if norma == 'todas':
            normas = [n for n, _ in NORMAS]
        elif norma in NOMBRE_NORMA:
            normas = [norma]
        else:
            return _error('Norma no reconocida.')
        sede = None
        if request.query_params.get('sede'):
            sede = next((x for x in servicio.sedes_activas() if str(x.id) == request.query_params['sede']), None)
            if not sede:
                return _error('La sede no existe.')
        resp = HttpResponse(generar_matriz_pdf(normas, sede, request.user), content_type='application/pdf')
        nombre = 'Matriz de cumplimiento' + (f' {sede.nombre}' if sede else '')
        resp['Content-Disposition'] = f'inline; filename="{nombre}.pdf"'
        return resp
    pdf.operacion = 'leer'

    @action(detail=False, methods=['post'])
    def corte(self, request):
        """Guarda el resultado actual por norma como corte. Body: {observaciones}"""
        u = request.user
        c = CorteCumplimiento.objects.create(
            fecha=timezone.localdate(), resultados=servicio.resultados_corte(),
            observaciones=str(request.data.get('observaciones') or '').strip(),
            firma={'usuario_id': u.pk, 'nombre': _nombre(u), 'fecha': timezone.localtime().isoformat(timespec='seconds'),
                   'ip': get_client_ip(request)}, created_by=u, updated_by=u)
        return Response({'id': c.id, 'fecha': c.fecha, 'resultados': c.resultados}, status=status.HTTP_201_CREATED)
    corte.operacion = 'aprobar'


# ---------------------------------------------------------------------------------------------- otros requisitos
class RequisitoAdicionalSerializer(serializers.ModelSerializer):
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    norma_display = serializers.CharField(source='get_norma_display', read_only=True)

    class Meta:
        model = RequisitoAdicional
        fields = ['id', 'fuente', 'fuente_display', 'referencia', 'codigo', 'texto', 'norma', 'norma_display',
                  'orden', 'is_active', 'motivo_baja', 'historial']
        read_only_fields = ['is_active', 'motivo_baja', 'historial']


class RequisitoAdicionalViewSet(viewsets.ModelViewSet):
    permission_classes = [PermisoModular]
    modulo = 'cumplimiento'
    serializer_class = RequisitoAdicionalSerializer
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = RequisitoAdicional.objects.all()
        if self.request.query_params.get('bajas') != '1':
            qs = qs.filter(is_active=True)
        return qs

    def _hist(self, obj, accion, **extra):
        obj.historial = list(obj.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                      'usuario': _nombre(self.request.user), 'accion': accion,
                                                      **extra}]

    def perform_create(self, serializer):
        a = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        self._hist(a, 'Registro')
        a.save(update_fields=['historial'])

    def perform_update(self, serializer):
        if not serializer.instance.is_active:
            raise serializers.ValidationError({'detail': 'El requisito está dado de baja.'})
        a = serializer.save(updated_by=self.request.user)
        self._hist(a, 'Modificación')
        a.save(update_fields=['historial'])

    @action(detail=True, methods=['post'])
    def baja(self, request, pk=None):
        a = self.get_object()
        motivo = str(request.data.get('motivo') or '').strip()
        if not motivo:
            return _error('Indique el motivo de la baja.')
        a.is_active, a.motivo_baja, a.updated_by = False, motivo, request.user
        self._hist(a, 'Baja', motivo=motivo)
        a.save()
        return Response(RequisitoAdicionalSerializer(a).data)
    baja.operacion = 'eliminar'
