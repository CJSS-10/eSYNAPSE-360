"""API de Medio ambiente: matriz de aspectos e impactos (con aprobación del Comité de SST), consumos de energía y
agua, pesajes y disposición de residuos, y resumen anual de residuos."""
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular

from .models import (ALCANCES, CATEGORIAS_RESIDUO, CLASES, CRITERIOS, DESTINOS, ETAPAS_CICLO, GENERACION,
                     GRUPOS_DISPOSICION, SITUACIONES, TIPOS_CONSUMO, TIPOS_PESAJE, TIPOS_SUGERIDOS, UNIDAD_CONSUMO,
                     VALORACION, AprobacionMatrizAmbiental, AspectoAmbiental, ConsumoMensual, DisposicionResiduos,
                     PesajeResiduos, estado_aprobacion_matriz)

MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre',
         'Noviembre', 'Diciembre']
CAMPOS_CRITERIO = [c for c, _ in CRITERIOS]


def _nombre(u):
    return (u.get_full_name() or u.username) if u else ''


def _firma(request):
    u = request.user
    return {'usuario_id': u.pk, 'nombre': _nombre(u), 'cargo': getattr(u, 'cargo', ''),
            'sigla': getattr(u, 'sigla_cargo', ''), 'fecha': timezone.localtime().isoformat(timespec='seconds'),
            'ip': get_client_ip(request)}


def _hist(obj, request, accion, **datos):
    obj.historial = list(obj.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                  'usuario': _nombre(request.user), 'accion': accion, **datos}]


def _url(f):
    return f.url if f else None


def _decimal(v):
    try:
        return Decimal(str(v).replace(',', '.')) if v not in (None, '') else None
    except InvalidOperation:
        return None


def _anio(request):
    v = str(request.query_params.get('anio') or '')
    return int(v) if v.isdigit() else timezone.localdate().year


def legal_sugerido(obligacion):
    """Criterio A propuesto desde la última evaluación de cumplimiento de la obligación: no cumple → 3,
    pendiente → 2, cumple o no aplica → 1. None si nunca se evaluó."""
    if not obligacion:
        return None
    from legal.models import ResultadoEvaluacion
    r = (ResultadoEvaluacion.objects.filter(obligacion=obligacion, evaluacion__is_active=True)
         .order_by('-evaluacion__anio', '-evaluacion__orden', '-id').first())
    if not r:
        return None
    return {'no_cumple': 3, 'pendiente': 2}.get(r.resultado, 1)


class _Base:
    permission_classes = [PermisoModular]
    modulo = 'medio_ambiente'
    pagination_class = None

    def _error(self, mensaje, **extra):
        return Response({'detail': mensaje, **extra}, status=status.HTTP_400_BAD_REQUEST)

    def _clave(self, request, que):
        password = request.data.get('password') or ''
        if not password:
            return self._error(f'Confirme con su contraseña para firmar {que}.')
        if not request.user.check_password(password):
            return self._error(f'Contraseña incorrecta. No se registró {que}.')
        return None

    def _pdf(self, contenido, nombre):
        resp = HttpResponse(contenido, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{nombre}.pdf"'
        return resp


# ============================================================================================== aspectos
class AspectoSerializer(serializers.ModelSerializer):
    resultado = serializers.IntegerField(read_only=True)
    significativo = serializers.BooleanField(read_only=True)
    lugar_texto = serializers.CharField(read_only=True)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True, default=None)
    responsable_nombre = serializers.CharField(source='responsable.nombre', read_only=True, default=None)
    obligacion_texto = serializers.SerializerMethodField()
    legal_sugerido = serializers.SerializerMethodField()
    alcance_display = serializers.CharField(source='get_alcance_display', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default=None)

    class Meta:
        model = AspectoAmbiental
        fields = ['id', 'sede', 'sede_nombre', 'alcance', 'alcance_display', 'areas', 'lugar', 'lugar_texto',
                  'proceso', 'proceso_nombre',
                  'actividad', 'aspecto', 'impacto', 'situaciones', 'generacion', 'clase', 'etapa_ciclo',
                  'controles_existentes', 'legal', 'severidad', 'partes', 'escala', 'frecuencia', 'resultado',
                  'significativo', 'obligacion', 'obligacion_texto', 'legal_sugerido', 'control_operacional',
                  'registro_asociado', 'responsable', 'responsable_nombre', 'plazo', 'criterio_seguimiento', 'orden',
                  'estado', 'motivo_retiro', 'historial', 'updated_at']
        read_only_fields = ['estado', 'motivo_retiro', 'historial', 'orden']

    def get_obligacion_texto(self, obj):
        o = obj.obligacion
        if not o:
            return None
        return f'{o.documento or o.documento_legal or ""} {("· art. " + o.articulo) if o.articulo else ""}'.strip()

    def get_legal_sugerido(self, obj):
        return legal_sugerido(obj.obligacion)

    def validate_situaciones(self, v):
        validas = [s for s in (v or []) if s in dict(SITUACIONES)]
        if not validas:
            raise serializers.ValidationError('Marque al menos una situación: normal, anormal o emergencia.')
        return sorted(set(validas), key='NAE'.index)

    def validate(self, data):
        inst = self.instance

        def val(c, defecto=None):
            return data[c] if c in data else (getattr(inst, c) if inst else defecto)
        if inst and inst.estado == 'retirado':
            raise serializers.ValidationError({'detail': 'El aspecto está retirado: no se modifica.'})
        errores = {}
        for c in ('actividad', 'aspecto', 'impacto'):
            if c in data and not (data[c] or '').strip():
                errores[c] = ['Este dato es obligatorio.']
        alcance = val('alcance', 'areas')
        if alcance == 'areas' and not (data['areas'] if 'areas' in data else (list(inst.areas.all()) if inst else [])):
            errores['areas'] = ['Elija al menos un área o laboratorio.']
        if alcance == 'otro' and not (val('lugar', '') or '').strip():
            errores['lugar'] = ['Describa el lugar.']
        clase = val('clase', 'negativo')
        if clase == 'positivo':
            # Los aspectos positivos se identifican pero no se evalúan (procedimiento 6.2.3).
            for c in CAMPOS_CRITERIO:
                data[c] = None
        else:
            for c in CAMPOS_CRITERIO:
                v = val(c)
                if v not in (1, 2, 3):
                    errores[c] = ['Valore de 1 a 3.']
        if not errores and clase == 'negativo':
            valores = [val(c) for c in CAMPOS_CRITERIO]
            significativo = sum(valores) >= 10 or val('legal') == 3
            if significativo:
                if not (val('control_operacional', '') or '').strip():
                    errores['control_operacional'] = ['Un aspecto significativo necesita su control operacional.']
                if not val('responsable'):
                    errores['responsable'] = ['Un aspecto significativo necesita responsable.']
                if not val('plazo'):
                    errores['plazo'] = ['Un aspecto significativo necesita plazo de implementación.']
        if errores:
            raise serializers.ValidationError(errores)
        sede = validar_sede(self, data, obligatoria=False)
        if alcance == 'areas':
            areas = data['areas'] if 'areas' in data else list(inst.areas.all())
            fuera = [a.nombre for a in areas if sede and a.sede_id and a.sede_id != sede.pk]
            if fuera:
                raise serializers.ValidationError({'areas': [f'No están en {sede.nombre}: {", ".join(fuera)}.']})
        else:
            data['areas'] = []
        return data


class AspectoViewSet(_Base, viewsets.ModelViewSet):
    serializer_class = AspectoSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        p = self.request.query_params
        qs = AspectoAmbiental.objects.select_related('proceso', 'responsable', 'obligacion__requisito', 'sede') \
            .prefetch_related('areas')
        if self.action == 'list' and p.get('estado') != 'todos':
            qs = qs.filter(estado=p.get('estado') or 'vigente')
        if str(p.get('sede') or '').isdigit():
            # Lo que aplica en la sede: lo suyo, lo de sus áreas y lo que no se limita a una sede.
            qs = qs.filter(Q(sede_id=p['sede']) | Q(areas__sede_id=p['sede'])
                           | Q(sede__isnull=True, alcance__in=['empresa', 'laboratorios', 'oficinas', 'otro']))
        if p.get('area'):
            v = str(p['area'])
            if v.isdigit():
                # Lo que aplica a esa área: lo suyo, lo de toda la empresa y lo de su grupo (laboratorios u oficinas).
                from organizacion.models import Area
                ar = Area.objects.filter(pk=v).first()
                cond = Q(areas=v) | Q(alcance='empresa')
                if ar is not None:
                    cond |= Q(alcance='laboratorios') if ar.tipo == 'laboratorio' else Q(alcance='oficinas')
                qs = qs.filter(cond)
            else:
                qs = qs.filter(alcance=v)
        if p.get('proceso') and str(p['proceso']).isdigit():
            qs = qs.filter(proceso=p['proceso'])
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(aspecto__icontains=b) | Q(impacto__icontains=b) | Q(actividad__icontains=b))
        return qs.distinct()

    def list(self, request, *args, **kwargs):
        lista = list(self.get_queryset())
        if request.query_params.get('significativo') == '1':
            lista = [a for a in lista if a.significativo]
        return Response(self.get_serializer(lista, many=True).data)

    def perform_create(self, serializer):
        orden = (AspectoAmbiental.objects.order_by('-orden').values_list('orden', flat=True).first() or 0) + 1
        a = serializer.save(created_by=self.request.user, updated_by=self.request.user, orden=orden)
        _hist(a, self.request, 'Registro')
        a.save(update_fields=['historial'])

    def perform_update(self, serializer):
        antes = {c: getattr(serializer.instance, c) for c in serializer.validated_data if c != 'areas'}
        a = serializer.save(updated_by=self.request.user)
        cambios = [AspectoAmbiental._meta.get_field(c).verbose_name for c, v in antes.items() if getattr(a, c) != v]
        if 'areas' in serializer.validated_data:
            cambios.append('Lugar')
        if cambios:
            _hist(a, self.request, 'Modificación', campos=', '.join(cambios))
            a.save(update_fields=['historial'])

    @action(detail=True, methods=['post'])
    def retirar(self, request, pk=None):
        """El aspecto deja de aplicar (queda como registro). Body: {motivo}"""
        a = self.get_object()
        if a.estado == 'retirado':
            return self._error('El aspecto ya está retirado.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo del retiro (p. ej. la actividad ya no se realiza).')
        a.estado, a.motivo_retiro, a.updated_by = 'retirado', motivo, request.user
        _hist(a, request, 'Retiro', motivo=motivo)
        a.save()
        return Response(self.get_serializer(a).data)
    retirar.operacion = 'eliminar'

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'alcances': ALCANCES, 'situaciones': SITUACIONES, 'generacion': GENERACION,
                         'clases': CLASES, 'etapas': ETAPAS_CICLO, 'criterios': CRITERIOS,
                         'valoracion': {k: {str(n): t for n, t in v.items()} for k, v in VALORACION.items()}})
    catalogos.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def obligaciones(self, request):
        """Obligaciones ambientales vigentes de Requisitos legales, para vincular al aspecto."""
        from legal.models import Obligacion
        qs = Obligacion.objects.filter(is_active=True, estado='vigente', ambito='ma').select_related('requisito')
        return Response([{'id': o.pk, 'texto': f'{o.documento or o.documento_legal or ""}'
                          f'{(" · art. " + o.articulo) if o.articulo else ""} — {o.extracto[:120]}',
                          'legal_sugerido': legal_sugerido(o)} for o in qs])
    obligaciones.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        vigentes = list(AspectoAmbiental.objects.filter(estado='vigente'))
        est, ap = estado_aprobacion_matriz()
        sig = [a for a in vigentes if a.significativo]
        return Response({
            'total': len(vigentes), 'significativos': len(sig),
            'positivos': len([a for a in vigentes if a.clase == 'positivo']),
            'por_incumplimiento': len([a for a in sig if a.legal == 3]),
            'sin_responsable': len([a for a in vigentes if not a.responsable_id]),
            'vencidos': len([a for a in sig if a.plazo and a.plazo < timezone.localdate()]),
            'aprobacion': {'estado': est, 'fecha': ap.fecha if ap else None,
                           'cambios': AspectoAmbiental.objects.filter(updated_at__gt=ap.created_at).count()
                           if ap else None}})
    resumen.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def aprobaciones(self, request):
        from sst.comite_firmas import titulares_para_firmar
        c, titulares = titulares_para_firmar()
        historial = [{'id': a.pk, 'fecha': a.fecha, 'firmas': a.firmas, 'aspectos': a.aspectos,
                      'reunion': a.reunion.codigo if a.reunion_id else None, 'observaciones': a.observaciones,
                      'archivo_url': _url(a.archivo), 'registro': a.registro}
                     for a in AprobacionMatrizAmbiental.objects.select_related('reunion')[:30]]
        est, _ = estado_aprobacion_matriz()
        return Response({'estado': est, 'comite': c.periodo if c else None, 'titulares': titulares,
                         'quorum': len(titulares), 'historial': historial})
    aprobaciones.operacion = 'leer'

    @action(detail=False, methods=['post'])
    def aprobar(self, request):
        """Aprobación de la matriz por todos los titulares del Comité de SST. En pantalla (JSON): {fecha, reunion?,
        observaciones, firmas: [{miembro, clave | pin | pin_nuevo + pin_confirmacion}]}. En papel (multipart):
        {fecha, firmantes, archivo, password}."""
        from sst.comite_firmas import firmas_del_comite
        vigentes = AspectoAmbiental.objects.filter(estado='vigente').count()
        if not vigentes:
            return self._error('La matriz no tiene aspectos vigentes.')
        fecha = parse_date(str(request.data.get('fecha') or '')[:10]) or timezone.localdate()
        with transaction.atomic():
            datos, error = firmas_del_comite(request, fecha)
            if error:
                transaction.set_rollback(True)
                return error
            AprobacionMatrizAmbiental.objects.create(
                fecha=fecha, reunion=datos['reunion'], firmas=datos['firmas'],
                archivo=request.FILES.get('archivo') if datos['papel'] else None,
                observaciones=(request.data.get('observaciones') or '').strip(), registro=_firma(request),
                aspectos=vigentes, created_by=request.user, updated_by=request.user)
        return self.aprobaciones(request)
    aprobar.operacion = 'aprobar'

    @action(detail=False, methods=['get'])
    def pdf(self, request):
        from .pdf import generar_matriz_pdf
        qs = list(AspectoAmbiental.objects.filter(estado='vigente').select_related('proceso', 'responsable')
                  .prefetch_related('areas'))
        est, ap = estado_aprobacion_matriz()
        return self._pdf(generar_matriz_pdf(qs, ap, est), 'Matriz de aspectos e impactos ambientales')
    pdf.operacion = 'leer'


# ============================================================================================== consumos
class ConsumoSerializer(serializers.ModelSerializer):
    """Consumo de un suministro en un mes. Por lectura del medidor, el consumo es la diferencia con la lectura del
    registro anterior (o con la lectura inicial si es el primero o si se cambió el medidor); por recibo, dato del
    arrendador o estimación, se escribe el consumo."""
    unidad = serializers.CharField(read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    origen_display = serializers.CharField(source='get_origen_display', read_only=True)
    suministro_nombre = serializers.CharField(source='suministro.nombre', read_only=True, default=None)
    sede = serializers.IntegerField(source='suministro.sede_id', read_only=True, default=None)
    sede_nombre = serializers.CharField(source='suministro.sede.nombre', read_only=True, default=None)
    nivel_nombre = serializers.CharField(source='suministro.nivel.nombre', read_only=True, default=None)
    evidencia_url = serializers.SerializerMethodField()
    consumo_diario = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    aviso = serializers.CharField(read_only=True)
    consumo = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    tipo = serializers.CharField(required=False)

    class Meta:
        model = ConsumoMensual
        fields = ['id', 'suministro', 'suministro_nombre', 'sede', 'sede_nombre', 'nivel_nombre', 'tipo',
                  'tipo_display', 'anio', 'mes', 'origen', 'origen_display', 'fecha_lectura', 'lectura_anterior',
                  'lectura_actual', 'cambio_medidor', 'motivo_cambio', 'consumo', 'unidad', 'monto', 'evidencia',
                  'evidencia_url', 'observaciones', 'consumo_diario', 'aviso']
        extra_kwargs = {'evidencia': {'write_only': True, 'required': False}}

    def get_evidencia_url(self, obj):
        return _url(obj.evidencia)

    def validate(self, data):
        inst = self.instance

        def val(c, defecto=None):
            return data[c] if c in data else getattr(inst, c, defecto) if inst else defecto
        sumi = val('suministro')
        if inst and 'suministro' in data and data['suministro'] != inst.suministro and inst.suministro_id:
            raise serializers.ValidationError({'suministro': ['Un consumo no cambia de suministro: anúlelo y '
                                                               'regístrelo en el correcto.']})
        if not sumi and not inst:
            raise serializers.ValidationError({'suministro': ['Elija el suministro (Organización y personal › Sedes).']})
        if sumi and not inst and not sumi.is_active:
            raise serializers.ValidationError({'suministro': ['El suministro está desactivado.']})
        if sumi:
            data['tipo'] = sumi.tipo
        elif not val('tipo'):
            raise serializers.ValidationError({'tipo': ['Indique el servicio.']})
        anio, mes = val('anio'), val('mes')
        if not mes or not 1 <= int(mes) <= 12:
            raise serializers.ValidationError({'mes': ['Mes no válido.']})
        hoy = timezone.localdate()
        if anio and (int(anio), int(mes)) > (hoy.year, hoy.month):
            raise serializers.ValidationError({'mes': ['No se registra el consumo de un mes futuro.']})
        if val('fecha_lectura') and val('fecha_lectura') > hoy:
            raise serializers.ValidationError({'fecha_lectura': ['La fecha de la lectura no puede ser futura.']})
        filtro = {'suministro': sumi} if sumi else {'suministro__isnull': True, 'tipo': val('tipo')}
        if ConsumoMensual.objects.filter(is_active=True, anio=anio, mes=mes, **filtro) \
                .exclude(pk=getattr(inst, 'pk', None)).exists():
            raise serializers.ValidationError({'mes': ['Ese suministro ya tiene el consumo de ese mes: corríjalo en '
                                                       'lugar de registrar otro.']})
        origen = val('origen') or ('lectura' if sumi and sumi.modalidad == 'lectura' else 'recibo')
        data['origen'] = origen
        if origen == 'lectura':
            self._por_lectura(data, val, sumi, anio, mes)
        else:
            consumo = val('consumo')
            if consumo is None:
                raise serializers.ValidationError({'consumo': ['Indique el consumo del mes.']})
            if consumo < 0:
                raise serializers.ValidationError({'consumo': ['El consumo no puede ser negativo.']})
            data.update(lectura_anterior=None, lectura_actual=None, cambio_medidor=False, motivo_cambio='')
        return data

    def _por_lectura(self, data, val, sumi, anio, mes):
        if not sumi:
            raise serializers.ValidationError({'origen': ['La lectura se registra sobre un suministro.']})
        actual = val('lectura_actual')
        if actual is None:
            raise serializers.ValidationError({'lectura_actual': ['Indique la lectura del medidor.']})
        if actual < 0:
            raise serializers.ValidationError({'lectura_actual': ['La lectura no puede ser negativa.']})
        ref = ConsumoMensual(pk=getattr(self.instance, 'pk', None), suministro=sumi, anio=int(anio), mes=int(mes))
        previo, sig = ref.anterior(), ref.siguiente()
        cambio = bool(val('cambio_medidor'))
        if cambio:
            if not (val('motivo_cambio') or '').strip():
                raise serializers.ValidationError({'motivo_cambio': ['Indique el motivo del cambio o reinicio del '
                                                                     'medidor.']})
            anterior = val('lectura_anterior')
            if anterior is None:
                raise serializers.ValidationError({'lectura_anterior': ['Indique la lectura inicial del medidor nuevo.']})
        elif previo and previo.lectura_actual is not None:
            anterior = previo.lectura_actual
        else:
            anterior = val('lectura_anterior')
            if anterior is None:
                raise serializers.ValidationError({'lectura_anterior': [
                    'Es la primera lectura de este suministro: indique también la lectura del mes anterior.']})
        if actual < anterior:
            raise serializers.ValidationError({'lectura_actual': [
                f'La lectura ({actual}) es menor que la anterior ({anterior}). Si se cambió o reinició el medidor, '
                'márquelo e indique la lectura inicial del medidor nuevo.']})
        if sig and sig.origen == 'lectura' and not sig.cambio_medidor and sig.lectura_actual is not None \
                and sig.lectura_actual < actual:
            raise serializers.ValidationError({'lectura_actual': [
                f'La lectura ({actual}) es mayor que la del mes siguiente ya registrado ({sig.lectura_actual}, '
                f'{MESES[sig.mes - 1].lower()} {sig.anio}): revise ambas.']})
        fl, fa = val('fecha_lectura'), previo.fecha_lectura if previo else None
        if fl and fa and fl <= fa and not cambio:
            raise serializers.ValidationError({'fecha_lectura': ['La fecha es anterior a la de la lectura previa.']})
        data.update(lectura_anterior=anterior, lectura_actual=actual, consumo=actual - anterior)
        if not cambio:
            data['motivo_cambio'] = ''


def recalcular_siguiente(c, usuario):
    """Si el registro del mes siguiente (por lectura, sin cambio de medidor) tomaba su lectura anterior de este,
    actualiza su lectura anterior y su consumo."""
    sig = c.siguiente() if c.suministro_id else None
    if not sig or sig.origen != 'lectura' or sig.cambio_medidor:
        return
    previo = sig.anterior()
    if not previo or previo.lectura_actual is None:
        return
    if sig.lectura_anterior != previo.lectura_actual:
        sig.lectura_anterior = previo.lectura_actual
        sig.consumo = sig.lectura_actual - sig.lectura_anterior
        sig.updated_by = usuario
        sig.save(update_fields=['lectura_anterior', 'consumo', 'updated_by', 'updated_at'])


def trabajadores_en_mes(anio, mes, sede=None):
    """Personal propio activo en algún día del mes; de una sede si se indica (por el área del trabajador o de su
    puesto)."""
    import calendar
    from datetime import date

    from organizacion.models import Trabajador, q_trabajadores_de_sede
    inicio, fin = date(anio, mes, 1), date(anio, mes, calendar.monthrange(anio, mes)[1])
    qs = Trabajador.objects.filter(is_active=True, puesto__tipo='propio').filter(
        Q(fecha_ingreso__isnull=True) | Q(fecha_ingreso__lte=fin)).filter(
        Q(fecha_cese__isnull=True) | Q(fecha_cese__gte=inicio))
    if sede:
        qs = qs.filter(q_trabajadores_de_sede(sede))
    return qs.count()


class ConsumoViewSet(_Base, viewsets.ModelViewSet):
    serializer_class = ConsumoSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        p = self.request.query_params
        qs = ConsumoMensual.objects.filter(is_active=True).select_related('suministro__sede', 'suministro__nivel')
        if p.get('anio'):
            qs = qs.filter(anio=_anio(self.request))
        if p.get('tipo'):
            qs = qs.filter(tipo=p['tipo'])
        if p.get('sede') and str(p['sede']).isdigit():
            qs = qs.filter(suministro__sede_id=p['sede'])
        if p.get('suministro') and str(p['suministro']).isdigit():
            qs = qs.filter(suministro_id=p['suministro'])
        return qs

    def perform_create(self, serializer):
        c = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        recalcular_siguiente(c, self.request.user)

    def perform_update(self, serializer):
        c = serializer.save(updated_by=self.request.user)
        recalcular_siguiente(c, self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Anula el registro (queda en la base como inactivo)."""
        c = self.get_object()
        sig = c.siguiente() if c.suministro_id else None
        if sig and sig.origen == 'lectura' and not sig.cambio_medidor:
            previo = c.anterior()
            if previo and previo.lectura_actual is not None and sig.lectura_actual < previo.lectura_actual:
                return self._error('No se puede anular: el mes siguiente quedaría con una lectura menor que la '
                                   'anterior. Corrija las lecturas primero.')
        c.is_active, c.updated_by = False, request.user
        c.save()
        previo = c.anterior()
        if sig and previo:
            # El mes siguiente pasa a tomar su lectura anterior del registro previo al anulado.
            recalcular_siguiente(previo, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def anterior(self, request):
        """Lectura anterior que tomará el registro de un suministro en un mes (para mostrarla al registrar).
        ?suministro=&anio=&mes="""
        from organizacion.models import Suministro
        p = request.query_params
        s = Suministro.objects.filter(pk=p.get('suministro') or 0).first()
        if not s or not str(p.get('anio', '')).isdigit() or not str(p.get('mes', '')).isdigit():
            return self._error('Indique suministro, año y mes.')
        ref = ConsumoMensual(pk=int(p['excluir']) if str(p.get('excluir', '')).isdigit() else None, suministro=s,
                             anio=int(p['anio']), mes=int(p['mes']))
        previo = ref.anterior()
        return Response({'modalidad': s.modalidad, 'unidad': s.unidad,
                         'lectura_anterior': previo.lectura_actual if previo else None,
                         'fecha_anterior': previo.fecha_lectura if previo else None,
                         'mes_anterior': f'{MESES[previo.mes - 1]} {previo.anio}' if previo else None})
    anterior.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def indicadores(self, request):
        """Por servicio y mes (de una sede o de toda la organización): consumo, monto, consumo por trabajador y
        variación frente al mismo mes del año anterior; además, el detalle por suministro y el total por sede."""
        from organizacion.models import Sede, Suministro
        anio = _anio(request)
        sede_id = request.query_params.get('sede')
        sede_id = int(sede_id) if str(sede_id or '').isdigit() else None
        qs = ConsumoMensual.objects.filter(is_active=True, anio__in=[anio, anio - 1]) \
            .select_related('suministro__sede', 'suministro__nivel')
        if sede_id:
            qs = qs.filter(suministro__sede_id=sede_id)
        registros = list(qs)
        suma = defaultdict(lambda: Decimal('0'))
        monto = defaultdict(lambda: Decimal('0'))
        estimado = set()
        for c in registros:
            suma[(c.tipo, c.anio, c.mes)] += c.consumo
            monto[(c.tipo, c.anio, c.mes)] += c.monto or 0
            if c.origen == 'estimado':
                estimado.add((c.tipo, c.anio, c.mes))
        sumis = list(Suministro.objects.filter(Q(is_active=True) | Q(consumos__anio=anio, consumos__is_active=True))
                     .filter(**({'sede_id': sede_id} if sede_id else {})).distinct()
                     .select_related('sede', 'nivel'))
        tipos_usados = [t for t, _ in TIPOS_CONSUMO if any(s.tipo == t for s in sumis)
                        or any(c.tipo == t for c in registros)] or ['energia', 'agua']
        trab = {m: trabajadores_en_mes(anio, m, sede_id) for m in range(1, 13)}
        salida = {}
        for tipo, nombre in TIPOS_CONSUMO:
            if tipo not in tipos_usados:
                continue
            meses, total, total_ant, total_monto = [], Decimal('0'), Decimal('0'), Decimal('0')
            esperados = len([s for s in sumis if s.tipo == tipo and s.is_active])
            for m in range(1, 13):
                k, ka = (tipo, anio, m), (tipo, anio - 1, m)
                hay = any(c.tipo == tipo and c.anio == anio and c.mes == m for c in registros)
                hay_ant = any(c.tipo == tipo and c.anio == anio - 1 and c.mes == m for c in registros)
                c, ant = (suma[k] if hay else None), (suma[ka] if hay_ant else None)
                n = len([1 for x in registros if x.tipo == tipo and x.anio == anio and x.mes == m and x.suministro_id])
                meses.append({'mes': m, 'nombre': MESES[m - 1], 'consumo': c, 'monto': monto[k] if hay else None,
                              'anterior': ant, 'registrados': n, 'esperados': esperados,
                              'estimado': k in estimado,
                              'por_trabajador': round(c / trab[m], 2) if c is not None and trab[m] else None,
                              'variacion': round((c - ant) * 100 / ant, 1) if c is not None and ant else None})
                if hay:
                    total += c
                    total_monto += monto[k]
                    if hay_ant:
                        total_ant += ant
            salida[tipo] = {'nombre': nombre, 'unidad': UNIDAD_CONSUMO[tipo], 'meses': meses, 'total': total,
                            'monto': total_monto, 'total_anterior_mismos_meses': total_ant,
                            'variacion': round((total - total_ant) * 100 / total_ant, 1) if total_ant else None}
        por_suministro = []
        for s in sumis:
            regs = {c.mes: c for c in registros if c.suministro_id == s.pk and c.anio == anio}
            por_suministro.append({
                'id': s.pk, 'nombre': s.nombre, 'tipo': s.tipo, 'unidad': s.unidad, 'sede': s.sede.nombre,
                'nivel': s.nivel.nombre if s.nivel_id else None, 'modalidad': s.modalidad, 'activo': s.is_active,
                'meses': [{'mes': m, 'id': regs[m].pk, 'consumo': regs[m].consumo, 'origen': regs[m].origen}
                          if m in regs else {'mes': m} for m in range(1, 13)],
                'total': sum((c.consumo for c in regs.values()), Decimal('0'))})
        por_sede = []
        for se in Sede.objects.filter(pk=sede_id) if sede_id else Sede.objects.filter(is_active=True):
            fila = {'sede': se.nombre, 'id': se.pk}
            for tipo in tipos_usados:
                fila[tipo] = sum((c.consumo for c in registros
                                  if c.anio == anio and c.tipo == tipo and c.suministro_id
                                  and c.suministro.sede_id == se.pk), Decimal('0'))
            por_sede.append(fila)
        sin_suministro = [c for c in registros if not c.suministro_id and c.anio == anio]
        return Response({'anio': anio, 'sede': sede_id, 'tipos': salida, 'suministros': por_suministro,
                         'por_sede': por_sede, 'sin_suministro': len(sin_suministro)})
    indicadores.operacion = 'leer'


# ============================================================================================== residuos
CATS = {c[0]: c for c in CATEGORIAS_RESIDUO}


def validar_sede(serializer, data, obligatoria):
    """La sede, si se indica, debe estar activa (salvo que ya la tuviera el registro); es obligatoria al registrar
    cuando la organización tiene sedes."""
    from organizacion.models import Sede
    inst = serializer.instance
    sede = data['sede'] if 'sede' in data else getattr(inst, 'sede', None)
    if sede is not None and not sede.is_active and sede != getattr(inst, 'sede', None):
        raise serializers.ValidationError({'sede': ['La sede está desactivada.']})
    if obligatoria and not inst and sede is None and Sede.objects.filter(is_active=True).exists():
        raise serializers.ValidationError({'sede': ['Indique la sede.']})
    return sede


class PesajeSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default=None)
    responsable_nombre = serializers.CharField(source='responsable.nombre_completo', read_only=True, default=None)
    responsable_cargo = serializers.CharField(source='responsable.puesto.nombre', read_only=True, default=None)
    totales = serializers.SerializerMethodField()
    etapas_abiertas = serializers.SerializerMethodField()

    class Meta:
        model = PesajeResiduos
        fields = ['id', 'codigo', 'sede', 'sede_nombre', 'tipo', 'tipo_display', 'fecha', 'hora', 'responsable',
                  'responsable_nombre', 'responsable_cargo', 'items', 'observaciones', 'estado', 'estado_display',
                  'firma', 'motivo_anulacion', 'historial', 'totales', 'etapas_abiertas']
        read_only_fields = ['codigo', 'estado', 'firma', 'motivo_anulacion', 'historial']

    def get_totales(self, obj):
        return obj.totales()

    def get_etapas_abiertas(self, obj):
        return ['registro'] if obj.estado == 'en_registro' else []

    def validate_fecha(self, v):
        if v > timezone.localdate():
            raise serializers.ValidationError('La fecha no puede ser futura.')
        return v

    def validate_items(self, v):
        limpio = []
        for i in v or []:
            if not isinstance(i, dict) or i.get('categoria') not in CATS:
                raise serializers.ValidationError('Cada línea indica su tipo de residuo.')
            kg, litros = _decimal(i.get('kg')), _decimal(i.get('litros'))
            cantidad = i.get('cantidad')
            if any(x is not None and x < 0 for x in (kg, litros)):
                raise serializers.ValidationError('Las cantidades no pueden ser negativas.')
            if kg is None and litros is None and not cantidad:
                continue  # línea vacía
            limpio.append({'categoria': i['categoria'], 'tipo': str(i.get('tipo') or '').strip()[:120],
                           'kg': float(kg) if kg is not None else None,
                           'litros': float(litros) if litros is not None else None,
                           'cantidad': int(cantidad) if str(cantidad or '').isdigit() else None,
                           'observaciones': str(i.get('observaciones') or '').strip()[:300]})
        return limpio

    def validate(self, data):
        if self.instance and self.instance.estado != 'en_registro':
            raise serializers.ValidationError({'detail': 'El pesaje ya fue cerrado: no se modifica.'})
        validar_sede(self, data, obligatoria=True)
        return data


class PesajeViewSet(_Base, viewsets.ModelViewSet):
    serializer_class = PesajeSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = PesajeResiduos.objects.select_related('responsable__puesto', 'sede')
        p = self.request.query_params
        if p.get('anio'):
            qs = qs.filter(fecha__year=_anio(self.request))
        if p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        if str(p.get('sede') or '').isdigit():
            qs = qs.filter(sede_id=p['sede'])
        return qs

    def perform_create(self, serializer):
        p = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(p, self.request, 'Registro')
        p.save(update_fields=['historial'])

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """Cierra el pesaje con la firma (contraseña) de quien registra. Body: {password}"""
        p = self.get_object()
        if p.estado != 'en_registro':
            return self._error('El pesaje ya está cerrado o anulado.')
        if not p.items:
            return self._error('Registre al menos un residuo pesado.')
        if not p.responsable_id:
            return self._error('Indique el responsable del pesaje.')
        error = self._clave(request, 'el pesaje')
        if error:
            return error
        p.estado, p.firma, p.updated_by = 'cerrado', _firma(request), request.user
        _hist(p, request, 'Cierre', total_kg=str(p.totales()['total_kg']))
        p.save()
        return Response(self.get_serializer(p).data)
    cerrar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        p = self.get_object()
        if p.estado == 'anulado':
            return self._error('El pesaje ya está anulado.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la anulación.')
        p.estado, p.motivo_anulacion, p.updated_by = 'anulado', motivo, request.user
        _hist(p, request, 'Anulación', motivo=motivo)
        p.save()
        return Response(self.get_serializer(p).data)
    anular.operacion = 'eliminar'

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'categorias': [{'clave': c[0], 'nombre': c[1], 'tacho': c[2], 'peligroso': c[3],
                                         'unidad': c[4], 'sugeridos': TIPOS_SUGERIDOS[c[0]]}
                                        for c in CATEGORIAS_RESIDUO],
                         'tipos': TIPOS_PESAJE, 'destinos': DESTINOS, 'grupos': GRUPOS_DISPOSICION})
    catalogos.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf import generar_pesaje_pdf
        p = self.get_object()
        return self._pdf(generar_pesaje_pdf(p), p.codigo)
    pdf.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def resumen_anual(self, request):
        """Residuos del año por mes, en kg y toneladas: generados (pesajes de ingreso cerrados) y dispuestos
        (disposiciones), peligrosos y no peligrosos — base de la declaración anual."""
        anio = _anio(request)
        sede = request.query_params.get('sede')
        por_sede = {'sede_id': sede} if str(sede or '').isdigit() else {}
        gen = defaultdict(lambda: {'no_peligroso': Decimal('0'), 'peligroso': Decimal('0'), 'litros': Decimal('0')})
        for p in PesajeResiduos.objects.filter(estado='cerrado', tipo='ingreso', fecha__year=anio, **por_sede):
            t = p.totales()
            g = gen[p.fecha.month]
            g['no_peligroso'] += t['no_peligrosos_kg']
            g['peligroso'] += t['peligrosos_kg']
            g['litros'] += t['peligrosos_litros']
        disp = defaultdict(lambda: {'no_peligroso': Decimal('0'), 'peligroso': Decimal('0')})
        for d in DisposicionResiduos.objects.filter(is_active=True, fecha__year=anio, **por_sede):
            disp[d.fecha.month]['no_peligroso' if d.grupo == 'no_peligroso' else 'peligroso'] += d.kg
        meses, tot = [], defaultdict(Decimal)
        for m in range(1, 13):
            fila = {'mes': m, 'nombre': MESES[m - 1],
                    'generado_no_peligroso_kg': gen[m]['no_peligroso'], 'generado_peligroso_kg': gen[m]['peligroso'],
                    'generado_peligroso_litros': gen[m]['litros'],
                    'dispuesto_no_peligroso_kg': disp[m]['no_peligroso'], 'dispuesto_peligroso_kg': disp[m]['peligroso']}
            for k, v in list(fila.items()):
                if k.endswith('_kg') or k.endswith('_litros'):
                    tot[k] += v
            fila['generado_no_peligroso_tm'] = round(fila['generado_no_peligroso_kg'] / 1000, 4)
            fila['generado_peligroso_tm'] = round(fila['generado_peligroso_kg'] / 1000, 4)
            meses.append(fila)
        generado = tot['generado_no_peligroso_kg'] + tot['generado_peligroso_kg']
        dispuesto = tot['dispuesto_no_peligroso_kg'] + tot['dispuesto_peligroso_kg']
        return Response({'anio': anio, 'meses': meses, 'totales': tot,
                         'generado_kg': generado, 'dispuesto_kg': dispuesto,
                         'generado_tm': round(generado / 1000, 4),
                         'porcentaje_dispuesto': round(dispuesto * 100 / generado, 1) if generado else None})
    resumen_anual.operacion = 'leer'


class DisposicionSerializer(serializers.ModelSerializer):
    grupo_display = serializers.CharField(source='get_grupo_display', read_only=True)
    destino_display = serializers.CharField(source='get_destino_display', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True, default=None)
    certificado_url = serializers.SerializerMethodField()

    class Meta:
        model = DisposicionResiduos
        fields = ['id', 'sede', 'sede_nombre', 'fecha', 'grupo', 'grupo_display', 'descripcion', 'kg', 'destino',
                  'destino_display', 'operadora', 'registro_operadora', 'manifiesto', 'certificado',
                  'certificado_url', 'observaciones']
        extra_kwargs = {'certificado': {'write_only': True, 'required': False}}

    def get_certificado_url(self, obj):
        return _url(obj.certificado)

    def validate_fecha(self, v):
        if v > timezone.localdate():
            raise serializers.ValidationError('La fecha no puede ser futura.')
        return v

    def validate_kg(self, v):
        if v is None or v <= 0:
            raise serializers.ValidationError('Indique la cantidad en kg.')
        return v

    def validate(self, data):
        destino = data.get('destino', getattr(self.instance, 'destino', None))
        grupo = data.get('grupo', getattr(self.instance, 'grupo', None))
        if grupo == 'peligroso' and destino not in ('eors', 'otro'):
            raise serializers.ValidationError({'destino': ['Los residuos peligrosos se entregan a una empresa '
                                                           'operadora autorizada (EO-RS).']})
        if destino == 'eors' and not (data.get('operadora') or getattr(self.instance, 'operadora', '')):
            raise serializers.ValidationError({'operadora': ['Indique la empresa operadora.']})
        validar_sede(self, data, obligatoria=True)
        return data


class DisposicionViewSet(_Base, viewsets.ModelViewSet):
    serializer_class = DisposicionSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = DisposicionResiduos.objects.filter(is_active=True).select_related('sede')
        if self.request.query_params.get('anio'):
            qs = qs.filter(fecha__year=_anio(self.request))
        if str(self.request.query_params.get('sede') or '').isdigit():
            qs = qs.filter(sede_id=self.request.query_params['sede'])
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        d = self.get_object()
        d.is_active, d.updated_by = False, request.user
        d.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
