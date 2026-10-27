from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from core.permissions import PermisoModular

from .models import (CONFORMIDAD_CLIENTE, ESTADOS_QUEJA, MEDIOS_COMUNICACION, MEDIOS_RECEPCION, MOTIVOS_QUEJA, ORIGENES_QUEJA,
                     TIPOS_COMUNICACION, TIPOS_RECLAMANTE, AdjuntoQueja, ComunicacionQueja, Queja)
from .serializers import QuejaListaSerializer, QuejaSerializer


def _si(valor):
    if valor is None:
        return None
    return str(valor).strip().lower() in ('1', 'true', 'si', 'sí', 'yes', 'on')


class QuejaViewSet(viewsets.ModelViewSet):
    """
    M18 — Quejas: recepción y registro → validación → evaluación e
    investigación → decisión → tratamiento → cierre con comunicación al
    cliente. Cada etapa cerrada queda de solo lectura.
    """
    queryset = Queja.objects.all().select_related('recibido_por', 'validado_por', 'decidido_por',
                                                  'responsable_acciones', 'notificado_por', 'hallazgo',
                                                  'created_by')
    permission_classes = [PermisoModular]
    modulo = 'quejas'
    parser_classes = [JSONParser, MultiPartParser, FormParser]


    def get_object(self):
        """Un registro anulado se consulta, pero no avanza en el flujo ni se modifica."""
        obj = super().get_object()
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS') and not getattr(obj, 'is_active', True):
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': f'{obj.codigo} está anulado: no se modifica.'})
        return obj
    def get_serializer_class(self):
        return QuejaListaSerializer if self.action == 'list' else QuejaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list' or self.action == 'seguimiento_pdf':
            qs = qs.filter(is_active=True)
        if p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        if p.get('abiertas') == '1':
            qs = qs.exclude(estado='cerrada')
        if p.get('origen'):
            qs = qs.filter(origen=p['origen'])
        if p.get('anio'):
            qs = qs.filter(fecha_recepcion__year=p['anio'])
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(empresa__icontains=b) | Q(descripcion__icontains=b)
                           | Q(orden_trabajo__icontains=b) | Q(contacto__icontains=b))
        return qs

    def _error(self, mensaje, codigo=status.HTTP_400_BAD_REQUEST):
        return Response({'detail': mensaje}, status=codigo)

    def _respuesta(self, queja, codigo=status.HTTP_200_OK):
        queja = Queja.objects.get(pk=queja.pk)
        return Response(QuejaSerializer(queja, context={'request': self.request}).data, status=codigo)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        """Solo se modifican los campos de las etapas abiertas."""
        q = self.get_object()
        if not q.is_active:
            return self._error('La queja está anulada.')
        abiertas = q.etapas_abiertas()
        for campo in request.data.keys():
            etapa = Queja.etapa_de_campo(campo)
            if etapa and etapa not in abiertas:
                nombre = Queja._meta.get_field(campo).verbose_name
                orden = [e for e, _ in ESTADOS_QUEJA]
                inicio = next(est[0] for n, est, _ in Queja.ETAPAS if n == etapa)
                situacion = ('aún no se abre' if orden.index(inicio) > orden.index(q.estado) else 'está cerrada')
                return self._error(f'La etapa de {Queja.NOMBRES_ETAPA[etapa]} {situacion} '
                                   f'({q.get_estado_display().lower()}): no se modifica «{nombre}».')
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Anula (baja lógica) una queja registrada por error, antes de validarla."""
        q = self.get_object()
        if q.estado != 'recibida' or q.fecha_validacion or q.reaperturas:
            return self._error('Solo se anula una queja aún no validada; después se trata hasta su cierre.')
        q.is_active = False
        q.updated_by = request.user
        q.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        """Opciones de los desplegables, como las define el procedimiento."""
        return Response({
            'origenes': ORIGENES_QUEJA, 'motivos': MOTIVOS_QUEJA, 'tipos_reclamante': TIPOS_RECLAMANTE,
            'medios_recepcion': MEDIOS_RECEPCION, 'medios_comunicacion': MEDIOS_COMUNICACION,
            'tipos_comunicacion': TIPOS_COMUNICACION, 'conformidad': CONFORMIDAD_CLIENTE,
        })
    catalogos.operacion = 'leer'

    # --- 2. Validación ---
    @action(detail=True, methods=['post'])
    def validar(self, request, pk=None):
        """¿La queja está relacionada con las actividades de la empresa?
        Body: {relacionada: bool, motivo}. No relacionada → cierre con motivos."""
        q = self.get_object()
        if q.estado != 'recibida':
            return self._error('La queja ya fue validada.')
        relacionada = _si(request.data.get('relacionada'))
        if relacionada is None:
            return self._error('Indique si la queja está relacionada con las actividades de la empresa.')
        motivo = (request.data.get('motivo') or '').strip()
        if not relacionada and not motivo:
            return self._error('Indique por qué la queja no está relacionada con las actividades de la empresa.')
        q.relacionada = relacionada
        q.motivo_validacion = motivo
        q.fecha_validacion = timezone.now()
        q.validado_por = request.user
        if relacionada:
            q.estado = 'en_evaluacion'
        else:
            q.resultado = 'no_relacionada'
            q.estado = 'en_cierre'
        q.updated_by = request.user
        q.save()
        return self._respuesta(q)
    validar.operacion = 'editar'

    # --- 4. Decisión ---
    @action(detail=True, methods=['post'])
    def decidir(self, request, pk=None):
        """Procedente o no procedente, con fundamento, sobre la evaluación registrada.
        Body: {procedente: bool, fundamento}."""
        q = self.get_object()
        if q.estado != 'en_evaluacion':
            return self._error('La decisión se toma con la queja en evaluación.')
        falta = []
        if not q.responsables.exists():
            falta.append('los responsables de la evaluación')
        if not q.fecha_evaluacion:
            falta.append('la fecha de evaluación')
        if not q.evaluacion.strip():
            falta.append('la evaluación de la queja')
        if not q.investigacion.strip():
            falta.append('la investigación / análisis de causas')
        if falta:
            return self._error('Para decidir registre antes ' + ', '.join(falta) + '.')
        procedente = _si(request.data.get('procedente'))
        if procedente is None:
            return self._error('Indique si la queja es procedente.')
        fundamento = (request.data.get('fundamento') or '').strip()
        if not fundamento:
            return self._error('Indique el fundamento de la decisión.')
        q.resultado = 'procedente' if procedente else 'no_procedente'
        q.fundamento_decision = fundamento
        q.fecha_decision = timezone.now()
        q.decidido_por = request.user
        q.estado = 'en_tratamiento' if procedente else 'en_cierre'
        q.updated_by = request.user
        q.save()
        return self._respuesta(q)
    decidir.operacion = 'aprobar'

    # --- 5. Tratamiento ---
    @action(detail=True, methods=['post'])
    def registrar_nc(self, request, pk=None):
        """Registra la queja procedente como No Conformidad en Hallazgos (procedencia
        Queja), que sigue el flujo de acción correctiva. Body: {tipo_nc, proceso, requisito}"""
        from esynapse_sig.models import Hallazgo
        q = self.get_object()
        if q.estado != 'en_tratamiento' or q.resultado != 'procedente':
            return self._error('La No Conformidad se registra durante el tratamiento de una queja procedente.')
        if q.hallazgo_id:
            return self._error(f'La queja ya está registrada como {q.hallazgo.codigo}.')
        tipo = request.data.get('tipo_nc')
        if tipo not in ('nc_mayor', 'nc_menor'):
            return self._error('Indique la clasificación de la No Conformidad (NC mayor o NC menor).')
        proceso = (request.data.get('proceso') or '').strip()
        if not proceso:
            return self._error('Indique el proceso afectado.')
        h = Hallazgo.objects.create(
            tipo=tipo, fuente='queja', proceso=proceso,
            descripcion=f'Queja {q.codigo} ({q.empresa}): {q.descripcion}',
            requisito=(request.data.get('requisito') or '').strip(),
            fecha_deteccion=timezone.localtime(q.fecha_recepcion).date(),
            responsable=q.responsable_acciones, created_by=request.user, updated_by=request.user)
        q.hallazgo = h
        q.updated_by = request.user
        q.save(update_fields=['hallazgo', 'updated_by', 'updated_at'])
        return self._respuesta(q)
    registrar_nc.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def pasar_a_cierre(self, request, pk=None):
        """Concluido el tratamiento y su seguimiento, la queja pasa a cierre."""
        q = self.get_object()
        if q.estado != 'en_tratamiento':
            return self._error('La queja no está en tratamiento.')
        falta = []
        if not q.acciones.strip():
            falta.append('las acciones a realizar')
        if not q.responsable_acciones_id:
            falta.append('el responsable de las acciones')
        if not q.seguimiento.strip() or not q.fecha_seguimiento:
            falta.append('el seguimiento de las acciones y su fecha')
        if falta:
            return self._error('Para pasar a cierre registre ' + ', '.join(falta) + '.')
        q.estado = 'en_cierre'
        q.updated_by = request.user
        q.save(update_fields=['estado', 'updated_by', 'updated_at'])
        return self._respuesta(q)
    pasar_a_cierre.operacion = 'editar'

    # --- 6. Cierre ---
    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """Cierra con la comunicación del resultado al cliente, notificada por
        alguien no involucrado en el origen de la queja.
        Body: {comunicacion_cliente, medio_cierre, conformidad_cliente, notificado_por}"""
        from core.models import Usuario
        q = self.get_object()
        if q.estado != 'en_cierre':
            return self._error('La queja no está en cierre.')
        texto = (request.data.get('comunicacion_cliente') or q.comunicacion_cliente or '').strip()
        medio = request.data.get('medio_cierre') or q.medio_cierre
        conformidad = request.data.get('conformidad_cliente') or q.conformidad_cliente
        if not texto:
            return self._error('Registre lo comunicado al cliente.')
        if medio not in dict(MEDIOS_COMUNICACION):
            return self._error('Indique el medio por el que se comunicó al cliente.')
        if q.resultado == 'procedente' and conformidad not in dict(CONFORMIDAD_CLIENTE):
            return self._error('Indique la conformidad del cliente con la resolución.')
        notificador = request.user
        if request.data.get('notificado_por'):
            notificador = Usuario.objects.filter(pk=request.data['notificado_por'], is_active=True).first()
            if not notificador:
                return self._error('Usuario que notifica no válido.')
        if q.involucrados.filter(pk=notificador.pk).exists():
            return self._error(f'{notificador.get_full_name() or notificador.username} está involucrado en el origen '
                               'de la queja: la notifica alguien del Área SIG o Comercial no involucrado.')
        ahora = timezone.localtime()
        ComunicacionQueja.objects.create(
            queja=q, tipo='resultado' if q.resultado == 'procedente' else 'no_procede', fecha=ahora, medio=medio,
            resumen=texto, created_by=request.user, updated_by=request.user)
        q.comunicacion_cliente = texto
        q.medio_cierre = medio
        q.conformidad_cliente = conformidad or ''
        q.notificado_por = notificador
        q.fecha_cierre = ahora
        q.estado = 'cerrada'
        q.updated_by = request.user
        q.save()
        return self._respuesta(q)
    cerrar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def reabrir(self, request, pk=None):
        """Reabre una queja cerrada, con motivo (p. ej. el cliente no quedó conforme).
        Vuelve a la etapa que corresponde a su resultado."""
        q = self.get_object()
        if q.estado != 'cerrada':
            return self._error('Solo se reabre una queja cerrada.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la reapertura.')
        q.reaperturas = list(q.reaperturas or []) + [{
            'fecha': timezone.localtime().isoformat(timespec='minutes'),
            'usuario': request.user.get_full_name() or request.user.username, 'motivo': motivo,
            'resultado': q.resultado, 'comunicacion_cliente': q.comunicacion_cliente,
            'conformidad_cliente': q.conformidad_cliente,
            'fecha_cierre': q.fecha_cierre.isoformat(timespec='minutes') if q.fecha_cierre else '',
        }]
        if q.resultado == 'procedente':
            q.estado = 'en_tratamiento'
        elif q.resultado == 'no_procedente':
            q.estado, q.resultado = 'en_evaluacion', ''
        else:
            q.estado, q.resultado, q.relacionada = 'recibida', '', None
        q.comunicacion_cliente, q.medio_cierre, q.conformidad_cliente = '', '', ''
        q.fecha_cierre, q.notificado_por = None, None
        q.updated_by = request.user
        q.save()
        return self._respuesta(q)
    reabrir.operacion = 'aprobar'

    # --- Comunicaciones y adjuntos ---
    @action(detail=True, methods=['post'])
    def comunicar(self, request, pk=None):
        """Registra una comunicación al reclamante. Multipart: {tipo, medio, resumen, fecha, evidencia}"""
        q = self.get_object()
        if q.estado == 'cerrada':
            return self._error('La queja está cerrada.')
        tipo = request.data.get('tipo')
        if tipo not in dict(TIPOS_COMUNICACION) or tipo in ('resultado', 'no_procede'):
            return self._error('Tipo de comunicación no válido (el resultado final se registra al cerrar).')
        if tipo == 'informe' and not q.fecha_validacion:
            return self._error('El informe de resultados se emite después de validar la queja.')
        medio = request.data.get('medio')
        if medio not in dict(MEDIOS_COMUNICACION):
            return self._error('Indique el medio de la comunicación.')
        resumen = (request.data.get('resumen') or '').strip()
        if not resumen:
            return self._error('Resuma lo comunicado.')
        fecha = timezone.now()
        if request.data.get('fecha'):
            from django.utils.dateparse import parse_datetime
            f = parse_datetime(request.data['fecha'])
            if not f:
                return self._error('Fecha no válida.')
            fecha = timezone.make_aware(f) if timezone.is_naive(f) else f
            if fecha > timezone.now() or fecha < q.fecha_recepcion:
                return self._error('La fecha de la comunicación debe estar entre la recepción y hoy.')
        ComunicacionQueja.objects.create(queja=q, tipo=tipo, medio=medio, resumen=resumen, fecha=fecha,
                                         evidencia=request.FILES.get('evidencia'),
                                         created_by=request.user, updated_by=request.user)
        return self._respuesta(q, status.HTTP_201_CREATED)
    comunicar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def adjuntar(self, request, pk=None):
        """Adjunta un documento de sustento. Multipart: {archivo, descripcion}"""
        q = self.get_object()
        if q.estado == 'cerrada':
            return self._error('La queja está cerrada.')
        if not request.FILES.get('archivo'):
            return self._error('Falta el archivo.')
        AdjuntoQueja.objects.create(queja=q, archivo=request.FILES['archivo'],
                                    descripcion=(request.data.get('descripcion') or '').strip(),
                                    created_by=request.user, updated_by=request.user)
        return self._respuesta(q, status.HTTP_201_CREATED)
    adjuntar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_adjunto(self, request, pk=None):
        """Baja lógica de un adjunto mientras la queja no está cerrada. Body: {adjunto_id}"""
        q = self.get_object()
        if q.estado == 'cerrada':
            return self._error('La queja está cerrada.')
        a = q.adjuntos.filter(pk=request.data.get('adjunto_id'), is_active=True).first()
        if not a:
            return self._error('Adjunto no encontrado.')
        a.is_active = False
        a.updated_by = request.user
        a.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return self._respuesta(q)
    quitar_adjunto.operacion = 'editar'

    # --- Formatos impresos ---
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Reporte de Quejas."""
        from .pdf import generar_reporte_queja_pdf
        q = self.get_object()
        resp = HttpResponse(generar_reporte_queja_pdf(q), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{q.codigo}.pdf"'
        return resp
    pdf.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def seguimiento_pdf(self, request):
        """Registro de Seguimiento de Quejas (con los filtros del listado)."""
        from .pdf import generar_seguimiento_quejas_pdf
        quejas = list(self.filter_queryset(self.get_queryset()).order_by('fecha_recepcion', 'id'))
        resp = HttpResponse(generar_seguimiento_quejas_pdf(quejas), content_type='application/pdf')
        resp['Content-Disposition'] = 'inline; filename="seguimiento_quejas.pdf"'
        return resp
    seguimiento_pdf.operacion = 'leer'
