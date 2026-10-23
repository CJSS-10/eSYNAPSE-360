from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular
from organizacion.models import TIPOS_PUESTO

from .models import (ATS, CAMPOS_EN_CAMPO, FORMATOS_ATS, LUGARES_ATS, NIVELES_ATS, NIVELES_IPERC, SITUACIONES,
                     TIPOS_TRABAJO, AprobacionIPERC, ATSTipo, FilaIPERC, PasoATS, PeligroCatalogo, RevisionIPERC,
                     estado_aprobacion_iperc)
from .serializers import (ATSSerializer, ATSTipoSerializer, FilaIPERCListaSerializer, FilaIPERCSerializer,
                          PeligroSerializer, _validar_pasos_tipo)


def _nombre(u):
    return u.get_full_name() or u.username


def _firma(request):
    u = request.user
    return {'usuario_id': u.pk, 'nombre': _nombre(u), 'cargo': getattr(u, 'cargo', ''),
            'sigla': getattr(u, 'sigla_cargo', ''), 'fecha': timezone.now().isoformat(timespec='seconds'),
            'ip': get_client_ip(request)}


class _Base:
    permission_classes = [PermisoModular]
    modulo = 'sst'
    pagination_class = None

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


class IPERCViewSet(_Base, viewsets.ModelViewSet):
    """
    Matriz IPERC: probabilidad = A+B+C+D; nivel = probabilidad × severidad; trivial,
    tolerable y moderado son aceptables; importante e intolerable no (no se trabaja
    hasta reducir el riesgo). Cada cambio queda en el historial de la fila.
    """
    queryset = FilaIPERC.objects.all().select_related('proceso', 'unidad').prefetch_related('puestos', 'responsables')

    def get_serializer_class(self):
        return FilaIPERCListaSerializer if self.action == 'list' else FilaIPERCSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action in ('list', 'matriz_pdf', 'resumen'):
            qs = qs.filter(is_active=True)
            if p.get('retirados') != '1':
                qs = qs.filter(estado='vigente')
        if p.get('area'):
            qs = qs.filter(area=p['area'])
        if p.get('unidad'):
            qs = qs.filter(unidad_id=p['unidad'])
        if p.get('proceso'):
            qs = qs.filter(proceso_id=p['proceso'])
        if p.get('puesto'):
            qs = qs.filter(Q(puestos__id=p['puesto']) | Q(todos_los_puestos=True))
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(peligro__icontains=b) | Q(riesgo__icontains=b)
                           | Q(actividad__icontains=b))
        return qs.distinct()

    def list(self, request, *args, **kwargs):
        filas = list(self.filter_queryset(self.get_queryset()))
        p = request.query_params
        if p.get('clasificacion'):
            filas = [f for f in filas if f.clasificacion == p['clasificacion']]
        if p.get('situacion'):
            filas = [f for f in filas if f.situacion_control == p['situacion']]
        return Response(FilaIPERCListaSerializer(filas, many=True).data)

    def _hist(self, f, request, accion, **datos):
        f.historial = list(f.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                  'usuario': _nombre(request.user), 'accion': accion, **datos}]

    def perform_create(self, serializer):
        f = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        self._hist(f, self.request, 'Identificación', nivel=f.clasificacion)
        f.save(update_fields=['historial'])

    def update(self, request, *args, **kwargs):
        f = self.get_object()
        if f.estado != 'vigente':
            return self._error('La fila está retirada: queda como registro.')
        editables = {fld.name for fld in FilaIPERC._meta.concrete_fields} - {'historial', 'estado', 'codigo', 'id'}
        antes = {c: getattr(f, c) for c in request.data.keys() if c in editables}
        nivel_antes, residual_antes = f.clasificacion, f.r_clasificacion
        puestos_antes = set(f.puestos.values_list('pk', flat=True))
        responsables_antes = set(f.responsables.values_list('pk', flat=True))
        kwargs['partial'] = True
        resp = super().update(request, *args, **kwargs)
        f.refresh_from_db()
        cambiados = [FilaIPERC._meta.get_field(c).verbose_name for c, v in antes.items() if getattr(f, c) != v]
        if set(f.puestos.values_list('pk', flat=True)) != puestos_antes:
            cambiados.append('Puestos expuestos')
        if set(f.responsables.values_list('pk', flat=True)) != responsables_antes:
            cambiados.append('Responsable(s) de los controles')
        if cambiados:
            datos = {'campos': ', '.join(cambiados)}
            if nivel_antes != f.clasificacion:
                datos['de'], datos['a'] = nivel_antes, f.clasificacion
            if residual_antes != f.r_clasificacion:
                datos['residual'] = f'{residual_antes or "—"} → {f.r_clasificacion or "—"}'
            self._hist(f, request, 'Actualización', **datos)
            f.save(update_fields=['historial'])
        return Response(FilaIPERCSerializer(f).data) if resp.status_code == 200 else resp

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return self._error('Las filas de la matriz no se eliminan: se retiran con motivo.')

    @action(detail=True, methods=['post'])
    def retirar(self, request, pk=None):
        f = self.get_object()
        motivo = (request.data.get('motivo') or '').strip()
        if f.estado != 'vigente':
            return self._error('La fila ya está retirada.')
        if not motivo:
            return self._error('Indique por qué la fila deja de aplicar (actividad eliminada, peligro inexistente…).')
        f.estado = 'retirado'
        self._hist(f, request, 'Retiro', motivo=motivo)
        f.updated_by = request.user
        f.save(update_fields=['estado', 'historial', 'updated_by', 'updated_at'])
        return Response(FilaIPERCSerializer(f).data)
    retirar.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def catalogos(self, request):
        areas = list(FilaIPERC.objects.filter(is_active=True).values_list('area', flat=True).distinct().order_by('area'))
        return Response({'areas': areas, 'niveles': NIVELES_IPERC, 'situaciones': SITUACIONES,
                         'tipos_puesto': TIPOS_PUESTO, 'tipos_trabajo': TIPOS_TRABAJO, 'niveles_ats': NIVELES_ATS,
                         'lugares_ats': LUGARES_ATS, 'formatos_ats': FORMATOS_ATS,
                         'peligros': PeligroSerializer(PeligroCatalogo.objects.all(), many=True).data})
    catalogos.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def por_trabajador(self, request):
        """
        Riesgos a los que está expuesto un trabajador según la matriz: filas de su puesto en su área
        (o sin área: lugares comunes) y filas «todos los puestos» de su área o comunes.
        """
        from organizacion.models import Trabajador
        t = Trabajador.objects.filter(pk=request.query_params.get('trabajador')).select_related(
            'puesto', 'area', 'puesto__area').first()
        if not t:
            return self._error('Trabajador no encontrado.')
        area, unidades = t.area_efectiva, []
        while area:
            unidades.append(area.pk)
            area = area.padre
        base = FilaIPERC.objects.filter(is_active=True, estado='vigente').filter(
            Q(unidad__isnull=True) | Q(unidad_id__in=unidades))
        filas = list(base.filter(Q(puestos=t.puesto) | Q(todos_los_puestos=True)).distinct()
                     .select_related('unidad').order_by('area', 'codigo'))
        return Response({'trabajador': t.nombre_completo, 'puesto': t.puesto.nombre, 'filas': [
            {'id': f.id, 'codigo': f.codigo, 'hoja': f.area, 'actividad': f.actividad, 'peligro': f.peligro,
             'riesgo': f.riesgo, 'clasificacion': f.clasificacion, 'nivel_riesgo': f.nivel_riesgo,
             'r_clasificacion': f.r_clasificacion, 'control_epp': f.control_epp,
             'todos_los_puestos': f.todos_los_puestos} for f in filas]})
    por_trabajador.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def por_puesto(self, request):
        """Filas vigentes por puesto expuesto (las «todos los puestos» aparte)."""
        from django.db.models import Count
        qs = FilaIPERC.objects.filter(is_active=True, estado='vigente')
        filas = qs.filter(puestos__isnull=False).values('puestos').annotate(n=Count('id', distinct=True))
        return Response({'por_puesto': {str(f['puestos']): f['n'] for f in filas},
                         'todos_los_puestos': qs.filter(todos_los_puestos=True).count()})
    por_puesto.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Distribución por nivel (inicial y residual) y situación de control, por área."""
        filas = list(self.get_queryset())
        areas = {}
        for f in filas:
            a = areas.setdefault(f.area, {'area': f.area, 'total': 0, 'niveles': {}, 'residual': {}, 'situacion': {}})
            a['total'] += 1
            a['niveles'][f.clasificacion or 'sin'] = a['niveles'].get(f.clasificacion or 'sin', 0) + 1
            if f.r_clasificacion:
                a['residual'][f.r_clasificacion] = a['residual'].get(f.r_clasificacion, 0) + 1
            a['situacion'][f.situacion_control] = a['situacion'].get(f.situacion_control, 0) + 1
        revisiones = {}
        for r in RevisionIPERC.objects.all().select_related('usuario'):
            revisiones.setdefault(r.area, {'fecha': r.fecha, 'responsable': r.responsable_nombre})
        for a in areas.values():
            a['ultima_revision'] = revisiones.get(a['area'])
            est, ap = estado_aprobacion_iperc(a['area'])
            a['aprobacion'] = {'estado': est, 'fecha': ap.fecha if ap else None}
        return Response({'total': len(filas), 'areas': sorted(areas.values(), key=lambda x: x['area'])})
    resumen.operacion = 'leer'

    @action(detail=False, methods=['post'])
    def revisar_area(self, request):
        """Actualización / revisión de la matriz de un área, con firma. Body: {area, observaciones, password}"""
        area = (request.data.get('area') or '').strip()
        if not FilaIPERC.objects.filter(area=area, is_active=True).exists():
            return self._error('Indique un área de la matriz.')
        error = self._clave(request, 'la revisión de la matriz')
        if error:
            return error
        r = RevisionIPERC.objects.create(area=area, usuario=request.user, observaciones=(
            request.data.get('observaciones') or '').strip(), firma=_firma(request), created_by=request.user,
            updated_by=request.user)
        return Response({'id': r.id, 'area': r.area, 'fecha': r.fecha, 'responsable': r.responsable_nombre},
                        status=status.HTTP_201_CREATED)
    revisar_area.operacion = 'editar'

    # --- Aprobación por el Comité de SST ("realizado y aprobado por") ---
    @staticmethod
    def _cargo_comite(m):
        if m.cargo == 'presidente':
            return 'Presidente del Comité de SST'
        if m.cargo == 'secretario':
            return 'Secretario(a) del Comité de SST'
        return f'Miembro {m.get_condicion_display().lower()} del Comité de SST'

    @action(detail=False, methods=['get'])
    def aprobaciones(self, request):
        """Estado de aprobación por hoja, historial y titulares del comité vigente (con su forma de firmar)."""
        from .comite import ComiteSST
        from .epp_api import _estado_pin
        hojas = sorted(set(FilaIPERC.objects.filter(is_active=True).values_list('area', flat=True)))
        estados = []
        for h in hojas:
            est, ap = estado_aprobacion_iperc(h)
            estados.append({'area': h, 'estado': est, 'fecha': ap.fecha if ap else None,
                            'cambios': FilaIPERC.objects.filter(area=h, updated_at__gt=ap.created_at).count()
                            if ap else None})
        hoy = timezone.localdate()
        c = ComiteSST.objects.filter(is_active=True, fecha_instalacion__lte=hoy, fecha_fin__gte=hoy).first()
        titulares = [{'id': m.pk, 'nombre': m.trabajador.nombre_completo, 'cargo': self._cargo_comite(m),
                      'representacion': m.get_representacion_display(), 'firma': _estado_pin(m.trabajador)}
                     for m in (c.titulares().select_related('trabajador__usuario') if c else [])]
        historial = [{'id': a.pk, 'fecha': a.fecha, 'areas': a.areas, 'firmas': a.firmas,
                      'reunion': a.reunion.codigo if a.reunion_id else None, 'observaciones': a.observaciones,
                      'archivo_url': a.archivo.url if a.archivo else None, 'registro': a.registro}
                     for a in AprobacionIPERC.objects.all().select_related('reunion')[:30]]
        return Response({'areas': estados, 'comite': c.periodo if c else None, 'titulares': titulares,
                         'quorum': len(titulares) // 2 + 1 if titulares else 0, 'historial': historial})
    aprobaciones.operacion = 'leer'

    @action(detail=False, methods=['post'])
    def aprobar_comite(self, request):
        """Aprobación del Comité. En pantalla (JSON): {areas, fecha, reunion?, observaciones,
        firmas: [{miembro, clave | pin | pin_nuevo + pin_confirmacion}]}: cada titular firma con la contraseña de su
        usuario o, si no tiene usuario, con su PIN. En papel (multipart): {areas, fecha, firmantes, archivo, password}:
        se adjunta el acta firmada y quien registra firma con su contraseña."""
        import json
        from django.utils.dateparse import parse_date
        from .comite import ComiteSST, ReunionComite
        from .epp_api import firma_persona

        def lista(v):
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except ValueError:
                    v = [x for x in v.split(',') if x.strip()]
            return list(v or [])
        areas = [str(a).strip() for a in lista(request.data.get('areas')) if str(a).strip()]
        hojas = set(FilaIPERC.objects.filter(is_active=True).values_list('area', flat=True))
        if not areas:
            return self._error('Elija las hojas de la matriz que aprueba el Comité.')
        fuera = [a for a in areas if a not in hojas]
        if fuera:
            return self._error(f'La hoja «{fuera[0]}» no existe en la matriz.')
        fecha = parse_date(str(request.data.get('fecha') or '')[:10]) or timezone.localdate()
        if fecha > timezone.localdate():
            return self._error('La fecha de aprobación no puede ser futura.')
        c = ComiteSST.objects.filter(is_active=True, fecha_instalacion__lte=fecha, fecha_fin__gte=fecha).first()
        if not c:
            return self._error('No hay un Comité de SST vigente en esa fecha.')
        titulares = {m.pk: m for m in c.titulares().select_related('trabajador__usuario')}
        quorum = len(titulares) // 2 + 1
        reunion = None
        if request.data.get('reunion'):
            reunion = ReunionComite.objects.filter(pk=request.data['reunion'], comite=c, is_active=True).first()
            if not reunion:
                return self._error('Reunión no encontrada en el comité vigente.')
        papel = bool(request.FILES.get('archivo'))
        firmas = []
        if papel:
            ids = [int(x) for x in lista(request.data.get('firmantes')) if str(x).isdigit()]
            ajenos = [i for i in ids if i not in titulares]
            if ajenos or len(set(ids)) < quorum:
                return self._error(f'Marque a los titulares que firmaron el acta (al menos {quorum}).')
            error = self._clave(request, 'el registro de la aprobación')
            if error:
                return error
            for i in dict.fromkeys(ids):
                m = titulares[i]
                firmas.append({'miembro_id': m.pk, 'trabajador_id': m.trabajador_id,
                               'nombre': m.trabajador.nombre_completo, 'cargo': self._cargo_comite(m),
                               'metodo': 'papel', 'fecha': fecha.isoformat()})
        else:
            datos = lista(request.data.get('firmas'))
            ids = [int(f.get('miembro') or 0) for f in datos if isinstance(f, dict)]
            if any(i not in titulares for i in ids) or len(ids) != len(set(ids)):
                return self._error('Solo firman los miembros titulares del comité, una vez cada uno.')
            if len(ids) < quorum:
                return self._error(f'Se requiere la firma de al menos {quorum} titular(es) (mitad más uno); '
                                   f'firmaron {len(ids)}.')
            # Primero se validan todas las credenciales; los PIN nuevos se guardan solo si todas son válidas.
            nuevos = []
            for f in datos:
                m = titulares[int(f['miembro'])]
                fm, error = firma_persona(request, m.trabajador, datos=f, clave='clave', crear_pin=False)
                if error:
                    return error
                if fm['metodo'] == 'pin' and f.get('pin_nuevo'):
                    nuevos.append((m, f))
                firmas.append({**fm, 'miembro_id': m.pk, 'cargo': self._cargo_comite(m)})
            for m, f in nuevos:
                firma_persona(request, m.trabajador, datos=f, clave='clave')
        ap = AprobacionIPERC.objects.create(
            fecha=fecha, areas=areas, reunion=reunion, firmas=firmas,
            archivo=request.FILES.get('archivo') if papel else None,
            observaciones=(request.data.get('observaciones') or '').strip(), registro=_firma(request),
            created_by=request.user, updated_by=request.user)
        return Response({'id': ap.pk, 'fecha': ap.fecha, 'areas': ap.areas, 'firmas': len(firmas)},
                        status=status.HTTP_201_CREATED)
    aprobar_comite.operacion = 'aprobar'

    @action(detail=False, methods=['get'])
    def matriz_pdf(self, request):
        from .pdf import generar_iperc_pdf
        area = request.query_params.get('area')
        filas = list(self.get_queryset().order_by('area', 'codigo'))
        return self._pdf(generar_iperc_pdf(filas, area), f'Matriz IPERC{" - " + area if area else ""}')
    matriz_pdf.operacion = 'leer'


class ATSTipoViewSet(_Base, viewsets.ModelViewSet):
    """ATS tipo por servicio: etapas, peligros y medidas típicas para preparar los ATS."""
    queryset = ATSTipo.objects.all().select_related('proceso').prefetch_related('filas_iperc')
    serializer_class = ATSTipoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('todos') != '1':
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        t = self.get_object()
        t.is_active = False
        t.updated_by = request.user
        t.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ATSViewSet(_Base, viewsets.ModelViewSet):
    """
    Análisis de Trabajo Seguro.
    - En instalaciones de Metrindust: preparación → validación del supervisor con firma (antes de iniciar).
    - En campo: preparación → en campo (se imprime y se firma en el lugar, en el formato de Metrindust o en el
      del cliente) → recibido (con el ATS firmado adjunto) → revisado por SST con firma.
    Anulación con motivo; nunca se elimina.
    """
    queryset = ATS.objects.all().select_related('proceso', 'supervisor', 'ats_tipo', 'recibido_por', 'revisor') \
        .prefetch_related('pasos', 'filas_iperc')
    serializer_class = ATSSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list':
            qs = qs.filter(is_active=True)
        if p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        if p.get('lugar'):
            qs = qs.filter(lugar_ejecucion=p['lugar'])
        if p.get('buscar'):
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(tarea__icontains=b) | Q(zona__icontains=b)
                           | Q(orden_trabajo__icontains=b) | Q(cliente__icontains=b))
        return qs

    def _respuesta(self, a, codigo=status.HTTP_200_OK):
        return Response(ATSSerializer(ATS.objects.get(pk=a.pk)).data, status=codigo)

    def _hist(self, a, request, accion, **datos):
        a.historial = list(a.historial or []) + [{'fecha': timezone.localtime().isoformat(timespec='minutes'),
                                                  'usuario': _nombre(request.user), 'accion': accion, **datos}]

    def perform_create(self, serializer):
        a = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        t = a.ats_tipo
        if t:
            # Se prepara desde el ATS tipo: etapas, tipo de trabajo, proceso y filas IPERC.
            for n, p in enumerate(t.pasos or [], start=1):
                PasoATS.objects.create(ats=a, orden=n, created_by=self.request.user, updated_by=self.request.user,
                                       **{k: p.get(k) if p.get(k) is not None else ('' if k in (
                                           'etapa', 'peligros', 'riesgos', 'medidas') else None)
                                          for k in ('etapa', 'peligros', 'riesgos', 'medidas', 'severidad',
                                                    'probabilidad', 'r_severidad', 'r_probabilidad')})
            if not a.tipos_trabajo:
                a.tipos_trabajo = list(t.tipos_trabajo or [])
            if not a.proceso_id:
                a.proceso = t.proceso
            if not a.filas_iperc.exists():
                a.filas_iperc.set(t.filas_iperc.all())
        self._hist(a, self.request, 'Preparación', **({'ats_tipo': t.nombre} if t else {}))
        a.save()

    def update(self, request, *args, **kwargs):
        a = self.get_object()
        abiertas = a.etapas_abiertas()
        if not abiertas:
            return self._error(f'El ATS está {a.get_estado_display().lower()}: no se modifica. Si cambian las '
                               'condiciones, elabore uno nuevo.')
        if 'preparacion' not in abiertas:
            cerrados = [ATS._meta.get_field(c).verbose_name for c in request.data.keys()
                        if c not in CAMPOS_EN_CAMPO and c in {f.name for f in ATS._meta.get_fields()}]
            if cerrados:
                return self._error('El ATS ya salió a campo: la preparación quedó cerrada '
                                   f'({", ".join(cerrados)}). Solo se transcribe lo que cambió en el lugar.')
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        return self._error('Un ATS no se elimina: se anula con motivo.')

    def _paso(self, a, request):
        return a.pasos.filter(pk=request.data.get('paso_id'), is_active=True).first()

    def _datos_paso(self, request):
        datos = {}
        for c in ('etapa', 'peligros', 'riesgos', 'medidas'):
            if c in request.data:
                datos[c] = (request.data.get(c) or '').strip()
        for c in ('severidad', 'probabilidad', 'r_severidad', 'r_probabilidad'):
            if c in request.data:
                v = request.data.get(c)
                try:
                    v = int(v) if v not in (None, '') else None
                except (TypeError, ValueError):
                    return None, 'Valor no válido.'
                if v is not None and not 1 <= v <= 4:
                    return None, 'Severidad y probabilidad del ATS van de 1 a 4.'
                datos[c] = v
        return datos, None

    def _sin_pasos(self, a):
        if a.pasos_editables():
            return None
        if a.formato == 'cliente':
            return self._error('El ATS se llenó en el formato del cliente: sus etapas están en el archivo adjunto.')
        return self._error(f'El ATS está {a.get_estado_display().lower()}: sus etapas no se modifican.')

    @action(detail=True, methods=['post'])
    def agregar_paso(self, request, pk=None):
        a = self.get_object()
        error = self._sin_pasos(a)
        if error:
            return error
        datos, err = self._datos_paso(request)
        if err:
            return self._error(err)
        if not datos.get('etapa'):
            return self._error('Describa la etapa.')
        PasoATS.objects.create(ats=a, orden=a.pasos.filter(is_active=True).count() + 1, created_by=request.user,
                               updated_by=request.user, **datos)
        return self._respuesta(a, status.HTTP_201_CREATED)
    agregar_paso.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def editar_paso(self, request, pk=None):
        a = self.get_object()
        error = self._sin_pasos(a)
        if error:
            return error
        p = self._paso(a, request)
        if not p:
            return self._error('Etapa no encontrada.')
        datos, err = self._datos_paso(request)
        if err:
            return self._error(err)
        for k, v in datos.items():
            setattr(p, k, v)
        p.updated_by = request.user
        p.save()
        return self._respuesta(a)
    editar_paso.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_paso(self, request, pk=None):
        a = self.get_object()
        error = self._sin_pasos(a)
        if error:
            return error
        p = self._paso(a, request)
        if not p:
            return self._error('Etapa no encontrada.')
        p.is_active = False
        p.save(update_fields=['is_active'])
        for n, q in enumerate(a.pasos.filter(is_active=True).order_by('orden', 'id'), start=1):
            if q.orden != n:
                q.orden = n
                q.save(update_fields=['orden'])
        return self._respuesta(a)
    quitar_paso.operacion = 'editar'

    def _faltantes_generales(self, a):
        falta = []
        if not a.zona.strip():
            falta.append('la zona de trabajo')
        if not a.tarea.strip():
            falta.append('la tarea')
        if not [e for e in a.ejecutantes if (e.get('nombre') or '').strip()]:
            falta.append('el personal ejecutante')
        return falta

    def _revisar_pasos(self, a, falta):
        """Etapas completas y riesgo residual: (mensaje de error, etapas intolerables)."""
        pasos = list(a.pasos.filter(is_active=True))
        if not pasos:
            falta.append('al menos una etapa')
        elif any(not p.valor or not p.medidas for p in pasos):
            falta.append('la evaluación (S y P) y las medidas de control de cada etapa')
        if falta:
            return 'Registre ' + ', '.join(falta) + '.', []
        sin_residual = [p.orden for p in pasos if p.nivel in ('significativo', 'intolerable') and not p.r_valor]
        if sin_residual:
            return ('Las etapas con riesgo significativo o intolerable requieren la evaluación con medidas de '
                    f'control (S y P residuales): etapa(s) {", ".join(map(str, sin_residual))}.'), []
        return None, [p.orden for p in pasos if (p.r_nivel or p.nivel) == 'intolerable']

    @action(detail=True, methods=['post'])
    def validar(self, request, pk=None):
        """ATS en instalaciones de Metrindust: el supervisor o prevencionista lo valida antes de iniciar, con firma."""
        a = self.get_object()
        if a.en_campo:
            return self._error('Es un ATS de trabajo en campo: se envía a campo y, al volver, se recibe y se revisa.')
        if a.estado != 'borrador':
            return self._error('El ATS ya fue validado o anulado.')
        mensaje, intolerables = self._revisar_pasos(a, self._faltantes_generales(a))
        if mensaje:
            return self._error('Para validar el ATS: ' + mensaje[0].lower() + mensaje[1:])
        if intolerables:
            return self._error('Riesgo intolerable después de las medidas de control: no se permite realizar el '
                               f'trabajo (etapa(s) {", ".join(map(str, intolerables))}).')
        error = self._clave(request, 'la validación del ATS')
        if error:
            return error
        a.estado, a.supervisor, a.firma_supervisor = 'validado', request.user, _firma(request)
        self._hist(a, request, 'Validación')
        a.updated_by = request.user
        a.save()
        return self._respuesta(a)
    validar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def enviar_a_campo(self, request, pk=None):
        """El ATS preparado sale a campo (se imprime prellenado o se usará el formato del cliente)."""
        a = self.get_object()
        if not a.en_campo:
            return self._error('Es un ATS en las instalaciones de Metrindust: se valida con firma antes de iniciar.')
        if a.estado != 'borrador':
            return self._error('El ATS ya salió a campo.')
        falta = self._faltantes_generales(a)
        if not a.fecha:
            falta.append('la fecha')
        if falta:
            return self._error('Para enviarlo a campo registre ' + ', '.join(falta) + '.')
        a.estado = 'en_campo'
        self._hist(a, request, 'Enviado a campo')
        a.updated_by = request.user
        a.save()
        return self._respuesta(a)
    enviar_a_campo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def recibir(self, request, pk=None):
        """Multipart: {evidencia, fecha_ejecucion, observaciones}. El ATS vuelve de campo firmado."""
        a = self.get_object()
        if a.estado != 'en_campo':
            return self._error('Solo se recibe un ATS que está en campo.')
        archivo = request.FILES.get('evidencia')
        if not archivo and not a.evidencia:
            return self._error('Adjunte el ATS firmado en campo (foto o escaneo).')
        from datetime import date
        fecha = request.data.get('fecha_ejecucion') or ''
        try:
            fecha = date.fromisoformat(fecha) if fecha else a.fecha
        except ValueError:
            return self._error('Fecha de ejecución no válida.')
        if fecha and fecha > timezone.localdate():
            return self._error('La fecha de ejecución no puede ser futura.')
        if archivo:
            a.evidencia = archivo
        a.fecha_ejecucion = fecha
        a.observaciones_campo = (request.data.get('observaciones') or '').strip()
        a.estado, a.recibido_por, a.fecha_recepcion = 'recibido', request.user, timezone.now()
        self._hist(a, request, 'Recepción', archivo=a.evidencia.name.rsplit('/', 1)[-1])
        a.updated_by = request.user
        a.save()
        return self._respuesta(a)
    recibir.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def observar(self, request, pk=None):
        """SST devuelve el ATS recibido (archivo ilegible, falta una firma, transcripción incompleta)."""
        a = self.get_object()
        if a.estado != 'recibido':
            return self._error('Solo se devuelve un ATS recibido y pendiente de revisión.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique qué falta corregir.')
        a.estado = 'en_campo'
        self._hist(a, request, 'Devuelto con observación', motivo=motivo)
        a.updated_by = request.user
        a.save()
        return self._respuesta(a)
    observar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def revisar(self, request, pk=None):
        """Revisión de SST con firma del ATS recibido de campo. Body: {password, observaciones}"""
        a = self.get_object()
        if a.estado != 'recibido':
            return self._error('Solo se revisa un ATS recibido de campo.')
        obs = (request.data.get('observaciones') or '').strip()
        if a.formato == 'metrindust':
            mensaje, intolerables = self._revisar_pasos(a, [])
            if mensaje:
                return self._error('Transcriba las etapas del ATS de campo antes de revisarlo: ' + mensaje[0].lower()
                                   + mensaje[1:] + ' Devuélvalo con observación si falta información.')
            if intolerables and not obs:
                return self._error('Hay etapas con riesgo intolerable después de las medidas de control '
                                   f'({", ".join(map(str, intolerables))}): registre en las observaciones qué se '
                                   'hizo (el trabajo debió detenerse) y, si corresponde, el hallazgo.')
        error = self._clave(request, 'la revisión del ATS')
        if error:
            return error
        a.estado, a.revisor, a.firma_revision, a.observaciones_revision = 'revisado', request.user, _firma(request), obs
        self._hist(a, request, 'Revisión de SST')
        a.updated_by = request.user
        a.save()
        return self._respuesta(a)
    revisar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        a = self.get_object()
        if a.estado == 'anulado':
            return self._error('El ATS ya está anulado.')
        if a.estado == 'revisado':
            return self._error('El ATS ya fue revisado: queda como registro del trabajo realizado.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo (p. ej., cambiaron las condiciones y se elaboró uno nuevo).')
        a.estado, a.motivo_anulacion = 'anulado', motivo
        self._hist(a, request, 'Anulación', motivo=motivo)
        a.updated_by = request.user
        a.save(update_fields=['estado', 'motivo_anulacion', 'historial', 'updated_by', 'updated_at'])
        return self._respuesta(a)
    anular.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def guardar_como_tipo(self, request, pk=None):
        """Crea un ATS tipo con las etapas de este ATS. Body: {nombre, descripcion}"""
        a = self.get_object()
        nombre = (request.data.get('nombre') or '').strip()
        if not nombre:
            return self._error('Indique el nombre del servicio.')
        if any(n.casefold() == nombre.casefold() for n in ATSTipo.objects.values_list('nombre', flat=True)):
            return self._error('Ya existe un ATS tipo con ese nombre.')
        pasos = _validar_pasos_tipo([{k: getattr(p, k) for k in ('etapa', 'peligros', 'riesgos', 'medidas', 'severidad',
                                                                   'probabilidad', 'r_severidad', 'r_probabilidad')}
                                     for p in a.pasos.filter(is_active=True)])
        if not pasos:
            return self._error('El ATS no tiene etapas que guardar.')
        t = ATSTipo.objects.create(nombre=nombre, descripcion=(request.data.get('descripcion') or '').strip(),
                                   tipos_trabajo=list(a.tipos_trabajo or []), proceso=a.proceso, pasos=pasos,
                                   created_by=request.user, updated_by=request.user)
        t.filas_iperc.set(a.filas_iperc.all())
        return Response(ATSTipoSerializer(t).data, status=status.HTTP_201_CREATED)
    guardar_como_tipo.operacion = 'crear'

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """ATS por estado y trabajos en campo pendientes de recibir o de revisar."""
        hoy = timezone.localdate()
        qs = ATS.objects.filter(is_active=True)
        por_estado = {k: qs.filter(estado=k).count() for k, _ in ATS._meta.get_field('estado').choices}
        pendientes = [{'id': a.id, 'codigo': a.codigo, 'fecha': a.fecha, 'cliente': a.cliente, 'zona': a.zona,
                       'dias': (hoy - a.fecha).days}
                      for a in qs.filter(estado='en_campo', fecha__lt=hoy).order_by('fecha')]
        return Response({'por_estado': por_estado, 'sin_recibir': pendientes,
                         'por_revisar': qs.filter(estado='recibido').count()})
    resumen.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        from .pdf import generar_ats_pdf
        a = self.get_object()
        if a.formato == 'cliente':
            return self._error('Este ATS se llena en el formato del cliente: vea el archivo adjunto.')
        return self._pdf(generar_ats_pdf(a), f'ATS {a.codigo}')
    pdf.operacion = 'leer'
