"""API de trabajos y salidas no conformes: registro → tratamiento → autorización → evaluación → cierre."""
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular

from .models import (ACCIONES, ACCIONES_AFECTACION, CATEGORIAS, ESTADOS, EVENTOS_PARA_SAC, FUENTES, NATURALEZAS,
                     NIVELES, TIPOS, AdjuntoTNC, AfectacionTNC, TrabajoNoConforme, acciones_vacias)

NOMBRE_ACCION = dict(ACCIONES)
ORDEN_ESTADOS = [e for e, _ in ESTADOS]


def _nombre(u):
    return (u.get_full_name() or u.username) if u else ''


def _firma(request):
    u = request.user
    t = getattr(u, 'trabajador', None)
    return {'usuario_id': u.pk, 'nombre': t.nombre_completo if t else _nombre(u),
            'cargo': t.puesto.nombre if t else getattr(u, 'cargo', ''),
            'fecha': timezone.localtime().isoformat(timespec='seconds'), 'ip': get_client_ip(request)}


def _hist(obj, request, accion, **extra):
    obj.historial = list(obj.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                  'usuario': _nombre(request.user), 'accion': accion, **extra}]


def puede_autorizar(usuario, tnc):
    """Reanudación: naturaleza técnica → Gerente Técnico o Jefe de Laboratorio; administrativa → Gerente SIG
    (el Gerente Comercial solo gestiona la devolución del monto). Devuelve un mensaje de error o None."""
    from revision.models import sigla_de_puesto
    try:
        puesto = usuario.trabajador.puesto
    except Exception:
        puesto = None
    if not puesto:
        return 'Su usuario no está vinculado a un trabajador con puesto: no puede autorizar la reanudación.'
    sigla = sigla_de_puesto(puesto)
    if tnc.naturaleza == 'tecnica':
        if sigla == 'GT' or puesto.nombre.lower().startswith('jefe de laboratorio'):
            return None
        return 'La reanudación de un trabajo técnico la autoriza el Gerente Técnico o el Jefe de Laboratorio.'
    if sigla == 'GSIG':
        return None
    return 'La reanudación de un trabajo administrativo la autoriza el Gerente SIG.'


# ================================================================================================ serializers
class AfectacionSerializer(serializers.ModelSerializer):
    accion_display = serializers.CharField(source='get_accion_display', read_only=True)

    class Meta:
        model = AfectacionTNC
        fields = ['id', 'ot', 'certificado', 'entregado', 'afectado', 'accion', 'accion_display']


class AdjuntoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = AdjuntoTNC
        fields = ['id', 'descripcion', 'url', 'created_at']

    def get_url(self, obj):
        return obj.archivo.url if obj.archivo else None


class TncSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    naturaleza_display = serializers.CharField(source='get_naturaleza_display', read_only=True)
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    nivel_display = serializers.CharField(source='get_nivel_riesgo_display', read_only=True)
    nivel_confirmado_display = serializers.CharField(source='get_nivel_confirmado_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)
    reportado_nombre = serializers.CharField(source='reportado_por.nombre_completo', read_only=True)
    responsable_nombre = serializers.CharField(source='responsable_tratamiento.nombre_completo', read_only=True,
                                               default=None)
    queja_codigo = serializers.CharField(source='queja.codigo', read_only=True, default=None)
    hallazgo_codigo = serializers.CharField(source='hallazgo.codigo', read_only=True, default=None)
    sac_codigo = serializers.CharField(source='sac.codigo', read_only=True, default=None)
    sac_estado = serializers.CharField(source='sac.get_estado_display', read_only=True, default=None)
    etapas_abiertas = serializers.SerializerMethodField()

    class Meta:
        model = TrabajoNoConforme
        fields = ['id', 'codigo', 'tipo', 'tipo_display', 'naturaleza', 'naturaleza_display', 'categoria',
                  'categoria_display', 'area', 'area_nombre', 'reportado_por', 'reportado_nombre', 'fecha_deteccion',
                  'fecha_reporte', 'fuente', 'fuente_display', 'queja', 'queja_codigo', 'hallazgo', 'hallazgo_codigo',
                  'referencias', 'equipos', 'descripcion', 'nivel_riesgo', 'nivel_display', 'responsable_tratamiento',
                  'responsable_nombre', 'nivel_confirmado', 'nivel_confirmado_display', 'amerita_sac', 'sac',
                  'sac_codigo', 'sac_estado', 'estado', 'estado_display', 'etapas_abiertas', 'updated_at']
        read_only_fields = ['codigo', 'nivel_riesgo', 'estado', 'responsable_tratamiento']

    def get_etapas_abiertas(self, obj):
        return obj.etapas_abiertas()

    def validate(self, data):
        inst = self.instance

        def val(c):
            return data[c] if c in data else getattr(inst, c, None)
        f = val('fecha_deteccion')
        if f and f > timezone.localdate():
            raise serializers.ValidationError({'fecha_deteccion': ['La fecha de detección no puede ser futura.']})
        r = val('fecha_reporte')
        if f and r and r < f:
            raise serializers.ValidationError({'fecha_reporte': ['El reporte no puede ser anterior a la detección.']})
        if 'fuente' in data or 'queja' in data or 'hallazgo' in data:
            fuente = val('fuente')
            if fuente == 'queja' and not val('queja'):
                raise serializers.ValidationError({'queja': ['Indique la queja de origen (RQ).']})
            if fuente == 'no_conformidad' and not val('hallazgo'):
                raise serializers.ValidationError({'hallazgo': ['Indique la no conformidad de origen.']})
        return data


class TncDetalleSerializer(TncSerializer):
    afectaciones = serializers.SerializerMethodField()
    adjuntos = serializers.SerializerMethodField()
    equipos_detalle = serializers.SerializerMethodField()
    correccion_por_nombre = serializers.CharField(source='correccion_por.nombre_completo', read_only=True,
                                                  default=None)
    asignado_nombre = serializers.CharField(source='asignado_a.nombre_completo', read_only=True, default=None)
    similares = serializers.SerializerMethodField()

    class Meta(TncSerializer.Meta):
        fields = TncSerializer.Meta.fields + [
            'firma_nivel', 'acciones', 'correccion', 'correccion_por', 'correccion_por_nombre', 'correccion_fecha',
            'nota_cliente', 'periodo_desde', 'periodo_hasta', 'ultima_condicion', 'notificacion_cliente',
            'notificacion_fecha_medio', 'certificado_anulado', 'certificado_reemplazo', 'conclusion_retroactivo',
            'acepta', 'sustento_autorizacion', 'asignado_a', 'asignado_nombre', 'firma_autorizacion',
            'afecta_validez', 'incumple_sig', 'compromete_competencia', 'evaluacion', 'eventos_similares',
            'registros_similares', 'firma_evaluacion', 'evidencias', 'firma_cierre', 'motivo_anulacion',
            'historial', 'afectaciones', 'adjuntos', 'equipos_detalle', 'similares']
        read_only_fields = TncSerializer.Meta.read_only_fields + [
            'firma_nivel', 'firma_autorizacion', 'eventos_similares', 'registros_similares', 'firma_evaluacion',
            'firma_cierre', 'motivo_anulacion', 'historial']

    def get_afectaciones(self, obj):
        return AfectacionSerializer(obj.afectaciones.filter(is_active=True), many=True).data

    def get_adjuntos(self, obj):
        return AdjuntoSerializer(obj.adjuntos.filter(is_active=True), many=True).data

    def get_equipos_detalle(self, obj):
        return [{'id': e.id, 'codigo': e.codigo, 'nombre': e.nombre, 'estado': e.get_estado_display()}
                for e in obj.equipos.all()]

    def get_similares(self, obj):
        if not obj.fecha_deteccion or not obj.area_id:
            return []
        return [x.codigo for x in obj.similares()]

    def validate_acciones(self, valor):
        if not isinstance(valor, dict):
            raise serializers.ValidationError('Formato de acciones no válido.')
        base = acciones_vacias()
        for clave, v in valor.items():
            if clave not in base or not isinstance(v, dict):
                raise serializers.ValidationError(f'Acción desconocida: {clave}.')
            for k in ('aplica', 'ejecutada'):
                if v.get(k) not in (True, False, None):
                    raise serializers.ValidationError('Indique Sí, No o deje en blanco.')
            base[clave] = {'aplica': v.get('aplica'), 'ejecutada': v.get('ejecutada') if v.get('aplica') else None}
        return base


# ===================================================================================================== vistas
class TncViewSet(viewsets.ModelViewSet):
    permission_classes = [PermisoModular]
    modulo = 'trabajo_no_conforme'
    pagination_class = None
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_serializer_class(self):
        return TncSerializer if self.action == 'list' else TncDetalleSerializer

    def get_queryset(self):
        qs = TrabajoNoConforme.objects.select_related(
            'area', 'reportado_por', 'responsable_tratamiento', 'queja', 'hallazgo', 'sac', 'correccion_por',
            'asignado_a')
        p = self.request.query_params
        if self.action == 'list':
            if p.get('anulados') != '1':
                qs = qs.filter(is_active=True)
            if p.get('abiertos') == '1':
                qs = qs.exclude(estado__in=('cerrado', 'anulado'))
            for campo in ('estado', 'tipo', 'nivel_riesgo', 'area'):
                if p.get(campo):
                    qs = qs.filter(**{campo: p[campo]})
            if str(p.get('anio') or '').isdigit():
                qs = qs.filter(fecha_deteccion__year=p['anio'])
            if p.get('buscar'):
                from django.db.models import Q
                b = p['buscar']
                qs = qs.filter(Q(codigo__icontains=b) | Q(descripcion__icontains=b) | Q(referencias__icontains=b))
        return qs

    def _error(self, mensaje, **extra):
        return Response({'detail': mensaje, **extra}, status=status.HTTP_400_BAD_REQUEST)

    def _clave(self, request, que):
        pw = request.data.get('password') or ''
        if not pw:
            return self._error(f'Confirme con su contraseña para {que}.')
        if not request.user.check_password(pw):
            return self._error(f'Contraseña incorrecta. No se registró {que}.')
        return None

    def _det(self, t):
        return Response(TncDetalleSerializer(self.get_queryset().get(pk=t.pk), context={'request': self.request}).data)

    def _en(self, t, estado, que):
        if not t.is_active or t.estado != estado:
            return self._error(f'{que} en la etapa «{dict(ESTADOS)[estado].lower()}» (el registro está '
                               f'«{t.get_estado_display().lower()}»).')
        return None

    def perform_create(self, serializer):
        t = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        _hist(t, self.request, 'Registro')
        t.save(update_fields=['historial'])

    def create(self, request, *args, **kwargs):
        otros = [c for c in request.data.keys() if TrabajoNoConforme.etapa_de_campo(c) not in (None, 'registro')]
        if otros:
            return self._error('Al registrar solo se capturan los datos del registro; las demás etapas aún no se '
                               'abren.')
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        self.perform_create(s)
        return Response(TncDetalleSerializer(s.instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Solo se modifican los campos de la etapa abierta (ADR-0005)."""
        t = self.get_object()
        if not t.is_active:
            return self._error('El registro está anulado.')
        abiertas = t.etapas_abiertas()
        for campo in request.data.keys():
            etapa = TrabajoNoConforme.etapa_de_campo(campo)
            if etapa and etapa not in abiertas:
                nombre = TrabajoNoConforme._meta.get_field(campo).verbose_name
                inicio = next(est[0] for n, est, _ in TrabajoNoConforme.ETAPAS if n == etapa)
                situacion = 'aún no se abre' if ORDEN_ESTADOS.index(inicio) > ORDEN_ESTADOS.index(t.estado) \
                    else 'está cerrada'
                return self._error(f'La etapa de {TrabajoNoConforme.NOMBRES_ETAPA[etapa]} {situacion}: no se '
                                   f'modifica «{nombre}».')
        antes = t.accion('fuera_servicio').get('ejecutada')
        kwargs['partial'] = True
        super().update(request, *args, **kwargs)
        t.refresh_from_db()
        if not antes and t.accion('fuera_servicio').get('ejecutada'):
            self._fuera_de_servicio(t)
        return self._det(t)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def _fuera_de_servicio(self, t):
        """La acción «Equipo fuera de servicio» ejecutada deja los equipos vinculados como inoperativos."""
        codigos = []
        for e in t.equipos.exclude(estado__in=('inoperativo', 'baja')):
            e.estado, e.updated_by = 'inoperativo', self.request.user
            e.save(update_fields=['estado', 'updated_by', 'updated_at'])
            codigos.append(e.codigo)
        if codigos:
            _hist(t, self.request, 'Equipos fuera de servicio', equipos=', '.join(codigos))
            t.save(update_fields=['historial'])

    # ---------------------------------------------------------------------------------------- registro
    @action(detail=True, methods=['post'])
    def iniciar_tratamiento(self, request, pk=None):
        """El Gerente Técnico o el Gerente SIG asigna el nivel de riesgo (Tabla N° 2) y el responsable del
        tratamiento. Body: {nivel_riesgo, responsable_tratamiento, password}"""
        from organizacion.models import Trabajador
        t = self.get_object()
        error = self._en(t, 'registrado', 'El tratamiento se inicia')
        if error:
            return error
        nivel = request.data.get('nivel_riesgo')
        if nivel not in dict(NIVELES):
            return self._error('Asigne el nivel de riesgo (Alto, Medio o Bajo) según la Tabla N° 2.')
        resp = Trabajador.objects.filter(pk=request.data.get('responsable_tratamiento'), is_active=True,
                                         estado='activo').first()
        if not resp:
            return self._error('Designe al responsable del tratamiento.')
        error = self._clave(request, 'la asignación del nivel de riesgo')
        if error:
            return error
        t.nivel_riesgo, t.responsable_tratamiento, t.firma_nivel = nivel, resp, _firma(request)
        t.estado, t.updated_by = 'tratamiento', request.user
        if t.acciones is None or not t.acciones:
            t.acciones = acciones_vacias()
        _hist(t, request, 'Inicio del tratamiento', nivel=dict(NIVELES)[nivel], responsable=resp.nombre_completo)
        t.save()
        return self._det(t)
    iniciar_tratamiento.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        t = self.get_object()
        if not t.is_active or t.estado not in ('registrado', 'tratamiento'):
            return self._error('Se anula solo un registro hecho por error, antes de la autorización.')
        motivo = str(request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la anulación.')
        t.estado, t.is_active, t.motivo_anulacion, t.updated_by = 'anulado', False, motivo, request.user
        _hist(t, request, 'Anulación', motivo=motivo)
        t.save()
        return Response(TncSerializer(t).data)
    anular.operacion = 'eliminar'

    # -------------------------------------------------------------------------------------- tratamiento
    @action(detail=True, methods=['post'])
    def afectacion(self, request, pk=None):
        """Agrega o corrige una fila del análisis retroactivo. Body: {id?, ot, certificado, entregado, afectado,
        accion}"""
        t = self.get_object()
        error = self._en(t, 'tratamiento', 'El análisis de impacto retroactivo se registra')
        if error:
            return error
        d = request.data
        f = t.afectaciones.filter(pk=d.get('id'), is_active=True).first() if d.get('id') else \
            AfectacionTNC(tnc=t, created_by=request.user)
        if not f:
            return self._error('Fila no encontrada.')
        f.ot, f.certificado = str(d.get('ot') or '').strip()[:40], str(d.get('certificado') or '').strip()[:60]
        if not (f.ot or f.certificado):
            return self._error('Indique la OT o el certificado.')
        f.entregado = d.get('entregado') in (True, 'true', '1', 1)
        f.afectado = d.get('afectado') in (True, 'true', '1', 1)
        f.accion = d.get('accion') if d.get('accion') in dict(ACCIONES_AFECTACION) else 'ninguna'
        f.updated_by = request.user
        f.save()
        return self._det(t)
    afectacion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_afectacion(self, request, pk=None):
        t = self.get_object()
        error = self._en(t, 'tratamiento', 'El análisis de impacto retroactivo se modifica')
        if error:
            return error
        f = t.afectaciones.filter(pk=request.data.get('id'), is_active=True).first()
        if not f:
            return self._error('Fila no encontrada.')
        f.is_active, f.updated_by = False, request.user
        f.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return self._det(t)
    quitar_afectacion.operacion = 'editar'

    def faltantes_tratamiento(self, t):
        falta = []
        if not (t.correccion or '').strip() or not t.correccion_por_id or not t.correccion_fecha:
            falta.append('la corrección con quien la realizó y su fecha')
        acc = t.acciones or {}
        sin_decidir = [NOMBRE_ACCION[c] for c, _ in ACCIONES if (acc.get(c) or {}).get('aplica') is None]
        if sin_decidir:
            falta.append(f'decidir si aplica: {", ".join(sin_decidir).lower()}')
        sin_ejecutar = [NOMBRE_ACCION[c] for c, _ in ACCIONES if (acc.get(c) or {}).get('aplica')
                        and not (acc.get(c) or {}).get('ejecutada')]
        if sin_ejecutar:
            falta.append(f'ejecutar: {", ".join(sin_ejecutar).lower()}')
        if t.nivel_riesgo == 'alto':
            obligatorias = ['detencion', 'retroactivo']
            if t.categoria == 'equipo' and t.equipos.exists():
                obligatorias.append('fuera_servicio')
            no = [NOMBRE_ACCION[c] for c in obligatorias if not (acc.get(c) or {}).get('aplica')]
            if no:
                falta.append(f'en nivel Alto aplican: {", ".join(no).lower()}')
        filas = list(t.afectaciones.filter(is_active=True))
        if (acc.get('retroactivo') or {}).get('aplica'):
            if not (t.periodo_desde and t.periodo_hasta):
                falta.append('el periodo revisado del análisis retroactivo')
            if not filas:
                falta.append('al menos una OT o certificado revisado')
            if not (t.conclusion_retroactivo or '').strip():
                falta.append('la conclusión del análisis retroactivo')
        if any(f.entregado and f.afectado for f in filas):
            if not (acc.get('notificacion') or {}).get('aplica') or not (t.notificacion_cliente or '').strip():
                falta.append('la notificación al cliente (hay certificados entregados afectados)')
        return falta

    @action(detail=True, methods=['post'])
    def pasar_autorizacion(self, request, pk=None):
        t = self.get_object()
        error = self._en(t, 'tratamiento', 'Se pasa a autorización')
        if error:
            return error
        falta = self.faltantes_tratamiento(t)
        if falta:
            return self._error('Para pasar a la autorización falta: ' + '; '.join(falta) + '.')
        t.estado, t.updated_by = 'autorizacion', request.user
        _hist(t, request, 'Tratamiento concluido')
        t.save()
        return self._det(t)
    pasar_autorizacion.operacion = 'editar'

    # ------------------------------------------------------------------------------------- autorización
    @action(detail=True, methods=['post'])
    def autorizar(self, request, pk=None):
        """¿Acepta el TNC/SNC corregido como conforme? Body: {acepta, sustento, asignado_a?, password}. Si no se
        acepta, vuelve al tratamiento."""
        from organizacion.models import Trabajador
        t = self.get_object()
        error = self._en(t, 'autorizacion', 'Se autoriza la reanudación')
        if error:
            return error
        acepta = request.data.get('acepta')
        if acepta not in (True, False, 'true', 'false'):
            return self._error('Indique si acepta el TNC o SNC corregido como conforme.')
        acepta = acepta in (True, 'true')
        sustento = str(request.data.get('sustento') or '').strip()
        if not sustento:
            return self._error('Sustente su decisión.')
        error = puede_autorizar(request.user, t)
        if error:
            return self._error(error)
        error = self._clave(request, 'la autorización')
        if error:
            return error
        asignado = Trabajador.objects.filter(pk=request.data.get('asignado_a')).first() \
            if request.data.get('asignado_a') else None
        firma = _firma(request)
        if not acepta:
            t.estado, t.updated_by = 'tratamiento', request.user
            _hist(t, request, 'No aceptado: vuelve al tratamiento', sustento=sustento, firma=firma['nombre'])
            t.save()
            return self._det(t)
        t.acepta, t.sustento_autorizacion, t.asignado_a, t.firma_autorizacion = True, sustento, asignado, firma
        # Eventos similares al pasar a la evaluación de la importancia (Área SIG).
        sim = list(t.similares())
        t.eventos_similares, t.registros_similares = len(sim), [x.codigo for x in sim]
        t.estado, t.updated_by = 'evaluacion', request.user
        _hist(t, request, 'Reanudación autorizada', firma=firma['nombre'])
        t.save()
        return self._det(t)
    autorizar.operacion = 'editar'

    # --------------------------------------------------------------------------------------- evaluación
    @action(detail=True, methods=['post'])
    def evaluar(self, request, pk=None):
        """Firma la evaluación de la importancia (Área SIG). Body: {password}"""
        t = self.get_object()
        error = self._en(t, 'evaluacion', 'Se registra la evaluación')
        if error:
            return error
        falta = []
        for c in ('afecta_validez', 'incumple_sig', 'compromete_competencia'):
            if getattr(t, c) is None:
                falta.append(f'«{TrabajoNoConforme._meta.get_field(c).verbose_name}»')
        if not t.nivel_confirmado:
            falta.append('el nivel de riesgo confirmado')
        if not (t.evaluacion or '').strip():
            falta.append('el análisis de la evaluación')
        if t.amerita_sac is None:
            falta.append('si amerita una solicitud de acción correctiva')
        if falta:
            return self._error('Para registrar la evaluación falta: ' + ', '.join(falta) + '.')
        sim = list(t.similares())
        t.eventos_similares, t.registros_similares = len(sim), [x.codigo for x in sim]
        if t.sac_obligatoria() and not t.amerita_sac:
            motivo = 'el nivel confirmado es Alto' if (t.nivel_confirmado == 'alto') else \
                f'hay {t.eventos_similares} eventos similares en 12 meses (desde {EVENTOS_PARA_SAC})'
            return self._error(f'Amerita una solicitud de acción correctiva: {motivo}.')
        error = self._clave(request, 'la evaluación')
        if error:
            return error
        t.firma_evaluacion, t.estado, t.updated_by = _firma(request), 'cierre', request.user
        _hist(t, request, 'Evaluación de la importancia', nivel=t.get_nivel_confirmado_display(),
              amerita_sac='Sí' if t.amerita_sac else 'No', similares=t.eventos_similares)
        t.save()
        return self._det(t)
    evaluar.operacion = 'aprobar'

    # -------------------------------------------------------------------------------------------- cierre
    @action(detail=True, methods=['post'])
    def crear_sac(self, request, pk=None):
        """Crea la solicitud de acción correctiva del TNC/SNC y la vincula."""
        from esynapse_sig.models import SolicitudAC
        t = self.get_object()
        error = self._en(t, 'cierre', 'La solicitud de acción correctiva se crea')
        if error:
            return error
        if not t.amerita_sac:
            return self._error('La evaluación indica que no amerita una acción correctiva.')
        if t.sac_id:
            return self._error(f'Ya está vinculada la {t.sac.codigo}.')
        with transaction.atomic():
            s = SolicitudAC.objects.create(
                fuente='otros', fuente_detalle=f'Trabajo o salida no conforme {t.codigo}',
                descripcion_nc=t.descripcion, fecha_registro=timezone.localdate(),
                created_by=request.user, updated_by=request.user)
            t.sac, t.updated_by = s, request.user
            _hist(t, request, 'Solicitud de acción correctiva creada', sac=s.codigo)
            t.save()
        return self._det(t)
    crear_sac.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def adjuntar(self, request, pk=None):
        t = self.get_object()
        if not t.is_active or t.estado in ('cerrado', 'anulado'):
            return self._error('El registro está cerrado: no se adjuntan evidencias.')
        f = request.FILES.get('archivo')
        if not f:
            return self._error('Elija el archivo.')
        AdjuntoTNC.objects.create(tnc=t, archivo=f, descripcion=str(request.data.get('descripcion') or '')[:200],
                                  created_by=request.user, updated_by=request.user)
        return self._det(t)
    adjuntar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """Cierre (Área SIG): verifica la SAC si amerita y las evidencias. Body: {password}"""
        t = self.get_object()
        error = self._en(t, 'cierre', 'Se cierra')
        if error:
            return error
        falta = []
        if t.amerita_sac and not t.sac_id:
            falta.append('vincular o crear la solicitud de acción correctiva')
        if not (t.evidencias or '').strip() and not t.adjuntos.filter(is_active=True).exists():
            falta.append('las evidencias archivadas')
        if falta:
            return self._error('Para cerrar falta: ' + '; '.join(falta) + '.')
        error = self._clave(request, 'el cierre')
        if error:
            return error
        t.firma_cierre, t.estado, t.updated_by = _firma(request), 'cerrado', request.user
        _hist(t, request, 'Cierre del registro')
        t.save()
        return self._det(t)
    cerrar.operacion = 'aprobar'

    # ---------------------------------------------------------------------------------------- catálogos
    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({'tipos': TIPOS, 'naturalezas': NATURALEZAS, 'categorias': CATEGORIAS, 'fuentes': FUENTES,
                         'niveles': NIVELES, 'acciones': ACCIONES, 'acciones_afectacion': ACCIONES_AFECTACION,
                         'estados': ESTADOS})
    catalogos.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def opciones(self, request):
        """Quejas, no conformidades, equipos y solicitudes de acción correctiva para vincular."""
        from esynapse_sig.models import Equipo, Hallazgo, SolicitudAC
        from quejas.models import Queja
        return Response({
            'quejas': [{'id': q.id, 'codigo': q.codigo, 'texto': (q.descripcion or '')[:80]}
                       for q in Queja.objects.filter(is_active=True).order_by('-id')[:300]],
            'hallazgos': [{'id': h.id, 'codigo': h.codigo, 'texto': (h.descripcion or '')[:80]}
                          for h in Hallazgo.objects.filter(is_active=True, tipo__in=('nc_mayor', 'nc_menor'))
                          .order_by('-id')[:300]],
            'equipos': [{'id': e.id, 'codigo': e.codigo, 'nombre': e.nombre}
                        for e in Equipo.objects.filter(is_active=True).exclude(estado='baja').order_by('codigo')],
            'sacs': [{'id': s.id, 'codigo': s.codigo, 'texto': (s.descripcion_nc or '')[:80]}
                     for s in SolicitudAC.objects.filter(is_active=True).order_by('-id')[:300]],
        })
    opciones.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf import generar_registro_pdf
        t = self.get_object()
        resp = HttpResponse(generar_registro_pdf(t), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="Registro {t.codigo}.pdf"'
        return resp
    pdf.operacion = 'leer'
