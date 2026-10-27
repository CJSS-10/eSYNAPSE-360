from datetime import timedelta

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular

from .models import (CATEGORIAS, DECISIONES_CARTERA, DECISIONES_MEJORA, EFICACIAS_MEJORA, ESTADOS_ACCION, ESTRATEGIAS,
                     FUENTES, FUENTES_MEJORA, NIVELES, TIPOS_CONTEXTO, AccionRiesgo, ElementoContexto,
                     OportunidadMejora, RevisionMatriz, RiesgoOportunidad)
from .serializers import (ElementoContextoSerializer, OportunidadMejoraSerializer, RevisionSerializer,
                          RiesgoListaSerializer, RiesgoSerializer)

DIAS_EFICACIA = 90          # la eficacia se verifica tras tres meses de operación de la acción


def _vacio(texto):
    return not (texto or '').strip()


def _entero(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _nombre(u):
    return u.get_full_name() or u.username


def _firma(request):
    u = request.user
    return {'usuario_id': u.pk, 'nombre': _nombre(u), 'cargo': getattr(u, 'cargo', ''),
            'sigla': getattr(u, 'sigla_cargo', ''), 'fecha': timezone.localtime().isoformat(timespec='seconds'),
            'ip': get_client_ip(request)}


class _Base:
    permission_classes = [PermisoModular]
    modulo = 'riesgos'

    def _error(self, mensaje, codigo=status.HTTP_400_BAD_REQUEST):
        return Response({'detail': mensaje}, status=codigo)

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

    def _crear_hallazgo(self, request, proceso, descripcion, fuente, fecha=None):
        from esynapse_sig.models import Hallazgo
        return Hallazgo.objects.create(
            tipo='nc_menor', fuente=fuente, proceso=proceso.nombre if proceso else 'Sistema Integrado de Gestión',
            descripcion=descripcion, fecha_deteccion=fecha or timezone.localdate(),
            created_by=request.user, updated_by=request.user)


class ContextoViewSet(_Base, viewsets.ModelViewSet):
    """Análisis de contexto: FODA y partes interesadas."""
    queryset = ElementoContexto.objects.all()
    serializer_class = ElementoContextoSerializer
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('todos') != '1':
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        tipo = serializer.validated_data['tipo']
        serializer.save(codigo=ElementoContexto.siguiente_codigo(tipo), created_by=self.request.user,
                        updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        if 'tipo' in request.data and request.data['tipo'] != self.get_object().tipo:
            return self._error('El tipo no cambia: el código depende de él. Registre un elemento nuevo.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Deja de estar vigente (no se borra)."""
        e = self.get_object()
        e.is_active = False
        e.updated_by = request.user
        e.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class RiesgoViewSet(_Base, viewsets.ModelViewSet):
    """
    M3 — Matriz de riesgos y oportunidades: registro (identificación, valoración
    inicial y tratamiento) → en la matriz (seguimiento de acciones) →
    verificación de la eficacia por valoración residual. Correcciones posteriores
    solo por revaloración con motivo.
    """
    queryset = RiesgoOportunidad.objects.all().select_related('proceso', 'hallazgo', 'verificado_por') \
        .prefetch_related('acciones', 'contexto')
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        return RiesgoListaSerializer if self.action == 'list' else RiesgoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action in ('list', 'matriz_pdf', 'indicadores'):
            qs = qs.filter(is_active=True)
            if p.get('retirados') != '1':
                qs = qs.exclude(estado='retirado')
        for campo in ('tipo', 'categoria', 'estado', 'fuente'):
            if p.get(campo):
                qs = qs.filter(**{campo: p[campo]})
        if p.get('proceso'):
            qs = qs.filter(proceso_id=p['proceso'])
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(descripcion__icontains=b) | Q(causa__icontains=b)
                           | Q(actividad__icontains=b))
        return qs

    def list(self, request, *args, **kwargs):
        """Filtros calculados (nivel, situación, vencidas) sobre el queryset."""
        qs = list(self.filter_queryset(self.get_queryset()))
        p = request.query_params
        if p.get('nivel'):
            qs = [r for r in qs if r.nivel == p['nivel']]
        if p.get('situacion'):
            qs = [r for r in qs if r.situacion == p['situacion']]
        if p.get('vencidas') == '1':
            qs = [r for r in qs if r.acciones_vencidas]
        return Response(RiesgoListaSerializer(qs, many=True).data)

    def _respuesta(self, r, codigo=status.HTTP_200_OK):
        r = self.get_queryset().get(pk=r.pk)
        return Response(RiesgoSerializer(r, context={'request': self.request}).data, status=codigo)

    def _guardar(self, r, request, campos=None):
        r.updated_by = request.user
        r.save(update_fields=(list(campos) + ['updated_by', 'updated_at']) if campos else None)

    def _historial(self, r, request, accion, **datos):
        r.historial = list(r.historial or []) + [{
            'fecha': timezone.localtime().isoformat(timespec='minutes'), 'usuario': _nombre(request.user),
            'accion': accion, **datos}]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        """Solo se modifican los campos de las etapas abiertas."""
        r = self.get_object()
        if not r.is_active or r.estado == 'retirado':
            return self._error('El registro no está activo.')
        abiertas = r.etapas_abiertas()
        for campo in request.data.keys():
            etapa = RiesgoOportunidad.etapa_de_campo(campo)
            if etapa and etapa not in abiertas:
                nombre = RiesgoOportunidad._meta.get_field(campo).verbose_name
                if etapa == 'identificacion':
                    return self._error(f'{r.codigo} ya está en la matriz: «{nombre}» se corrige con una '
                                       f'revaloración (con motivo).')
                return self._error(f'El tratamiento de {r.codigo} ya se verificó: «{nombre}» no se modifica. '
                                   f'Si no fue eficaz, inicie un nuevo tratamiento.')
        if r.firma_aceptacion:
            # La valoración (P × I) es parte de lo que el Gerente General aceptó: tampoco cambia con la firma vigente.
            for campo in ('estrategia', 'justificacion_aceptacion', 'probabilidad', 'impacto'):
                if campo in request.data and str(request.data.get(campo) or '') != str(getattr(r, campo) or ''):
                    return self._error('La aceptación ya está firmada por el Gerente General: la estrategia y su '
                                       'decisión no se modifican. Para cambiarlas, revalore el riesgo (con motivo); '
                                       'la firma se anula y se vuelve a firmar.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Anula un registro que aún no entra a la matriz (borrado lógico)."""
        r = self.get_object()
        if r.estado != 'borrador':
            return self._error('Un registro de la matriz no se anula: se retira con motivo.')
        r.is_active = False
        self._guardar(r, request, ['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        return Response({
            'categorias': CATEGORIAS, 'fuentes': FUENTES, 'fuentes_mejora': FUENTES_MEJORA, 'estrategias': ESTRATEGIAS,
            'estados_accion': ESTADOS_ACCION, 'niveles': NIVELES, 'decisiones_mejora': DECISIONES_MEJORA,
            'eficacias_mejora': EFICACIAS_MEJORA, 'decisiones_cartera': DECISIONES_CARTERA,
            'tipos_contexto': TIPOS_CONTEXTO,
        })
    catalogos.operacion = 'leer'

    # --- Registro en la matriz ---
    def _faltantes_tratamiento(self, r):
        falta = []
        acciones = r.acciones_activas()
        if not r.debe_tratarse:
            return falta
        if not r.estrategia:
            falta.append('la estrategia de tratamiento')
        if r.estrategia == 'aceptar':
            if _vacio(r.justificacion_aceptacion):
                falta.append('la decisión documentada de aceptar el riesgo')
            if r.nivel in ('importante', 'critico') and not r.firma_aceptacion:
                falta.append('la aceptación firmada por el Gerente General (riesgo '
                             f'{dict(NIVELES)[r.nivel].lower()})')
        elif r.estrategia:
            if not acciones:
                falta.append('al menos una acción de tratamiento')
            elif any(not (a.responsable_id or a.responsable_texto.strip()) or not a.fecha_maxima for a in acciones):
                falta.append('el responsable y la fecha máxima de cada acción')
        return falta

    @action(detail=True, methods=['post'])
    def registrar(self, request, pk=None):
        """Pasa el registro a la matriz: identificación, valoración y tratamiento completos."""
        r = self.get_object()
        if r.estado != 'borrador':
            return self._error(f'{r.codigo} ya está en la matriz.')
        falta = []
        if not r.proceso_id:
            falta.append('el proceso')
        if not r.categoria:
            falta.append('la categoría')
        if not r.fuente:
            falta.append('la fuente u origen')
        for campo, nombre in (('descripcion', 'la descripción'), ('causa', 'la causa'),
                              ('efecto', 'el efecto o beneficio esperado')):
            if _vacio(getattr(r, campo)):
                falta.append(nombre)
        if not r.probabilidad or not r.impacto:
            falta.append('la valoración (probabilidad e impacto)' if r.tipo == 'riesgo'
                         else 'la valoración (viabilidad y beneficio)')
        if not falta:
            falta = self._faltantes_tratamiento(r)
        if falta:
            return self._error('Para registrar en la matriz falta ' + ', '.join(falta) + '.')
        r.estado = 'vigente'
        self._historial(r, request, 'Registro en la matriz', valor=r.valor, nivel=r.nivel)
        self._guardar(r, request, ['estado', 'historial'])
        return self._respuesta(r)
    registrar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def aceptar_riesgo(self, request, pk=None):
        """Aceptación de un riesgo Importante o Crítico por el Gerente General, con firma."""
        r = self.get_object()
        if r.tipo != 'riesgo' or r.estrategia != 'aceptar':
            return self._error('Solo se firma la aceptación de un riesgo con estrategia «aceptar».')
        if 'tratamiento' not in r.etapas_abiertas():
            return self._error('El tratamiento de este riesgo ya no está abierto.')
        if _vacio(r.justificacion_aceptacion):
            return self._error('Registre primero la decisión documentada de aceptar el riesgo.')
        error = self._clave(request, 'la aceptación del riesgo')
        if error:
            return error
        r.firma_aceptacion = {**_firma(request), 'nivel': r.nivel, 'valor': r.valor}
        self._historial(r, request, 'Aceptación del riesgo firmada', nivel=r.nivel)
        self._guardar(r, request, ['firma_aceptacion', 'historial'])
        return self._respuesta(r)
    aceptar_riesgo.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def decidir_cartera(self, request, pk=None):
        """Oportunidad en cartera (nivel moderado): la Alta Dirección decide abordarla o descartarla."""
        r = self.get_object()
        if r.requiere_accion != 'en_cartera':
            return self._error('Solo las oportunidades de nivel moderado quedan en cartera.')
        if r.estado == 'retirado' or r.valor_residual is not None:
            return self._error('La oportunidad ya no admite esta decisión.')
        decision = request.data.get('decision')
        if decision not in dict(DECISIONES_CARTERA):
            return self._error('Indique si la oportunidad se aborda o se descarta.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la decisión.')
        r.decision_cartera, r.motivo_cartera = decision, motivo
        self._historial(r, request, f'Cartera: {dict(DECISIONES_CARTERA)[decision].lower()}', motivo=motivo)
        self._guardar(r, request, ['decision_cartera', 'motivo_cartera', 'historial'])
        return self._respuesta(r)
    decidir_cartera.operacion = 'aprobar'

    # --- Acciones de tratamiento ---
    def _datos_accion(self, request):
        from core.models import Usuario
        datos = {}
        for campo in ('actividad', 'implementacion_documental', 'responsable_texto', 'recursos'):
            if campo in request.data:
                datos[campo] = (request.data.get(campo) or '').strip()
        if 'responsable' in request.data:
            rid = request.data.get('responsable')
            datos['responsable'] = Usuario.objects.filter(pk=rid, is_active=True).first() if rid else None
        for campo in ('fecha_inicio', 'fecha_maxima'):
            if campo in request.data:
                datos[campo] = parse_date(request.data.get(campo) or '') if request.data.get(campo) else None
        if datos.get('fecha_inicio') and datos.get('fecha_maxima') and datos['fecha_maxima'] < datos['fecha_inicio']:
            return None, 'La fecha máxima no puede ser anterior a la fecha de inicio.'
        return datos, None

    def _accion(self, r, request):
        return r.acciones.filter(pk=request.data.get('accion_id'), is_active=True).first()

    @action(detail=True, methods=['post'])
    def agregar_accion(self, request, pk=None):
        r = self.get_object()
        if 'tratamiento' not in r.etapas_abiertas():
            return self._error('El tratamiento no está abierto. Si la acción anterior no fue eficaz, inicie un '
                               'nuevo tratamiento.')
        datos, error = self._datos_accion(request)
        if error:
            return self._error(error)
        if not datos.get('actividad'):
            return self._error('Describa la acción.')
        AccionRiesgo.objects.create(riesgo=r, orden=r.acciones.count() + 1, created_by=request.user,
                                    updated_by=request.user, **datos)
        return self._respuesta(r, status.HTTP_201_CREATED)
    agregar_accion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def editar_accion(self, request, pk=None):
        r = self.get_object()
        if 'tratamiento' not in r.etapas_abiertas():
            return self._error('El tratamiento no está abierto.')
        a = self._accion(r, request)
        if not a:
            return self._error('Acción no encontrada.')
        if a.estado == 'ejecutado':
            return self._error('Una acción ejecutada no se modifica.')
        datos, error = self._datos_accion(request)
        if error:
            return self._error(error)
        if 'actividad' in datos and not datos['actividad']:
            return self._error('Describa la acción.')
        cambio_plazo = r.estado != 'borrador' and 'fecha_maxima' in datos and datos['fecha_maxima'] != a.fecha_maxima
        if cambio_plazo:
            # Mover el plazo de una acción de la matriz (p. ej. para que deje de estar vencida) exige motivo y queda
            # en el historial.
            motivo = (request.data.get('motivo') or '').strip()
            if not motivo:
                return self._error('Indique el motivo del cambio del plazo máximo.')
            anterior = a.fecha_maxima
        for k, v in datos.items():
            setattr(a, k, v)
        a.updated_by = request.user
        a.save()
        if cambio_plazo:
            self._historial(r, request, 'Cambio de plazo de una acción', actividad=a.actividad[:100],
                            de=anterior.isoformat() if anterior else '',
                            a=a.fecha_maxima.isoformat() if a.fecha_maxima else '', motivo=motivo)
            r.save(update_fields=['historial'])
        return self._respuesta(r)
    editar_accion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_accion(self, request, pk=None):
        r = self.get_object()
        if r.estado != 'borrador':
            return self._error('En la matriz las acciones no se quitan: se marcan «no aplica» con su observación.')
        a = self._accion(r, request)
        if not a:
            return self._error('Acción no encontrada.')
        a.is_active = False
        a.updated_by = request.user
        a.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return self._respuesta(r)
    quitar_accion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def seguimiento_accion(self, request, pk=None):
        """Estado de una acción. Multipart: {accion_id, estado, fecha_ejecucion, observaciones, evidencia}"""
        r = self.get_object()
        if r.estado != 'vigente':
            return self._error('El seguimiento de acciones se registra con el riesgo en la matriz.')
        if r.valor_residual is not None:
            return self._error('El tratamiento ya se verificó.')
        a = self._accion(r, request)
        if not a:
            return self._error('Acción no encontrada.')
        if a.estado == 'ejecutado':
            return self._error('La acción ya está ejecutada.')
        estado = request.data.get('estado')
        if estado not in dict(ESTADOS_ACCION) or estado == 'pendiente':
            return self._error('Indique el nuevo estado: en proceso, ejecutado o no aplica.')
        obs = (request.data.get('observaciones') or '').strip()
        if estado == 'ejecutado':
            fecha = parse_date(request.data.get('fecha_ejecucion') or '')
            if not fecha:
                return self._error('Indique la fecha de ejecución.')
            if fecha > timezone.localdate():
                return self._error('La fecha de ejecución no puede ser futura.')
            if not obs and not request.FILES.get('evidencia'):
                return self._error('Registre la evidencia de la ejecución (descripción o archivo).')
            a.fecha_ejecucion = fecha
        if estado == 'no_aplica' and not obs:
            return self._error('Explique por qué la acción ya no aplica.')
        a.estado = estado
        if obs:
            a.observaciones = obs
        if request.FILES.get('evidencia'):
            a.evidencia = request.FILES['evidencia']
        a.updated_by = request.user
        a.save()
        return self._respuesta(r)
    seguimiento_accion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def registrar_incumplimiento(self, request, pk=None):
        """Acción no ejecutada dentro de su plazo: se registra como hallazgo para su acción correctiva."""
        r = self.get_object()
        a = self._accion(r, request)
        if not a:
            return self._error('Acción no encontrada.')
        fuera_de_plazo = a.vencida or (a.estado == 'ejecutado' and a.fecha_maxima and a.fecha_ejecucion
                                       and a.fecha_ejecucion > a.fecha_maxima)
        if not fuera_de_plazo:
            return self._error('La acción no está fuera de su plazo máximo.')
        if a.hallazgo_incumplimiento_id:
            return self._error(f'El incumplimiento ya está registrado como {a.hallazgo_incumplimiento.codigo}.')
        h = self._crear_hallazgo(
            request, r.proceso,
            f'La acción «{a.actividad[:200]}» del {r.get_tipo_display().lower()} {r.codigo} no se ejecutó dentro de '
            f'su plazo máximo de implementación ({a.fecha_maxima.isoformat()}).', 'seguimiento')
        a.hallazgo_incumplimiento = h
        a.updated_by = request.user
        a.save(update_fields=['hallazgo_incumplimiento', 'updated_by', 'updated_at'])
        return self._respuesta(r)
    registrar_incumplimiento.operacion = 'editar'

    # --- Verificación de la eficacia ---
    @action(detail=True, methods=['post'])
    def verificar(self, request, pk=None):
        """Valoración residual. Body: {residual_probabilidad, residual_impacto, fecha_verificacion, evidencia}"""
        r = self.get_object()
        if r.estado != 'vigente':
            return self._error('La eficacia se verifica con el registro en la matriz.')
        if r.valor_residual is not None:
            return self._error('La eficacia ya está verificada. Si no fue eficaz, inicie un nuevo tratamiento.')
        acciones = r.acciones_activas()
        ejecutadas = [a for a in acciones if a.estado == 'ejecutado']
        if not ejecutadas or any(a.estado not in ('ejecutado', 'no_aplica') for a in acciones):
            return self._error('La eficacia se verifica cuando todas las acciones están ejecutadas.')
        tardias = [a for a in ejecutadas if a.fecha_maxima and a.fecha_ejecucion > a.fecha_maxima
                   and not a.hallazgo_incumplimiento_id]
        if tardias:
            return self._error('Hay acciones ejecutadas fuera de su plazo máximo: registre primero el '
                               'incumplimiento (no corresponde valoración residual sin tratarlo).')
        p, i = _entero(request.data.get('residual_probabilidad')), _entero(request.data.get('residual_impacto'))
        if not p or not i or not (1 <= p <= 5 and 1 <= i <= 5):
            return self._error('Indique la valoración residual en la escala de 1 a 5.')
        fecha = parse_date(request.data.get('fecha_verificacion') or '')
        if not fecha:
            return self._error('Indique la fecha de verificación.')
        if fecha > timezone.localdate():
            return self._error('La fecha de verificación no puede ser futura.')
        ultima = max(a.fecha_ejecucion for a in ejecutadas)
        if fecha < ultima + timedelta(days=DIAS_EFICACIA):
            return self._error(f'La eficacia se verifica tras tres meses de operación de la acción: no antes del '
                               f'{(ultima + timedelta(days=DIAS_EFICACIA)).isoformat()}.')
        evidencia = (request.data.get('evidencia') or '').strip()
        if not evidencia:
            return self._error('Registre la evidencia de la verificación.')
        r.residual_probabilidad, r.residual_impacto = p, i
        r.fecha_verificacion, r.evidencia_verificacion, r.verificado_por = fecha, evidencia, request.user
        self._historial(r, request, 'Verificación de la eficacia', valor=r.valor, residual=p * i,
                        eficacia=r.eficacia)
        self._guardar(r, request)
        return self._respuesta(r)
    verificar.operacion = 'editar'

    def _archivar_ciclo(self, r, request, accion, motivo):
        self._historial(r, request, accion, motivo=motivo, probabilidad=r.probabilidad, impacto=r.impacto,
                        valor=r.valor, residual_probabilidad=r.residual_probabilidad,
                        residual_impacto=r.residual_impacto, fecha_verificacion=(
                            r.fecha_verificacion.isoformat() if r.fecha_verificacion else None),
                        evidencia=r.evidencia_verificacion, eficacia=r.eficacia)
        r.residual_probabilidad = r.residual_impacto = r.fecha_verificacion = r.verificado_por = None
        r.evidencia_verificacion = ''

    @action(detail=True, methods=['post'])
    def nuevo_tratamiento(self, request, pk=None):
        """Tratamiento no eficaz (o sin cambio): se abre un nuevo ciclo; el anterior queda en el historial."""
        r = self.get_object()
        if r.estado != 'vigente' or r.eficacia not in ('no_eficaz', 'sin_cambio'):
            return self._error('Solo se inicia un nuevo tratamiento cuando la verificación resultó no eficaz o sin '
                               'cambio.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo y el enfoque del nuevo tratamiento.')
        self._archivar_ciclo(r, request, 'Nuevo tratamiento', motivo)
        self._guardar(r, request)
        return self._respuesta(r)
    nuevo_tratamiento.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def revalorar(self, request, pk=None):
        """Actualización de la valoración (revisión anual o evento). Body: {probabilidad, impacto, controles, motivo}"""
        r = self.get_object()
        if r.estado != 'vigente':
            return self._error('Solo se revalora un registro de la matriz.')
        p, i = _entero(request.data.get('probabilidad')), _entero(request.data.get('impacto'))
        if not p or not i or not (1 <= p <= 5 and 1 <= i <= 5):
            return self._error('Indique la nueva valoración en la escala de 1 a 5.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la revaloración.')
        if r.valor_residual is not None:
            self._archivar_ciclo(r, request, 'Cierre de ciclo por revaloración', motivo)
        controles = request.data.get('controles_existentes')
        self._historial(r, request, 'Revaloración', motivo=motivo, de=f'{r.probabilidad}×{r.impacto}',
                        a=f'{p}×{i}', controles_anteriores=r.controles_existentes if controles is not None else None)
        r.probabilidad, r.impacto = p, i
        if controles is not None:
            r.controles_existentes = controles.strip()
        if r.requiere_accion != 'en_cartera':
            r.decision_cartera, r.motivo_cartera = '', ''
        if r.firma_aceptacion:
            # La aceptación firmada valía para la valoración anterior.
            r.historial[-1]['aceptacion_anulada'] = r.firma_aceptacion
            r.firma_aceptacion = {}
        self._guardar(r, request)
        return self._respuesta(r)
    revalorar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def materializar(self, request, pk=None):
        """Riesgo materializado: se registra un hallazgo para su acción correctiva. Body: {fecha, descripcion}"""
        r = self.get_object()
        if r.tipo != 'riesgo' or r.estado != 'vigente':
            return self._error('Solo se registra la materialización de un riesgo en la matriz.')
        fecha = parse_date(request.data.get('fecha') or '') or timezone.localdate()
        if fecha > timezone.localdate():
            return self._error('La fecha no puede ser futura.')
        descripcion = (request.data.get('descripcion') or '').strip()
        if not descripcion:
            return self._error('Describa cómo se materializó el riesgo.')
        h = self._crear_hallazgo(request, r.proceso, f'Riesgo materializado {r.codigo} ({r.descripcion[:150]}): '
                                                     f'{descripcion}', 'riesgo', fecha)
        self._historial(r, request, 'Materialización', fecha_evento=fecha.isoformat(), descripcion=descripcion,
                        hallazgo=h.codigo)
        self._guardar(r, request, ['historial'])
        return self._respuesta(r)
    materializar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def retirar(self, request, pk=None):
        r = self.get_object()
        if r.estado != 'vigente':
            return self._error('Solo se retira un registro de la matriz.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique por qué el registro deja de aplicar.')
        r.estado, r.motivo_retiro = 'retirado', motivo
        self._historial(r, request, 'Retiro', motivo=motivo)
        self._guardar(r, request)
        return self._respuesta(r)
    retirar.operacion = 'editar'

    # --- Hallazgos derivados, indicadores, PDF ---
    @action(detail=False, methods=['get'])
    def hallazgos_derivados(self, request):
        """Observaciones y oportunidades de mejora derivadas desde Hallazgos que aún no se registran aquí."""
        from esynapse_sig.models import Hallazgo
        usados = set(RiesgoOportunidad.objects.exclude(hallazgo=None).values_list('hallazgo_id', flat=True))
        usados |= set(OportunidadMejora.objects.exclude(hallazgo=None).values_list('hallazgo_id', flat=True))
        qs = Hallazgo.objects.filter(estado='derivado', is_active=True).exclude(pk__in=usados).order_by('-id')
        return Response([{'id': h.id, 'codigo': h.codigo, 'tipo': h.get_tipo_display(), 'fuente': h.fuente,
                          'fuente_display': h.get_fuente_display(),
                          'proceso': h.proceso, 'proceso_id': h.proceso_catalogo_id, 'descripcion': h.descripcion,
                          'fecha': h.fecha_deteccion} for h in qs])
    hallazgos_derivados.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def indicadores(self, request):
        from .indicadores import indicadores
        return Response(indicadores(list(self.get_queryset().filter(estado='vigente')),
                                    list(OportunidadMejora.objects.filter(is_active=True))))
    indicadores.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def matriz_pdf(self, request):
        from .pdf import generar_matriz_pdf
        registros = list(self.get_queryset().exclude(estado='borrador').order_by('tipo', 'codigo')
                         if request.query_params.get('borradores') != '1' else self.get_queryset())
        registros.sort(key=lambda r: (0 if r.tipo == 'riesgo' else 1, r.codigo))
        return self._pdf(generar_matriz_pdf(registros), 'Matriz de riesgos y oportunidades')
    matriz_pdf.operacion = 'leer'


class OportunidadMejoraViewSet(_Base, viewsets.ModelViewSet):
    """Matriz de oportunidades de mejora: registro → decisión → implementación → eficacia."""
    queryset = OportunidadMejora.objects.all().select_related('proceso', 'responsable', 'hallazgo')
    serializer_class = OportunidadMejoraSerializer
    pagination_class = None
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action in ('list', 'matriz_pdf'):
            qs = qs.filter(is_active=True)
        for campo in ('decision', 'estado_accion', 'eficacia', 'fuente'):
            if p.get(campo):
                qs = qs.filter(**{campo: p[campo]})
        if p.get('proceso'):
            qs = qs.filter(proceso_id=p['proceso'])
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(descripcion__icontains=b) | Q(situacion__icontains=b))
        return qs

    def _respuesta(self, o, codigo=status.HTTP_200_OK):
        o = self.get_queryset().get(pk=o.pk)
        return Response(OportunidadMejoraSerializer(o, context={'request': self.request}).data, status=codigo)

    def _guardar(self, o, request):
        o.updated_by = request.user
        o.save()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        o = self.get_object()
        abiertas = o.etapas_abiertas()
        for campo in request.data.keys():
            etapa = OportunidadMejora.etapa_de_campo(campo)
            if etapa and etapa not in abiertas:
                nombre = OportunidadMejora._meta.get_field(campo).verbose_name
                return self._error(f'{o.codigo} ya tiene decisión: «{nombre}» no se modifica.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        o = self.get_object()
        if o.decision != 'en_evaluacion':
            return self._error('Una oportunidad de mejora con decisión no se anula.')
        o.is_active = False
        self._guardar(o, request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _hist(self, o, request, accion, **datos):
        o.historial = list(o.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                  'usuario': _nombre(request.user), 'accion': accion, **datos}]

    @action(detail=True, methods=['post'])
    def decidir(self, request, pk=None):
        """Body: {decision, justificacion, accion, responsable, responsable_texto, fecha_maxima}"""
        from core.models import Usuario
        o = self.get_object()
        if o.decision != 'en_evaluacion':
            return self._error(f'{o.codigo} ya tiene decisión: {o.get_decision_display().lower()}.')
        decision = request.data.get('decision')
        if decision not in ('se_implementa', 'no_se_implementa'):
            return self._error('Indique si la mejora se implementa o no.')
        justificacion = (request.data.get('justificacion') or '').strip()
        if not justificacion:
            return self._error('Registre la justificación de la decisión.')
        if decision == 'se_implementa':
            accion = (request.data.get('accion') or '').strip()
            rid = request.data.get('responsable')
            responsable = Usuario.objects.filter(pk=rid, is_active=True).first() if rid else None
            texto = (request.data.get('responsable_texto') or '').strip()
            fecha = parse_date(request.data.get('fecha_maxima') or '')
            falta = [n for v, n in ((accion, 'la acción'), (responsable or texto, 'el responsable'),
                                    (fecha, 'la fecha máxima de implementación')) if not v]
            if falta:
                return self._error('Para implementarla registre ' + ', '.join(falta) + '.')
            o.accion, o.responsable, o.responsable_texto, o.fecha_maxima = accion, responsable, texto, fecha
        o.decision, o.justificacion, o.fecha_decision = decision, justificacion, timezone.localdate()
        self._hist(o, request, f'Decisión: {o.get_decision_display().lower()}', motivo=justificacion)
        self._guardar(o, request)
        return self._respuesta(o)
    decidir.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def seguimiento(self, request, pk=None):
        """Estado de la acción. Multipart: {estado, fecha_ejecucion, evidencia, archivo}"""
        o = self.get_object()
        if o.decision != 'se_implementa' or o.eficacia != 'pendiente':
            return self._error('El seguimiento se registra en una mejora que se implementa, antes de su eficacia.')
        if o.estado_accion == 'ejecutado':
            return self._error('La acción ya está ejecutada.')
        estado = request.data.get('estado')
        if estado not in ('en_proceso', 'ejecutado'):
            return self._error('Indique el nuevo estado: en proceso o ejecutado.')
        evidencia = (request.data.get('evidencia') or '').strip()
        if estado == 'ejecutado':
            fecha = parse_date(request.data.get('fecha_ejecucion') or '')
            if not fecha or fecha > timezone.localdate():
                return self._error('Indique la fecha de ejecución (no futura).')
            if not evidencia and not request.FILES.get('archivo'):
                return self._error('Registre la evidencia de la ejecución.')
            o.fecha_ejecucion = fecha
        o.estado_accion = estado
        if evidencia:
            o.evidencia = evidencia
        if request.FILES.get('archivo'):
            o.evidencia_archivo = request.FILES['archivo']
        self._guardar(o, request)
        return self._respuesta(o)
    seguimiento.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def evaluar_eficacia(self, request, pk=None):
        """Body: {eficacia, fecha_verificacion, evidencia}"""
        o = self.get_object()
        if o.decision != 'se_implementa' or o.estado_accion != 'ejecutado':
            return self._error('La eficacia se evalúa con la acción ejecutada.')
        if o.eficacia != 'pendiente':
            return self._error('La eficacia ya está evaluada.')
        eficacia = request.data.get('eficacia')
        if eficacia not in ('lograda', 'parcial', 'no_lograda'):
            return self._error('Indique si el beneficio se logró, se logró en parte o no se logró.')
        fecha = parse_date(request.data.get('fecha_verificacion') or '')
        if not fecha or fecha > timezone.localdate():
            return self._error('Indique la fecha de verificación (no futura).')
        if o.fecha_ejecucion and fecha < o.fecha_ejecucion:
            return self._error('La verificación no puede ser anterior a la ejecución.')
        evidencia = (request.data.get('evidencia') or '').strip()
        if not evidencia:
            return self._error('Registre la evidencia: beneficio obtenido contra el esperado'
                               + (' y qué faltó.' if eficacia != 'lograda' else '.'))
        o.eficacia, o.fecha_verificacion, o.evidencia = eficacia, fecha, evidencia
        self._hist(o, request, f'Eficacia: {o.get_eficacia_display().lower()}', motivo=evidencia)
        self._guardar(o, request)
        return self._respuesta(o)
    evaluar_eficacia.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def matriz_pdf(self, request):
        from .pdf import generar_mejoras_pdf
        return self._pdf(generar_mejoras_pdf(list(self.get_queryset().order_by('codigo'))),
                         'Matriz de oportunidades de mejora')
    matriz_pdf.operacion = 'leer'


class RevisionMatrizViewSet(_Base, viewsets.ReadOnlyModelViewSet):
    """Actualizaciones (Área SIG) y supervisiones (Gerente Técnico) de las matrices."""
    queryset = RevisionMatriz.objects.all().select_related('usuario')
    serializer_class = RevisionSerializer
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('matriz'):
            qs = qs.filter(matriz=self.request.query_params['matriz'])
        return qs

    def _registrar(self, request, tipo):
        matriz = request.data.get('matriz')
        if matriz not in dict(RevisionMatriz.MATRICES):
            return self._error('Indique la matriz.')
        error = self._clave(request, 'la ' + dict(RevisionMatriz.TIPOS_REVISION)[tipo].lower())
        if error:
            return error
        if tipo == 'supervision':
            ultima = RevisionMatriz.objects.filter(matriz=matriz, tipo='actualizacion').first()
            if ultima and ultima.usuario_id == request.user.pk:
                return self._error('La supervisión es un control independiente: no la firma quien actualizó la '
                                   'matriz.')
        r = RevisionMatriz.objects.create(matriz=matriz, tipo=tipo, usuario=request.user, fecha=timezone.localdate(),
                                          observaciones=(request.data.get('observaciones') or '').strip(),
                                          firma=_firma(request), created_by=request.user, updated_by=request.user)
        return Response(RevisionSerializer(r).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def actualizacion(self, request):
        return self._registrar(request, 'actualizacion')
    actualizacion.operacion = 'editar'

    @action(detail=False, methods=['post'])
    def supervision(self, request):
        return self._registrar(request, 'supervision')
    supervision.operacion = 'aprobar'
