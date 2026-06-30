"""
eSYNAPSE 360 — API de M6 Gestión Documental.
Flujo: Borrador → En revisión → En aprobación → Vigente → Obsoleto.
Reglas críticas:
- Un documento vigente NO se edita directamente: nueva versión.
- Al aprobar una nueva versión, la anterior pasa a Obsoleto (se conserva).
- Revisar y aprobar requieren la operación 'aprobar' del módulo documentos.
"""
from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from core.middleware import get_client_ip
from core.permissions import PermisoModular

from .firmas import convertir_a_pdf, generar_pdf_firmado, hash_sha256
from .models import FirmaVersion

from .models import (
    ArchivoVersion, Documento, ObservacionVersion, VerificacionExterna, VersionDocumento,
)
from .serializers import (
    DocumentoListaSerializer,
    DocumentoSerializer,
    VerificacionExternaSerializer,
    VersionDocumentoSerializer,
)

class DocumentoViewSet(viewsets.ModelViewSet):
    queryset = Documento.objects.all().prefetch_related('versiones')
    permission_classes = [PermisoModular]
    modulo = 'documentos'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentoListaSerializer
        return DocumentoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        # Los filtros de vista solo aplican al LISTADO; el detalle y las
        # acciones siempre acceden al documento (si no, un archivado o
        # inactivo sería imposible de restaurar).
        if self.action == 'list':
            if p.get('incluir_inactivos') != '1':
                qs = qs.filter(is_active=True)
            if p.get('archivados') == '1':
                qs = qs.filter(archivado=True)
            else:
                qs = qs.filter(archivado=False)
        if p.get('tipo'):
            qs = qs.filter(tipo=p['tipo'])
        if p.get('buscar'):
            from django.db.models import Q
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(titulo__icontains=b) | Q(proceso__icontains=b))
        return qs

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete: el registro se conserva para siempre (trazabilidad),
        pero su código se LIBERA renombrándolo internamente, para que pueda
        reutilizarse en el documento correcto (caso típico: código puesto
        por error). El cambio queda en el log de auditoría.
        """
        doc = self.get_object()
        sufijo = f'~E{doc.pk}'
        if not doc.codigo.endswith(sufijo):
            doc.codigo = f'{doc.codigo[:30 - len(sufijo)]}{sufijo}'
        doc.is_active = False
        doc.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        """
        Reactiva un documento desactivado. Si su código original sigue libre,
        lo recupera; si ya fue reutilizado por otro documento, conserva el
        código renombrado (~E) y puede corregirse después.
        """
        doc = self.get_object()
        sufijo = f'~E{doc.pk}'
        if doc.codigo.endswith(sufijo):
            original = doc.codigo[:-len(sufijo)]
            if not Documento.objects.filter(codigo__iexact=original).exclude(pk=doc.pk).exists():
                doc.codigo = original
        doc.is_active = True
        doc.save()
        return Response(DocumentoSerializer(doc, context={'request': request}).data)
    activar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def editar_ficha(self, request, pk=None):
        """
        Edita los datos descriptivos (ficha) del documento PREVIA AUTORIZACIÓN
        con la contraseña del usuario (segundo factor). No toca el archivo ni el
        flujo de versiones. Quién edita y cuándo queda registrado automáticamente
        (updated_by / updated_at y el log de auditoría, campo a campo).
        """
        doc = self.get_object()
        password = request.data.get('password') or ''
        if not password:
            return Response({'detail': 'Debe confirmar con su contraseña para editar.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(password):
            return Response({'detail': 'Contraseña incorrecta. No se guardaron los cambios.'},
                            status=status.HTTP_400_BAD_REQUEST)

        EDITABLES = ('titulo', 'tipo', 'proceso', 'objetivo', 'alcance',
                     'entidad_emisora', 'normas_aplicables', 'soporte',
                     'anos_retencion', 'meses_revision', 'dias_verificacion', 'padre')
        datos = {}
        for k in EDITABLES:
            if k in request.data:
                datos[k] = request.data.get(k)
        # En multipart las normas llegan como lista repetida.
        if 'normas_aplicables' in request.data and hasattr(request.data, 'getlist'):
            lst = request.data.getlist('normas_aplicables')
            if lst:
                datos['normas_aplicables'] = lst

        ser = DocumentoSerializer(doc, data=datos, partial=True, context={'request': request})
        ser.is_valid(raise_exception=True)
        ser.save()

        # En externos la fecha de aprobación vive en la versión vigente.
        fa = request.data.get('fecha_aprobacion')
        if doc.origen == 'externo' and fa:
            from datetime import datetime, time
            v = doc.version_vigente
            if v:
                try:
                    d = datetime.strptime(str(fa)[:10], '%Y-%m-%d').date()
                    fa_dt = datetime.combine(d, time.min)
                    if timezone.is_naive(fa_dt):
                        try:
                            fa_dt = timezone.make_aware(fa_dt)
                        except Exception:
                            pass
                    v.fecha_aprobacion = fa_dt
                    v.fecha_vigencia = d
                    v.save()
                except Exception:
                    pass

        doc.refresh_from_db()
        return Response(DocumentoSerializer(doc, context={'request': request}).data)
    editar_ficha.operacion = 'editar'

    # ---------- Flujo de aprobación ----------

    def _firmar(self, request, version, rol):
        """
        Registra la firma electrónica: exige contraseña como segundo factor,
        guarda usuario, cargo, IP y hash del archivo. Devuelve error o None.
        """
        password = request.data.get('password') or ''
        if not password:
            return Response({'detail': 'Debe confirmar con su contraseña para firmar.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(password):
            return Response({'detail': 'Contraseña incorrecta. La firma no se aplicó.'},
                            status=status.HTTP_400_BAD_REQUEST)
        FirmaVersion.objects.update_or_create(
            version=version, rol=rol,
            defaults={
                'usuario': request.user,
                'cargo': request.user.cargo,
                'ip': get_client_ip(request),
                'hash_archivo': hash_sha256(version.archivo),
            },
        )
        return None

    def _solo_interno(self, doc):
        if doc.origen == 'externo':
            return Response(
                {'detail': 'Los documentos externos no pasan por flujo de aprobación: '
                           'se controlan mediante verificación de vigencia.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    @staticmethod
    def _es_si(valor, defecto=True):
        """Booleano robusto para JSON y multipart ('true'/'false' como texto)."""
        if valor is None:
            return defecto
        return str(valor).strip().lower() in ('1', 'true', 'si', 'sí', 'yes', 'on')

    def _registrar_observacion(self, request, version, etapa, accion):
        """
        Registra la observación de la etapa y, si se adjunta el documento
        anotado, lo promueve a archivo vivo de la versión: así el MISMO
        documento viaja por todas las etapas llevando sus anotaciones
        (agregadas, quitadas o modificadas) las vueltas que hagan falta hasta
        ser aprobado. La copia adjunta queda además como snapshot inmutable en
        el historial, para trazabilidad de la revisión ante auditorías.
        """
        from django.core.files.base import ContentFile
        adjunto = request.FILES.get('archivo_observaciones')
        contenido = adjunto.read() if adjunto else None
        nombre = adjunto.name if adjunto else None
        ObservacionVersion.objects.create(
            version=version,
            etapa=etapa,
            accion=accion,
            comentarios=request.data.get('comentarios', ''),
            archivo=ContentFile(contenido, name=nombre) if contenido is not None else None,
        )
        # El documento anotado pasa a ser el archivo vivo que continúa el viaje:
        # quien corrige trabaja directamente sobre las marcas recibidas. El
        # archivo se persiste con el v.save() posterior de cada acción.
        if contenido is not None:
            version.archivo.save(nombre, ContentFile(contenido, name=nombre), save=False)
            origen = 'anotado_aprobacion' if etapa == 'aprobacion' else 'anotado_revision'
            self._bitacora(version, contenido, nombre, origen)

    def _version_o_error(self, doc, estados, mensaje):
        v = doc.versiones.filter(estado__in=estados).first()
        if v is None:
            return None, Response({'detail': mensaje}, status=status.HTTP_400_BAD_REQUEST)
        return v, None

    def _bitacora(self, version, contenido, nombre, origen):
        """Registra un archivo en la bitácora append-only de la versión."""
        if contenido is None:
            return
        from django.core.files.base import ContentFile
        ArchivoVersion.objects.create(
            version=version,
            origen=origen,
            etapa=version.estado,
            hash_archivo=hash_sha256(contenido),
            archivo=ContentFile(contenido, name=nombre),
        )

    @action(detail=True, methods=['post'])
    def archivar(self, request, pk=None):
        """
        Retira el documento del uso activo conservándolo durante su periodo
        de retención. No puede archivarse con una versión
        en flujo de aprobación pendiente.
        """
        doc = self.get_object()
        if doc.versiones.filter(estado__in=['en_revision', 'en_aprobacion']).exists():
            return Response(
                {'detail': 'No puede archivarse: hay una versión en revisión o aprobación. '
                           'Complete o devuelva ese flujo primero.'},
                status=status.HTTP_400_BAD_REQUEST)
        doc.archivado = True
        doc.fecha_archivado = timezone.now()
        doc.save()
        return Response(DocumentoSerializer(doc, context={'request': request}).data)
    archivar.operacion = 'eliminar'

    @action(detail=True, methods=['post'])
    def desarchivar(self, request, pk=None):
        """Devuelve un documento archivado al uso activo."""
        doc = self.get_object()
        doc.archivado = False
        doc.fecha_archivado = None
        doc.save()
        return Response(DocumentoSerializer(doc, context={'request': request}).data)
    desarchivar.operacion = 'eliminar'

    @action(detail=True, methods=['post'])
    def reemplazar_archivo(self, request, pk=None):
        """
        Sube el documento corregido de la versión En elaboración (tras una
        devolución con observaciones). Mantiene el número de versión: las
        correcciones dentro del flujo no incrementan la versión.
        """
        doc = self.get_object()
        bloqueo = self._solo_interno(doc)
        if bloqueo:
            return bloqueo
        v, err = self._version_o_error(doc, ['borrador'],
                                       'Solo puede reemplazarse el archivo de una versión En elaboración.')
        if err:
            return err
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response({'detail': 'Adjunte el archivo corregido.'},
                            status=status.HTTP_400_BAD_REQUEST)
        from django.core.files.base import ContentFile
        contenido = archivo.read()
        nombre = archivo.name
        v.archivo.save(nombre, ContentFile(contenido, name=nombre), save=False)
        if request.data.get('resumen_cambios'):
            v.resumen_cambios = request.data['resumen_cambios']
        # Se adjuntó el corregido: se libera el candado de etapa.
        v.requiere_recarga = False
        # El archivo cambió: las firmas previas de esta versión ya no aplican
        v.firmas.all().delete()
        v.save()
        self._bitacora(v, contenido, nombre, 'correccion')
        return Response(VersionDocumentoSerializer(v, context={'request': request}).data)
    reemplazar_archivo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def enviar_revision(self, request, pk=None):
        """En elaboración → En revisión. La hace quien elabora."""
        doc = self.get_object()
        bloqueo = self._solo_interno(doc)
        if bloqueo:
            return bloqueo
        v, err = self._version_o_error(doc, ['borrador'], 'No hay versión en elaboración para enviar.')
        if err:
            return err
        if v.requiere_recarga:
            return Response(
                {'detail': 'Este documento fue devuelto con observaciones. Adjunte el documento '
                           'corregido antes de reenviarlo a revisión.'},
                status=status.HTTP_400_BAD_REQUEST)
        err = self._firmar(request, v, 'elaborado')
        if err:
            return err
        # Al reenviar, las observaciones de las rondas previas quedan atendidas:
        # se marcan como resueltas para distinguirlas de cualquier nueva.
        v.observaciones.filter(resuelta=False).update(resuelta=True)
        v.estado = 'en_revision'
        v.save()
        return Response(VersionDocumentoSerializer(v, context={'request': request}).data)
    enviar_revision.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def revisar(self, request, pk=None):
        """
        En revisión → En aprobación (conforme) o Borrador (con observaciones).
        Regla: el revisor no puede ser quien elaboró la versión.
        """
        doc = self.get_object()
        bloqueo = self._solo_interno(doc)
        if bloqueo:
            return bloqueo
        v, err = self._version_o_error(doc, ['en_revision'], 'No hay versión en revisión.')
        if err:
            return err
        if v.elaborado_por_id == request.user.id and not request.user.is_superuser:
            return Response(
                {'detail': 'Quien elabora no puede revisar su propia versión.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        conforme = self._es_si(request.data.get('conforme'), True)
        if conforme:
            err = self._firmar(request, v, 'revisado')
            if err:
                return err
        else:
            self._registrar_observacion(request, v, 'revision', 'devuelto')
            v.requiere_recarga = True
        v.comentarios_revision = request.data.get('comentarios', '')
        v.revisado_por = request.user
        v.fecha_revision = timezone.now()
        v.estado = 'en_aprobacion' if conforme else 'borrador'
        v.save()
        return Response(VersionDocumentoSerializer(v, context={'request': request}).data)
    revisar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        """
        En aprobación → Vigente. Obsoletiza la versión vigente anterior.
        Asigna fecha de vigencia y próxima revisión.
        """
        doc = self.get_object()
        bloqueo = self._solo_interno(doc)
        if bloqueo:
            return bloqueo
        v, err = self._version_o_error(doc, ['en_aprobacion'], 'No hay versión pendiente de aprobación.')
        if err:
            return err
        err = self._firmar(request, v, 'aprobado')
        if err:
            return err

        # --- Generar el PDF publicado con la hoja de firmas ---
        nombre_archivo = (v.archivo.name or '').lower()
        if nombre_archivo.endswith('.pdf'):
            v.archivo.open('rb'); pdf_base = v.archivo.read(); v.archivo.close()
        else:
            pdf_adjunto = request.FILES.get('archivo_pdf')
            if pdf_adjunto:
                pdf_base = pdf_adjunto.read()
            else:
                v.archivo.open('rb'); contenido = v.archivo.read(); v.archivo.close()
                extension = '.' + nombre_archivo.rsplit('.', 1)[-1] if '.' in nombre_archivo else '.docx'
                pdf_base = convertir_a_pdf(contenido, extension)
                if pdf_base is None:
                    FirmaVersion.objects.filter(version=v, rol='aprobado').delete()
                    return Response(
                        {'detail': 'El archivo es editable (Word/Excel) y no hay LibreOffice para '
                                   'convertirlo. Adjunte el PDF exportado en el campo archivo_pdf, '
                                   'o instale LibreOffice en el servidor.'},
                        status=status.HTTP_400_BAD_REQUEST)

        firmas = list(v.firmas.order_by('id'))
        # Capa criptográfica PAdES: el sello (logo + datos) ES el campo de
        # firma clicable. Si falla, respaldo: sellos visuales sin criptografía.
        try:
            from .firma_digital import firmar_pdf_criptograficamente
            pdf_final, cajas_firma = generar_pdf_firmado(pdf_base, doc, v, firmas, con_sellos=False)
            pdf_final = firmar_pdf_criptograficamente(pdf_final, firmas, cajas_firma)
        except Exception:
            # La firma criptográfica nunca debe impedir la publicación;
            # el documento conserva sellos visuales + registro auditado.
            # El error queda en backend/firma_error.log para diagnóstico.
            import traceback
            from pathlib import Path
            from django.conf import settings as st
            try:
                with open(Path(st.BASE_DIR) / 'firma_error.log', 'a', encoding='utf-8') as flog:
                    flog.write(f'\n=== {timezone.now()} — {doc.codigo} ===\n')
                    flog.write(traceback.format_exc())
            except OSError:
                pass
            import logging
            logging.getLogger('esynapse.firmas').exception('Fallo en firma criptográfica')
            # Respaldo: documento con sellos visuales (sin capa criptográfica)
            try:
                pdf_final, _ = generar_pdf_firmado(pdf_base, doc, v, firmas, con_sellos=True)
            except Exception:
                FirmaVersion.objects.filter(version=v, rol='aprobado').delete()
                return Response(
                    {'detail': 'El archivo de esta versión no es un PDF válido o está dañado. '
                               'Reemplácelo con un PDF correcto antes de aprobar.'},
                    status=status.HTTP_400_BAD_REQUEST)

        from django.core.files.base import ContentFile
        # La versión vigente anterior pasa a Obsoleto (se conserva el historial)
        doc.versiones.filter(estado='vigente').update(estado='obsoleto')
        hoy = timezone.now().date()
        v.estado = 'vigente'
        v.aprobado_por = request.user
        v.fecha_aprobacion = timezone.now()
        v.fecha_vigencia = hoy
        v.fecha_proxima_revision = hoy + timedelta(days=doc.meses_revision * 30)
        v.archivo_publicado.save(f'{doc.codigo}_Ver{v.version}_firmado.pdf', ContentFile(pdf_final), save=False)
        v.hash_publicado = hash_sha256(pdf_final)
        v.save()
        return Response(VersionDocumentoSerializer(v, context={'request': request}).data)
    aprobar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def devolver(self, request, pk=None):
        """En aprobación → vuelve a En elaboración para correcciones."""
        doc = self.get_object()
        bloqueo = self._solo_interno(doc)
        if bloqueo:
            return bloqueo
        v, err = self._version_o_error(doc, ['en_aprobacion'], 'No hay versión pendiente de aprobación.')
        if err:
            return err
        self._registrar_observacion(request, v, 'aprobacion', 'devuelto')
        v.requiere_recarga = True
        v.estado = 'borrador'
        v.comentarios_revision = request.data.get('comentarios', v.comentarios_revision)
        v.save()
        return Response(VersionDocumentoSerializer(v, context={'request': request}).data)
    devolver.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        """
        Rechazo DEFINITIVO: la versión queda como Rechazada (terminal) y se
        conserva en el historial. Para continuar, se crea una nueva versión.
        Requiere justificación obligatoria.
        """
        doc = self.get_object()
        bloqueo = self._solo_interno(doc)
        if bloqueo:
            return bloqueo
        v, err = self._version_o_error(doc, ['en_revision', 'en_aprobacion'],
                                       'No hay versión en revisión o aprobación para rechazar.')
        if err:
            return err
        comentarios = (request.data.get('comentarios') or '').strip()
        if not comentarios:
            return Response({'detail': 'El rechazo definitivo requiere justificación.'},
                            status=status.HTTP_400_BAD_REQUEST)
        etapa_obs = 'revision' if v.estado == 'en_revision' else 'aprobacion'
        self._registrar_observacion(request, v, etapa_obs, 'rechazado')
        v.estado = 'rechazado'
        v.comentarios_revision = comentarios
        v.revisado_por = v.revisado_por or request.user
        v.save()
        return Response(VersionDocumentoSerializer(v, context={'request': request}).data)
    rechazar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def nueva_version(self, request, pk=None):
        """
        Crea la siguiente versión en Borrador. Regla M6: un documento vigente
        no se edita — se versiona. La vigente sigue activa hasta aprobar la nueva.
        """
        doc = self.get_object()
        if doc.version_en_proceso:
            return Response(
                {'detail': 'Ya existe una versión en proceso. Complete su flujo antes de crear otra.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response({'detail': 'Debe adjuntar el archivo de la nueva versión.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if doc.origen == 'externo':
            # Nueva edición del emisor: entra Vigente, la anterior queda Obsoleta
            edicion = (request.data.get('edicion') or '').strip()
            if not edicion:
                return Response({'detail': 'Indique la edición/versión del emisor (ej: 2017, Rev. 03).'},
                                status=status.HTTP_400_BAD_REQUEST)
            doc.versiones.filter(estado='vigente').update(estado='obsoleto')
            v = VersionDocumento.objects.create(
                documento=doc,
                version=edicion,
                archivo=archivo,
                resumen_cambios=request.data.get('resumen_cambios', ''),
                estado='vigente',
                fecha_vigencia=timezone.now().date(),
                elaborado_por=request.user,
            )
            v.archivo.open('rb'); _cont = v.archivo.read(); v.archivo.close()
            self._bitacora(v, _cont, v.archivo.name.split('/')[-1], 'nueva_version')
            return Response(VersionDocumentoSerializer(v, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)
        ultima = doc.versiones.order_by('-id').first()
        try:
            siguiente = f'{int(ultima.version) + 1:02d}' if ultima else '00'
        except ValueError:
            siguiente = f'{doc.versiones.count():02d}'
        v = VersionDocumento.objects.create(
            documento=doc,
            version=siguiente,
            archivo=archivo,
            resumen_cambios=request.data.get('resumen_cambios', ''),
            estado='borrador',
            elaborado_por=request.user,
        )
        v.archivo.open('rb'); _cont = v.archivo.read(); v.archivo.close()
        self._bitacora(v, _cont, v.archivo.name.split('/')[-1], 'nueva_version')
        return Response(VersionDocumentoSerializer(v, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)
    nueva_version.operacion = 'crear'

    @action(detail=True, methods=['post'])
    def verificar_vigencia(self, request, pk=None):
        """
        Registra una verificación de vigencia de documento externo.
        Body: {"vigente": true/false, "observaciones": ""}.
        """
        doc = self.get_object()
        if doc.origen != 'externo':
            return Response({'detail': 'La verificación de vigencia aplica solo a documentos externos.'},
                            status=status.HTTP_400_BAD_REQUEST)
        verificacion = VerificacionExterna.objects.create(
            documento=doc,
            vigente=bool(request.data.get('vigente', True)),
            observaciones=request.data.get('observaciones', ''),
        )
        doc.ultima_verificacion = timezone.now()
        doc.save()
        return Response(VerificacionExternaSerializer(verificacion).data, status=status.HTTP_201_CREATED)
    verificar_vigencia.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def externos_por_verificar(self, request):
        """Documentos externos cuya verificación de vigencia está pendiente o vencida."""
        ahora = timezone.now()
        data = []
        for doc in Documento.objects.filter(origen='externo', is_active=True):
            limite = doc.ultima_verificacion + timedelta(days=doc.dias_verificacion) if doc.ultima_verificacion else None
            if limite is None or limite <= ahora:
                data.append({
                    'documento_id': doc.id,
                    'codigo': doc.codigo,
                    'titulo': doc.titulo,
                    'entidad_emisora': doc.entidad_emisora,
                    'ultima_verificacion': doc.ultima_verificacion,
                    'nunca_verificado': doc.ultima_verificacion is None,
                })
        return Response(data)
    externos_por_verificar.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def por_vencer(self, request):
        """Documentos vigentes con próxima revisión en los próximos 30 días o vencida."""
        limite = timezone.now().date() + timedelta(days=30)
        versiones = VersionDocumento.objects.filter(
            estado='vigente', documento__is_active=True,
            fecha_proxima_revision__lte=limite,
        ).select_related('documento')
        data = [{
            'documento_id': v.documento_id,
            'codigo': v.documento.codigo,
            'titulo': v.documento.titulo,
            'version': v.version,
            'fecha_proxima_revision': v.fecha_proxima_revision,
            'vencido': v.fecha_proxima_revision < timezone.now().date(),
        } for v in versiones]
        return Response(data)
    por_vencer.operacion = 'leer'


# ============================================================
# M8 — HALLAZGOS
# ============================================================
from .models import Hallazgo  # noqa: E402
from .serializers import HallazgoListaSerializer, HallazgoSerializer  # noqa: E402


class HallazgoViewSet(viewsets.ModelViewSet):
    """
    M8 — Hallazgos. Ciclo: Registrado → En análisis → En tratamiento → Cerrado
    (→ Reabierto si la verificación falla). El cierre lo hace una persona
    distinta a la responsable del tratamiento.
    """
    queryset = Hallazgo.objects.all().select_related('responsable', 'cerrado_por', 'created_by')
    permission_classes = [PermisoModular]
    modulo = 'hallazgos'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return HallazgoListaSerializer
        return HallazgoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        # Los filtros de vista solo aplican al LISTADO; el detalle y las
        # acciones siempre acceden al hallazgo aunque esté inactivo.
        if self.action == 'list' and p.get('incluir_inactivos') != '1':
            qs = qs.filter(is_active=True)
        if p.get('tipo'):
            qs = qs.filter(tipo=p['tipo'])
        if p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        if p.get('buscar'):
            from django.db.models import Q
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(descripcion__icontains=b) |
                           Q(proceso__icontains=b) | Q(requisito__icontains=b))
        return qs

    def destroy(self, request, *args, **kwargs):
        """Soft delete: un hallazgo nunca se borra."""
        h = self.get_object()
        h.is_active = False
        h.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _transicion(self, h, desde, hacia, mensaje):
        if h.estado not in desde:
            return Response({'detail': mensaje}, status=status.HTTP_400_BAD_REQUEST)
        h.estado = hacia
        return None

    def _bloquea_si_nc(self, h):
        """Las NC se tratan en su Acción Correctiva (M9), no dentro de Hallazgos."""
        if h.tipo in ('nc_mayor', 'nc_menor'):
            return Response(
                {'detail': 'El análisis, tratamiento y cierre de una No Conformidad se realizan '
                           'en su Acción Correctiva (M9). Genere la SAC desde el hallazgo.'},
                status=status.HTTP_400_BAD_REQUEST)
        return None

    @action(detail=True, methods=['post'])
    def iniciar_analisis(self, request, pk=None):
        """Registrado/Reabierto → En análisis. Puede registrar el análisis inicial."""
        h = self.get_object()
        bloqueo = self._bloquea_si_nc(h)
        if bloqueo:
            return bloqueo
        err = self._transicion(h, ['registrado', 'reabierto'], 'en_analisis',
                               'Solo un hallazgo Registrado o Reabierto puede pasar a análisis.')
        if err:
            return err
        if request.data.get('analisis'):
            h.analisis = request.data['analisis']
        h.save()
        return Response(HallazgoSerializer(h, context={'request': request}).data)
    iniciar_analisis.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def registrar_tratamiento(self, request, pk=None):
        """
        En análisis → En tratamiento. Registra la corrección inmediata
        y/o el análisis. Body: {"correccion": "...", "analisis": "..."}
        """
        h = self.get_object()
        bloqueo = self._bloquea_si_nc(h)
        if bloqueo:
            return bloqueo
        err = self._transicion(h, ['en_analisis'], 'en_tratamiento',
                               'El hallazgo debe estar En análisis para registrar tratamiento.')
        if err:
            return err
        if request.data.get('analisis'):
            h.analisis = request.data['analisis']
        if request.data.get('correccion'):
            h.correccion = request.data['correccion']
        h.save()
        return Response(HallazgoSerializer(h, context={'request': request}).data)
    registrar_tratamiento.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """
        En tratamiento → Cerrado. Verificación por persona DISTINTA al
        responsable. Requiere comentarios. Las NC Mayores no pueden cerrarse
        hasta que su AC esté verificada (se valida desde M9; por ahora alerta).
        """
        h = self.get_object()
        bloqueo = self._bloquea_si_nc(h)
        if bloqueo:
            return bloqueo
        if h.estado != 'en_tratamiento':
            return Response({'detail': 'Solo un hallazgo En tratamiento puede cerrarse.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if h.responsable_id == request.user.id and not request.user.is_superuser:
            return Response({'detail': 'El responsable del tratamiento no puede verificar su propio cierre.'},
                            status=status.HTTP_400_BAD_REQUEST)
        comentarios = (request.data.get('comentarios') or '').strip()
        if not comentarios:
            return Response({'detail': 'El cierre requiere comentarios de verificación.'},
                            status=status.HTTP_400_BAD_REQUEST)
        h.estado = 'cerrado'
        h.comentarios_cierre = comentarios
        h.cerrado_por = request.user
        h.fecha_cierre = timezone.now()
        h.save()
        return Response(HallazgoSerializer(h, context={'request': request}).data)
    cerrar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def reabrir(self, request, pk=None):
        """Cerrado → Reabierto (la verificación posterior detectó recurrencia)."""
        h = self.get_object()
        bloqueo = self._bloquea_si_nc(h)
        if bloqueo:
            return bloqueo
        if h.estado != 'cerrado':
            return Response({'detail': 'Solo un hallazgo Cerrado puede reabrirse.'},
                            status=status.HTTP_400_BAD_REQUEST)
        justificacion = (request.data.get('justificacion') or '').strip()
        if not justificacion:
            return Response({'detail': 'La reapertura requiere justificación.'},
                            status=status.HTTP_400_BAD_REQUEST)
        h.estado = 'reabierto'
        h.comentarios_cierre = f'{h.comentarios_cierre}\n[REABIERTO] {justificacion}'.strip()
        h.cerrado_por = None
        h.fecha_cierre = None
        h.save()
        return Response(HallazgoSerializer(h, context={'request': request}).data)
    reabrir.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def generar_sac(self, request, pk=None):
        """
        Deriva una No Conformidad a Acciones Correctivas: crea la
        SAC en M9 enlazada al hallazgo y precargada con su descripción y
        requisito. Solo aplica a NC (Mayor/Menor) y a una SAC activa por vez.
        Las observaciones y oportunidades de mejora se derivan a Riesgos (M3).
        """
        h = self.get_object()
        if h.tipo not in ('nc_mayor', 'nc_menor'):
            return Response(
                {'detail': 'Solo las No Conformidades generan SAC. Las observaciones y '
                           'oportunidades de mejora se derivan a Riesgos y Oportunidades.'},
                status=status.HTTP_400_BAD_REQUEST)
        from .models import SolicitudAC
        existente = h.solicitudes_ac.filter(is_active=True).order_by('-id').first()
        if existente:
            return Response(
                {'detail': f'Este hallazgo ya tiene una SAC activa ({existente.codigo}).'},
                status=status.HTTP_400_BAD_REQUEST)
        fuentes_sac = {'auditoria_interna', 'auditoria_externa', 'revision_direccion', 'queja'}
        sac = SolicitudAC.objects.create(
            hallazgo=h,
            fuente=h.fuente if h.fuente in fuentes_sac else 'otros',
            descripcion_nc=h.descripcion,
            requisito_auditado=h.requisito,
            requiere_ac=True if h.tipo == 'nc_mayor' else None,
        )
        # El hallazgo entra en tratamiento; su SAC lo cerrará al ser eficaz (M9).
        if h.estado in ('registrado', 'en_analisis'):
            h.estado = 'en_tratamiento'
            h.save()
        from .serializers import HallazgoSerializer
        data = HallazgoSerializer(h, context={'request': request}).data
        data['sac_creada'] = sac.codigo
        return Response(data, status=status.HTTP_201_CREATED)
    generar_sac.operacion = 'crear'

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Conteo por estado y tipo para el dashboard."""
        from django.db.models import Count
        qs = Hallazgo.objects.filter(is_active=True)
        return Response({
            'por_estado': dict(qs.values_list('estado').annotate(c=Count('id'))),
            'por_tipo': dict(qs.values_list('tipo').annotate(c=Count('id'))),
            'abiertos': qs.exclude(estado='cerrado').count(),
        })
    resumen.operacion = 'leer'


# ============================================================
# M9 — SOLICITUDES DE ACCIÓN CORRECTIVA
# ============================================================
from .models import AccionSAC, SolicitudAC  # noqa: E402
from .serializers import (  # noqa: E402
    AccionSACSerializer,
    SolicitudACListaSerializer,
    SolicitudACSerializer,
)


class SolicitudACViewSet(viewsets.ModelViewSet):
    """
    M9 — SAC. Ciclo:
    Registrada → evaluar (6.4) → En análisis (6.5) → aprobar_plan (6.6)
    → En implementación (6.7) → En verificación → verificar_eficacia (6.8)
    → Cerrada conforme | reanálisis si no eficaz.
    """
    queryset = SolicitudAC.objects.all().select_related(
        'responsable', 'verificador', 'hallazgo', 'created_by').prefetch_related('acciones')
    permission_classes = [PermisoModular]
    modulo = 'acciones_correctivas'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return SolicitudACListaSerializer
        return SolicitudACSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list':
            if p.get('incluir_inactivos') != '1':
                qs = qs.filter(is_active=True)
        if p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        if p.get('abiertas') == '1':
            qs = qs.exclude(estado__in=['cerrada_conforme', 'cerrada_sin_ac'])
        if p.get('buscar'):
            from django.db.models import Q
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(descripcion_nc__icontains=b) |
                           Q(requisito_auditado__icontains=b))
        return qs

    def destroy(self, request, *args, **kwargs):
        sac = self.get_object()
        sac.is_active = False
        sac.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _es_si(valor, defecto=None):
        if valor is None:
            return defecto
        return str(valor).strip().lower() in ('1', 'true', 'si', 'sí', 'yes', 'on')

    def _error(self, mensaje):
        return Response({'detail': mensaje}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def evaluar(self, request, pk=None):
        """
        6.4 — Evaluación de la necesidad de AC.
        Body: {significancia, analisis_extension, requiere_ac, justificacion}
        requiere_ac=True → En análisis | False → En implementación (solo correcciones).
        """
        sac = self.get_object()
        if sac.estado != 'registrada':
            return self._error('La evaluación solo aplica a solicitudes Registradas.')
        requiere = request.data.get('requiere_ac')
        if requiere is None:
            return self._error('Debe indicar si requiere acción correctiva.')
        sac.significancia = request.data.get('significancia', sac.significancia)
        sac.analisis_extension = request.data.get('analisis_extension', '')
        sac.justificacion_evaluacion = request.data.get('justificacion', '')
        sac.requiere_ac = self._es_si(requiere, False)
        sac.estado = 'en_analisis' if sac.requiere_ac else 'en_implementacion'
        sac.save()
        return Response(SolicitudACSerializer(sac, context={'request': request}).data)
    evaluar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def registrar_analisis(self, request, pk=None):
        """
        6.5 — Análisis de causa (5 Porqués).
        Body: {porques: [...], causa_raiz, aplica_cambios_sig, aplica_actualizar_riesgos}
        """
        sac = self.get_object()
        if sac.estado != 'en_analisis':
            return self._error('El análisis de causa aplica solo en estado En análisis.')
        porques = request.data.get('porques')
        if porques is not None:
            if isinstance(porques, str):
                import json as _json
                try:
                    porques = _json.loads(porques)
                except ValueError:
                    porques = [porques]
            sac.porques = [p for p in porques if str(p).strip()]
        sac.causa_raiz = request.data.get('causa_raiz', sac.causa_raiz)
        if 'aplica_cambios_sig' in request.data:
            sac.aplica_cambios_sig = self._es_si(request.data['aplica_cambios_sig'], False)
        if 'aplica_actualizar_riesgos' in request.data:
            sac.aplica_actualizar_riesgos = self._es_si(request.data['aplica_actualizar_riesgos'], False)
        sac.save()
        return Response(SolicitudACSerializer(sac, context={'request': request}).data)
    registrar_analisis.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def agregar_accion(self, request, pk=None):
        """Agrega corrección o acción correctiva. Body: {tipo, descripcion, fecha_propuesta, responsable}"""
        sac = self.get_object()
        if sac.estado in ('cerrada_conforme', 'cerrada_sin_ac'):
            return self._error('La solicitud está cerrada.')
        ser = AccionSACSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(solicitud=sac)
        sac = SolicitudAC.objects.prefetch_related('acciones').get(pk=sac.pk)
        return Response(SolicitudACSerializer(sac, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)
    agregar_accion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def aprobar_plan(self, request, pk=None):
        """
        6.6 — Aprueba el análisis y las acciones; designa verificador.
        Requiere causa raíz y al menos una acción correctiva.
        Body: {verificador: id}
        """
        sac = self.get_object()
        if sac.estado != 'en_analisis':
            return self._error('Solo puede aprobarse el plan de una solicitud En análisis.')
        if not sac.causa_raiz.strip():
            return self._error('Registre la causa raíz antes de aprobar el plan.')
        if not sac.acciones.filter(tipo='correctiva').exists():
            return self._error('El plan debe incluir al menos una acción correctiva.')
        verificador_id = request.data.get('verificador')
        if not verificador_id:
            return self._error('Designe al responsable de verificar la eficacia (6.6.3).')
        from core.models import Usuario
        try:
            sac.verificador = Usuario.objects.get(pk=verificador_id, is_active=True)
        except Usuario.DoesNotExist:
            return self._error('Verificador no válido.')
        sac.estado = 'en_implementacion'
        sac.save()
        return Response(SolicitudACSerializer(sac, context={'request': request}).data)
    aprobar_plan.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def completar_accion(self, request, pk=None):
        """
        6.7 — Marca una acción como completada, con evidencia adjunta.
        Body multipart: {accion_id, verificacion, evidencia (archivo)}
        Cuando todas las acciones quedan completadas → En verificación
        (o cierre directo si la SAC no requería AC).
        """
        sac = self.get_object()
        if sac.estado != 'en_implementacion':
            return self._error('Las acciones se completan en estado En implementación.')
        try:
            accion = sac.acciones.get(pk=request.data.get('accion_id'))
        except (AccionSAC.DoesNotExist, ValueError, TypeError):
            return self._error('Acción no encontrada.')
        if accion.estado == 'completada':
            return self._error('Esa acción ya está completada.')
        accion.estado = 'completada'
        accion.fecha_completada = timezone.now().date()
        accion.verificacion = request.data.get('verificacion', '')
        if request.FILES.get('evidencia'):
            accion.evidencia = request.FILES['evidencia']
        accion.save()
        if not sac.acciones.filter(estado='pendiente').exists():
            if sac.requiere_ac:
                sac.estado = 'en_verificacion'
            else:
                sac.estado = 'cerrada_sin_ac'
                sac.fecha_cierre = timezone.now()
            sac.save()
        sac = SolicitudAC.objects.prefetch_related('acciones').get(pk=sac.pk)
        return Response(SolicitudACSerializer(sac, context={'request': request}).data)
    completar_accion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def verificar_eficacia(self, request, pk=None):
        """
        6.8 — Verificación de eficacia. Body: {eficaz: bool, evaluacion}.
        Eficaz → Cerrada conforme (+ cierra el hallazgo M8 vinculado).
        No eficaz → vuelve a En análisis (+ reabre el hallazgo si estaba cerrado).
        """
        sac = self.get_object()
        if sac.estado != 'en_verificacion':
            return self._error('La solicitud no está en verificación de eficacia.')
        evaluacion = (request.data.get('evaluacion') or '').strip()
        if not evaluacion:
            return self._error('Registre la evaluación de la eficacia (6.8.1).')
        eficaz = self._es_si(request.data.get('eficaz'), None)
        if eficaz is None:
            return self._error('Indique si las acciones fueron eficaces.')
        sac.evaluacion_eficacia = evaluacion
        sac.resultado_eficaz = eficaz
        sac.fecha_verificacion = timezone.now()
        if eficaz:
            sac.estado = 'cerrada_conforme'
            sac.fecha_cierre = timezone.now()
            if sac.hallazgo and sac.hallazgo.estado != 'cerrado':
                h = sac.hallazgo
               

# ============================================================
# M10 — AUDITORÍAS INTERNAS
# ============================================================
from .models import (  # noqa: E402
    ActaAuditoria, Auditoria, EquipoAuditoria, Hallazgo as _Hallazgo,
    ItemVerificacion, ListaVerificacion, ProgramaAuditoria, RequisitoNorma,
)
from .serializers import (  # noqa: E402
    AuditoriaListaSerializer, AuditoriaSerializer, ProgramaAuditoriaSerializer,
    RequisitoNormaSerializer,
)


class RequisitoNormaViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de cláusulas de las normas (solo lectura)."""
    queryset = RequisitoNorma.objects.all()
    serializer_class = RequisitoNormaSerializer
    permission_classes = [PermisoModular]
    modulo = 'auditorias'

    def get_queryset(self):
        qs = super().get_queryset()
        norma = self.request.query_params.get('norma')
        return qs.filter(norma=norma) if norma else qs


class ProgramaAuditoriaViewSet(viewsets.ModelViewSet):
    """Programa anual de auditorías."""
    queryset = ProgramaAuditoria.objects.all().prefetch_related('auditorias__auditor_lider')
    serializer_class = ProgramaAuditoriaSerializer
    permission_classes = [PermisoModular]
    modulo = 'auditorias'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list' and self.request.query_params.get('incluir_inactivos') != '1':
            qs = qs.filter(is_active=True)
        return qs

    def destroy(self, request, *args, **kwargs):
        p = self.get_object(); p.is_active = False; p.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        p = self.get_object()
        p.estado = 'aprobado'
        p.aprobado_por = request.user
        p.fecha_aprobacion = timezone.now()
        p.save()
        return Response(ProgramaAuditoriaSerializer(p, context={'request': request}).data)
    aprobar.operacion = 'aprobar'


class AuditoriaViewSet(viewsets.ModelViewSet):
    """
    M10 — Auditoría interna. Ciclo:
    Programada → Planificada → En ejecución → En informe → Cerrada.
    Los hallazgos se registran como Hallazgos (M8), que alimentan las
    Acciones Correctivas (M9).
    """
    queryset = Auditoria.objects.all().select_related('auditor_lider', 'programa').prefetch_related(
        'equipo__usuario', 'actas', 'listas__items', 'hallazgos')
    permission_classes = [PermisoModular]
    modulo = 'auditorias'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        return AuditoriaListaSerializer if self.action == 'list' else AuditoriaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list':
            if p.get('incluir_inactivos') != '1':
                qs = qs.filter(is_active=True)
            if p.get('estado'):
                qs = qs.filter(estado=p['estado'])
            if p.get('anio'):
                qs = qs.filter(programa__anio=p['anio'])
            if p.get('buscar'):
                from django.db.models import Q
                b = p['buscar']
                qs = qs.filter(Q(codigo__icontains=b) | Q(areas_procesos__icontains=b) |
                               Q(objetivo__icontains=b))
        return qs

    def destroy(self, request, *args, **kwargs):
        a = self.get_object(); a.is_active = False; a.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _error(self, msg):
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

    def _data(self, a, request):
        # Re-consulta fresca: evita servir el caché de prefetch obsoleto tras
        # crear/editar objetos relacionados (equipo, actas, listas, hallazgos).
        a = (Auditoria.objects.select_related('auditor_lider', 'programa')
             .prefetch_related('equipo__usuario', 'actas', 'listas__items', 'hallazgos')
             .get(pk=a.pk))
        return Response(AuditoriaSerializer(a, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def planificar(self, request, pk=None):
        """Programada → Planificada. Requiere objetivo, alcance y auditor líder."""
        a = self.get_object()
        if a.estado not in ('programada', 'planificada'):
            return self._error('Solo se planifica una auditoría Programada.')
        if not a.objetivo.strip() or not a.alcance.strip() or not a.auditor_lider_id:
            return self._error('Para planificar: defina objetivo, alcance y auditor líder.')
        a.estado = 'planificada'
        a.save()
        return self._data(a, request)
    planificar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def iniciar(self, request, pk=None):
        """Planificada → En ejecución."""
        a = self.get_object()
        if a.estado != 'planificada':
            return self._error('Solo se inicia una auditoría Planificada.')
        a.estado = 'en_ejecucion'
        if not a.fecha_inicio:
            a.fecha_inicio = timezone.now().date()
        a.save()
        return self._data(a, request)
    iniciar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def reprogramar(self, request, pk=None):
        """Mueve la fecha/mes con motivo registrado."""
        a = self.get_object()
        a.reprogramada = True
        a.motivo_reprogramacion = request.data.get('motivo', '')
        if request.data.get('mes_programado'):
            a.mes_programado = int(request.data['mes_programado'])
        if request.data.get('fecha_programada'):
            a.fecha_programada = request.data['fecha_programada']
        a.save()
        return self._data(a, request)
    reprogramar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def agregar_integrante(self, request, pk=None):
        a = self.get_object()
        rol = request.data.get('rol')
        if rol not in dict([('lider', 1), ('auditor', 1), ('experto', 1), ('observador', 1)]):
            return self._error('Rol no válido.')
        usuario_id = request.data.get('usuario') or None
        usuario = None
        if usuario_id:
            from core.models import Usuario
            usuario = Usuario.objects.filter(pk=usuario_id, is_active=True).first()
        EquipoAuditoria.objects.create(
            auditoria=a, usuario=usuario,
            nombre_externo=request.data.get('nombre_externo', ''),
            rol=rol, cargo=request.data.get('cargo', ''))
        return self._data(a, request)
    agregar_integrante.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_integrante(self, request, pk=None):
        a = self.get_object()
        EquipoAuditoria.objects.filter(auditoria=a, pk=request.data.get('integrante_id')).delete()
        return self._data(a, request)
    quitar_integrante.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def registrar_acta(self, request, pk=None):
        """Registra/actualiza el acta de apertura o cierre."""
        a = self.get_object()
        tipo = request.data.get('tipo')
        if tipo not in ('apertura', 'cierre'):
            return self._error('Tipo de acta no válido (apertura/cierre).')
        participantes = request.data.get('participantes', [])
        if isinstance(participantes, str):
            import json as _json
            try:
                participantes = _json.loads(participantes)
            except ValueError:
                participantes = []
        acta, _ = ActaAuditoria.objects.update_or_create(
            auditoria=a, tipo=tipo,
            defaults={
                'participantes': participantes,
                'contenido': request.data.get('contenido', ''),
                'observaciones_auditado': request.data.get('observaciones_auditado', ''),
            })
        if request.FILES.get('archivo'):
            acta.archivo = request.FILES['archivo']
            acta.save()
        return self._data(a, request)
    registrar_acta.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def generar_lista(self, request, pk=None):
        """Crea la lista de verificación de una norma con sus cláusulas del catálogo."""
        a = self.get_object()
        norma = request.data.get('norma')
        if norma not in ('iso_9001', 'iso_14001', 'iso_45001', 'iso_17025'):
            return self._error('Norma no válida.')
        if ListaVerificacion.objects.filter(auditoria=a, norma=norma).exists():
            return self._error('Ya existe la lista de verificación de esa norma.')
        lista = ListaVerificacion.objects.create(auditoria=a, norma=norma)
        reqs = RequisitoNorma.objects.filter(norma=norma).order_by('orden')
        ItemVerificacion.objects.bulk_create([
            ItemVerificacion(lista=lista, codigo=r.codigo, titulo=r.titulo,
                             es_seccion=r.es_seccion, orden=r.orden)
            for r in reqs])
        return self._data(a, request)
    generar_lista.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def evaluar_item(self, request, pk=None):
        """Marca el resultado de un ítem de la lista de verificación."""
        a = self.get_object()
        try:
            item = ItemVerificacion.objects.get(pk=request.data.get('item_id'), lista__auditoria=a)
        except ItemVerificacion.DoesNotExist:
            return self._error('Ítem no encontrado.')
        res = request.data.get('resultado')
        if res not in ('pendiente', 'cumple', 'no_cumple', 'na', 'observa'):
            return self._error('Resultado no válido.')
        item.resultado = res
        item.evidencia = request.data.get('evidencia', item.evidencia)
        item.observacion = request.data.get('observacion', item.observacion)
        item.save()
        return self._data(a, request)
    evaluar_item.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def registrar_hallazgo(self, request, pk=None):
        """
        Registra un hallazgo de la auditoría: crea un Hallazgo (M8) vinculado,
        con fuente 'auditoria_interna'. Las NC Mayores marcan requiere_ac (M9).
        """
        a = self.get_object()
        if a.estado not in ('en_ejecucion', 'en_informe'):
            return self._error('Los hallazgos se registran durante la ejecución o el informe.')
        tipo = request.data.get('tipo')
        if tipo not in ('nc_mayor', 'nc_menor', 'observacion', 'odm'):
            return self._error('Tipo de hallazgo no válido.')
        descripcion = (request.data.get('descripcion') or '').strip()
        if not descripcion:
            return self._error('La descripción del hallazgo es obligatoria.')
        h = _Hallazgo(
            tipo=tipo, fuente='auditoria_interna',
            proceso=request.data.get('proceso', '') or (a.areas_procesos[:100] or 'Auditoría'),
            descripcion=descripcion,
            requisito=request.data.get('requisito', ''),
            lugar=request.data.get('lugar', ''),
            fecha_deteccion=timezone.now().date(),
            auditoria=a,
            requiere_ac=(tipo == 'nc_mayor'),
        )
        h.save()
        return self._data(a, request)
    registrar_hallazgo.operacion = 'crear'

    @action(detail=True, methods=['post'])
    def generar_informe(self, request, pk=None):
        """En ejecución → En informe. Consolida conclusiones del informe."""
        a = self.get_object()
        if a.estado != 'en_ejecucion':
            return self._error('Solo se genera el informe de una auditoría En ejecución.')
        a.fortalezas = request.data.get('fortalezas', a.fortalezas)
        a.debilidades = request.data.get('debilidades', a.debilidades)
        a.conclusiones = request.data.get('conclusiones', a.conclusiones)
        if not a.fecha_fin:
            a.fecha_fin = timezone.now().date()
        a.estado = 'en_informe'
        a.fecha_informe = timezone.now()
        a.save()
        return self._data(a, request)
    generar_informe.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """En informe → Cerrada. Requiere conclusiones."""
        a = self.get_object()
        if a.estado != 'en_informe':
            return self._error('Solo se cierra una auditoría que ya tiene informe.')
        a.conclusiones = request.data.get('conclusiones', a.conclusiones)
        if not a.conclusiones.strip():
            return self._error('Registre las conclusiones antes de cerrar la auditoría.')
        a.estado = 'cerrada'
        a.save()
        return self._data(a, request)
    cerrar.operacion = 'aprobar'

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        from django.db.models import Count
        qs = Auditoria.objects.filter(is_active=True)
        return Response({
            'por_estado': dict(qs.values_list('estado').annotate(c=Count('id'))),
            'abiertas': qs.exclude(estado='cerrada').count(),
        })
    resumen.operacion = 'leer'


# ============================================================
# M13 — EQUIPOS
# ============================================================
from datetime import timedelta as _timedelta  # noqa: E402

from .models import (  # noqa: E402
    ActividadPrograma, CartaTrazabilidad, Equipo, InformeEquipo, MovimientoEquipo,
    NodoTrazabilidad, PuntoIntervalo, RegistroEquipo, ResultadoIntervalo,
    SolicitudCambioEquipo, calcular_intervalo_punto,
)
from .serializers import (  # noqa: E402
    CartaTrazabilidadSerializer, EquipoListaSerializer, EquipoSerializer,
    InformeEquipoSerializer, NodoTrazabilidadSerializer, PuntoIntervaloSerializer,
    ResultadoIntervaloSerializer, SolicitudCambioEquipoSerializer,
)


def _puede_aprobar_equipos(request):
    """True si el usuario puede aprobar cambios del módulo Equipos."""
    return request.user.tiene_permiso('equipos', 'aprobar')


def _crear_solicitud_equipo(request, *, entidad, operacion, equipo=None,
                            entidad_id=None, payload=None, archivo=None, resumen=''):
    """
    Registra un cambio pendiente de aprobación y responde 202. Lo usan los puntos
    de guardado (alta/baja, bitácoras, intervalo, nodos) cuando el usuario no tiene
    permiso de aprobar.
    """
    sol = SolicitudCambioEquipo(
        equipo=equipo, entidad=entidad, operacion=operacion, entidad_id=entidad_id,
        payload=payload or {}, resumen=resumen, created_by=request.user)
    if archivo:
        sol.archivo = archivo
    sol.save()
    return Response(
        {'pendiente': True,
         'detail': 'El cambio quedó registrado y pendiente de aprobación por un supervisor.'},
        status=status.HTTP_202_ACCEPTED)


def aplicar_matriz_intervalo(eq_id, celdas, usuario):
    """
    Sincroniza la matriz de intervalo de calibración (años × puntos): upsert de las
    celdas con datos y borrado de las que vienen vacías. Compartido por el guardado
    directo y por la aprobación de una solicitud.
    """
    puntos_validos = set(PuntoIntervalo.objects.filter(
        equipo_id=eq_id, is_active=True).values_list('id', flat=True))
    entrantes = {}
    for c in (celdas or []):
        try:
            pid = int(c.get('punto')); anio = int(c.get('anio'))
        except (TypeError, ValueError):
            continue
        if pid not in puntos_validos or anio <= 0:
            continue
        entrantes[(pid, anio)] = {
            'resultado': float(c.get('resultado') or 0),
            'incertidumbre': float(c.get('incertidumbre') or 0),
            'emp': float(c.get('emp') or 0),
        }
    existentes = {(r.punto_id, r.anio): r for r in
                  ResultadoIntervalo.objects.filter(punto_id__in=puntos_validos)}
    a_borrar = [r.id for k, r in existentes.items() if k not in entrantes]
    if a_borrar:
        ResultadoIntervalo.objects.filter(id__in=a_borrar).delete()
    for (pid, anio), vals in entrantes.items():
        r = existentes.get((pid, anio))
        if r:
            r.resultado = vals['resultado']; r.incertidumbre = vals['incertidumbre']
            r.emp = vals['emp']; r.updated_by = usuario
            r.save()
        else:
            ResultadoIntervalo.objects.create(
                punto_id=pid, anio=anio,
                created_by=usuario, updated_by=usuario, **vals)


class EquipoViewSet(viewsets.ModelViewSet):
    """M13 — Equipos del laboratorio (hoja de vida + inventario)."""
    queryset = Equipo.objects.all().prefetch_related(
        'actividades', 'movimientos', 'informes', 'registros')
    permission_classes = [PermisoModular]
    modulo = 'equipos'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        return EquipoListaSerializer if self.action == 'list' else EquipoSerializer

    @staticmethod
    def _es_si(v, d=False):
        if v is None:
            return d
        return str(v).strip().lower() in ('1', 'true', 'si', 'sí', 'yes', 'on')

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if self.action == 'list':
            if p.get('incluir_inactivos') != '1':
                qs = qs.filter(is_active=True)
            for campo in ('magnitud', 'clasificacion', 'estado'):
                if p.get(campo):
                    qs = qs.filter(**{campo: p[campo]})
            if p.get('laboratorio'):
                qs = qs.filter(laboratorio__icontains=p['laboratorio'])
            if p.get('vencidos') == '1':
                qs = qs.filter(requiere_calibracion=True,
                               fecha_proxima_calibracion__lt=timezone.now().date())
            if p.get('por_vencer'):
                try:
                    dias = int(p['por_vencer'])
                except ValueError:
                    dias = 30
                hoy = timezone.now().date()
                qs = qs.filter(requiere_calibracion=True,
                               fecha_proxima_calibracion__gte=hoy,
                               fecha_proxima_calibracion__lte=hoy + _timedelta(days=dias))
            if p.get('buscar'):
                from django.db.models import Q
                b = p['buscar']
                qs = qs.filter(Q(codigo__icontains=b) | Q(nombre__icontains=b) |
                               Q(marca__icontains=b) | Q(serie__icontains=b))
        return qs

    def destroy(self, request, *args, **kwargs):
        eq = self.get_object(); eq.is_active = False; eq.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """
        Control de cambios: si el usuario no tiene permiso de aprobar en el
        módulo, la edición no se aplica de inmediato — se guarda como una
        solicitud pendiente que un supervisor debe aprobar. Quien sí puede
        aprobar aplica el cambio directamente.
        """
        if not request.user.tiene_permiso('equipos', 'aprobar'):
            return self._solicitar_edicion(request)
        return super().update(request, *args, **kwargs)

    def _solicitar_edicion(self, request):
        eq = self.get_object()
        # Validar lo propuesto (sin guardar) para rechazar entradas inválidas
        ser = self.get_serializer(eq, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        payload = {k: request.data.get(k) for k in request.data.keys() if k not in request.FILES}
        sol = SolicitudCambioEquipo(
            equipo=eq, entidad='equipo', operacion='editar', entidad_id=eq.pk,
            payload=payload, resumen=f'Edición de la ficha de {eq.codigo} — {eq.nombre}',
            created_by=request.user,
        )
        if 'imagen' in request.FILES:
            sol.archivo = request.FILES['imagen']
        sol.save()
        return Response(
            {'pendiente': True,
             'detail': 'El cambio quedó registrado y pendiente de aprobación por un supervisor.'},
            status=status.HTTP_202_ACCEPTED)

    def _error(self, msg):
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

    def _data(self, eq, request):
        eq = (Equipo.objects.prefetch_related(
            'actividades', 'movimientos', 'informes', 'registros').get(pk=eq.pk))
        return Response(EquipoSerializer(eq, context={'request': request}).data)

    def create(self, request, *args, **kwargs):
        """
        Alta de equipo. Si en el alta se ingresa la calibración inicial
        (n° certificado, fecha de última calibración y/o periodicidad), se
        siembra el primer registro en la pestaña Calibraciones y se calcula
        la próxima calibración (regla "patrón vigente").
        """
        # Control de cambios: sin permiso de aprobar, el alta queda pendiente.
        if not _puede_aprobar_equipos(request):
            ser_v = self.get_serializer(data=request.data)
            ser_v.is_valid(raise_exception=True)
            payload = {k: v for k, v in request.data.items() if k != 'imagen'}
            return _crear_solicitud_equipo(
                request, entidad='equipo', operacion='crear',
                payload=payload, archivo=request.FILES.get('imagen'),
                resumen=f'Alta de equipo {request.data.get("codigo", "")} — {request.data.get("nombre", "")}')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        eq = serializer.instance

        fecha_ult = request.data.get('fecha_ultima_calibracion') or None
        n_cert = request.data.get('n_certificado') or ''
        if fecha_ult or n_cert:
            from datetime import date as _date
            def _parse(v):
                return _date.fromisoformat(v) if isinstance(v, str) and v else (v or None)
            fult = _parse(fecha_ult)
            prox = _parse(request.data.get('fecha_proxima_calibracion'))
            if not prox and fult and eq.periodicidad_dias:
                prox = fult + _timedelta(days=eq.periodicidad_dias)
            RegistroEquipo.objects.create(
                equipo=eq, tipo='calibracion',
                numero_documento=n_cert,
                frecuencia=(f'{eq.periodicidad_dias} días' if eq.periodicidad_dias else ''),
                fecha=fult, fecha_proxima=prox,
            )
            eq.actualizar_calibracion()

        headers = self.get_success_headers(serializer.data)
        return Response(self._data(eq, request).data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def registrar_calibracion(self, request, pk=None):
        """Registra la calibración: certificado, fecha y próxima (regla patrón vigente)."""
        eq = self.get_object()
        eq.n_certificado = request.data.get('n_certificado', eq.n_certificado)
        if request.data.get('fecha_ultima_calibracion'):
            eq.fecha_ultima_calibracion = request.data['fecha_ultima_calibracion']
        if request.data.get('periodicidad_dias'):
            try:
                eq.periodicidad_dias = int(request.data['periodicidad_dias'])
            except ValueError:
                pass
        if request.data.get('fecha_proxima_calibracion'):
            eq.fecha_proxima_calibracion = request.data['fecha_proxima_calibracion']
        elif eq.fecha_ultima_calibracion and eq.periodicidad_dias:
            base = eq.fecha_ultima_calibracion
            if isinstance(base, str):
                from datetime import date as _date
                base = _date.fromisoformat(base)
            eq.fecha_proxima_calibracion = base + _timedelta(days=eq.periodicidad_dias)
        if request.FILES.get('certificado'):
            eq.certificado = request.FILES['certificado']
        if eq.estado in ('operativo', 'calibrado'):
            eq.estado = 'calibrado'
        eq.save()
        return self._data(eq, request)
    registrar_calibracion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def agregar_registro(self, request, pk=None):
        """
        Agrega una fila a una pestaña de la Hoja de Vida (calibración,
        mantenimiento, verificación, comprobación intermedia, caracterización
        o historial de sucesos). Si es calibración, recalcula la próxima
        calibración del equipo (regla "patrón vigente").
        """
        eq = self.get_object()
        tipo = request.data.get('tipo')
        if tipo not in dict(RegistroEquipo._meta.get_field('tipo').choices):
            return self._error('Tipo de registro no válido.')
        # El documento adjunto es obligatorio en mantenimientos, calibraciones,
        # verificaciones, comprobaciones intermedias y caracterizaciones (no en el historial).
        if tipo != 'suceso' and 'archivo' not in request.FILES:
            return self._error('El documento adjunto es obligatorio para este registro.')
        # Control de cambios: sin permiso de aprobar, el registro queda pendiente.
        if not _puede_aprobar_equipos(request):
            payload = {
                'tipo': tipo, 'frecuencia': request.data.get('frecuencia', ''),
                'numero_documento': request.data.get('numero_documento', ''),
                'descripcion': request.data.get('descripcion', ''),
                'observaciones': request.data.get('observaciones', ''),
                'vb': request.data.get('vb', ''),
                'fecha': request.data.get('fecha') or None,
                'fecha_proxima': request.data.get('fecha_proxima') or None,
            }
            return _crear_solicitud_equipo(
                request, entidad='registro', operacion='crear', equipo=eq,
                payload=payload, archivo=request.FILES.get('archivo'),
                resumen=f'Bitácora ({tipo}) de {eq.codigo} — {eq.nombre}')
        reg = RegistroEquipo(
            equipo=eq, tipo=tipo,
            frecuencia=request.data.get('frecuencia', ''),
            numero_documento=request.data.get('numero_documento', ''),
            descripcion=request.data.get('descripcion', ''),
            observaciones=request.data.get('observaciones', ''),
            vb=request.data.get('vb', ''),
        )
        if request.data.get('fecha'):
            reg.fecha = request.data['fecha']
        if request.data.get('fecha_proxima'):
            reg.fecha_proxima = request.data['fecha_proxima']
        if request.FILES.get('archivo'):
            reg.archivo = request.FILES['archivo']
        reg.save()
        if tipo == 'calibracion':
            eq.actualizar_calibracion()
        return self._data(eq, request)
    agregar_registro.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def eliminar_registro(self, request, pk=None):
        """Elimina una fila de la Hoja de Vida (registro físico, queda en el log)."""
        eq = self.get_object()
        try:
            reg = eq.registros.get(pk=request.data.get('registro_id'))
        except (RegistroEquipo.DoesNotExist, ValueError, TypeError):
            return self._error('Registro no encontrado.')
        era_calibracion = reg.tipo == 'calibracion'
        reg.delete()
        if era_calibracion:
            eq.actualizar_calibracion()
        return self._data(eq, request)
    eliminar_registro.operacion = 'eliminar'

    @action(detail=True, methods=['post'])
    def marcar_inoperativo(self, request, pk=None):
        """Fuera de servicio: aísla el equipo. Levantar trabajo no conforme aparte."""
        eq = self.get_object()
        eq.estado = 'inoperativo'
        eq.motivo_inoperativo = request.data.get('motivo', '')
        eq.fecha_fuera_servicio = timezone.now().date()
        eq.save()
        return self._data(eq, request)
    marcar_inoperativo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def reactivar(self, request, pk=None):
        eq = self.get_object()
        eq.estado = 'operativo'
        eq.motivo_inoperativo = ''
        eq.fecha_fuera_servicio = None
        eq.save()
        return self._data(eq, request)
    reactivar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def dar_baja(self, request, pk=None):
        eq = self.get_object()
        if not _puede_aprobar_equipos(request):
            return _crear_solicitud_equipo(
                request, entidad='equipo', operacion='baja', equipo=eq,
                resumen=f'Dar de baja {eq.codigo} — {eq.nombre}')
        eq.estado = 'baja'
        eq.save()
        return self._data(eq, request)
    dar_baja.operacion = 'eliminar'

    @action(detail=False, methods=['get'])
    def inventario_pdf(self, request):
        """PDF horizontal del Inventario de Equipos; respeta los filtros."""
        p = request.query_params
        qs = Equipo.objects.all()
        if p.get('incluir_inactivos') != '1':
            qs = qs.filter(is_active=True)
        for campo in ('magnitud', 'clasificacion', 'estado'):
            if p.get(campo):
                qs = qs.filter(**{campo: p[campo]})
        if p.get('laboratorio'):
            qs = qs.filter(laboratorio__icontains=p['laboratorio'])
        if p.get('vencidos') == '1':
            qs = qs.filter(requiere_calibracion=True, fecha_proxima_calibracion__lt=timezone.now().date())
        if p.get('buscar'):
            from django.db.models import Q
            b = p['buscar']
            qs = qs.filter(Q(codigo__icontains=b) | Q(nombre__icontains=b) | Q(marca__icontains=b) | Q(serie__icontains=b))
        qs = qs.order_by('codigo')
        lab = p.get('laboratorio') or p.get('magnitud') or ''
        from .ficha_pdf import generar_inventario_pdf
        pdf = generar_inventario_pdf(list(qs), lab)
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = 'inline; filename="Inventario de Equipos.pdf"'
        return resp
    inventario_pdf.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def laboratorios(self, request):
        """Laboratorios (ubicaciones) presentes en los equipos, para el filtro de inventario."""
        labs = (Equipo.objects.exclude(laboratorio='')
                .values_list('laboratorio', flat=True).distinct())
        return Response(sorted(set(labs)))
    laboratorios.operacion = 'leer'

    @action(detail=True, methods=['post'])
    def agregar_actividad(self, request, pk=None):
        """Programa anual: actividad (tipo, año, frecuencia, meses)."""
        eq = self.get_object()
        tipo = request.data.get('tipo')
        if tipo not in dict(ActividadPrograma._meta.get_field('tipo').choices):
            return self._error('Tipo de actividad no válido.')
        meses = request.data.get('meses', [])
        if isinstance(meses, str):
            import json as _json
            try:
                meses = _json.loads(meses)
            except ValueError:
                meses = []
        ActividadPrograma.objects.create(
            equipo=eq, tipo=tipo, anio=int(request.data.get('anio') or timezone.now().year),
            frecuencia=request.data.get('frecuencia', ''), meses=meses)
        return self._data(eq, request)
    agregar_actividad.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def programar(self, request, pk=None):
        """Programa Anual: upsert de una actividad (equipo+tipo+año) con frecuencia y meses."""
        eq = self.get_object()
        tipo = request.data.get('tipo')
        if tipo not in dict(ActividadPrograma._meta.get_field('tipo').choices):
            return self._error('Tipo de actividad no válido.')
        anio = int(request.data.get('anio') or timezone.now().year)
        meses = request.data.get('meses', [])
        if isinstance(meses, str):
            import json as _json
            try:
                meses = _json.loads(meses)
            except ValueError:
                meses = []
        meses = [int(m) for m in meses if str(m).isdigit() and 1 <= int(m) <= 12]
        frecuencia = (request.data.get('frecuencia') or '').strip()
        if not meses and not frecuencia:
            ActividadPrograma.objects.filter(equipo=eq, tipo=tipo, anio=anio).delete()
        else:
            ActividadPrograma.objects.update_or_create(
                equipo=eq, tipo=tipo, anio=anio,
                defaults={'frecuencia': frecuencia, 'meses': meses})
        return Response({'ok': True})
    programar.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def programa(self, request):
        """Programa Anual consolidado: equipos (de un laboratorio) con sus actividades del año."""
        anio = int(request.query_params.get('anio') or timezone.now().year)
        lab = request.query_params.get('laboratorio', '')
        # El equipamiento auxiliar no entra al programa anual (solo patrones y equipos de medición)
        qs = Equipo.objects.filter(is_active=True).exclude(clasificacion__icontains='auxiliar')
        if lab:
            qs = qs.filter(laboratorio__icontains=lab)
        qs = qs.order_by('codigo').prefetch_related('actividades')
        data = []
        for e in qs:
            acts = {a.tipo: {'frecuencia': a.frecuencia, 'meses': a.meses or []}
                    for a in e.actividades.all() if a.anio == anio}
            data.append({
                'id': e.id, 'codigo': e.codigo, 'nombre': e.nombre, 'cantidad': e.cantidad,
                'clase_exactitud': e.clase_exactitud, 'marca': e.marca, 'modelo': e.modelo,
                'serie': e.serie, 'actividades': acts,
            })
        return Response({'anio': anio, 'laboratorio': lab, 'equipos': data})
    programa.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def programa_pdf(self, request):
        """PDF del Programa Anual por año y laboratorio."""
        anio = int(request.query_params.get('anio') or timezone.now().year)
        lab = request.query_params.get('laboratorio', '')
        # El equipamiento auxiliar no entra al programa anual (solo patrones y equipos de medición)
        qs = Equipo.objects.filter(is_active=True).exclude(clasificacion__icontains='auxiliar')
        if lab:
            qs = qs.filter(laboratorio__icontains=lab)
        qs = qs.order_by('codigo').prefetch_related('actividades')
        data = []
        for e in qs:
            acts = {a.tipo: {'frecuencia': a.frecuencia, 'meses': a.meses or []}
                    for a in e.actividades.all() if a.anio == anio}
            data.append({'nombre': e.nombre, 'codigo': e.codigo, 'cantidad': e.cantidad,
                         'clase_exactitud': e.clase_exactitud, 'marca': e.marca, 'modelo': e.modelo,
                         'serie': e.serie, 'actividades': acts})
        from .ficha_pdf import generar_programa_pdf
        pdf = generar_programa_pdf(data, anio, lab)
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="Programa Anual {anio}.pdf"'
        return resp
    programa_pdf.operacion = 'leer'

    @action(detail=True, methods=['post'])
    def registrar_movimiento(self, request, pk=None):
        """Salida del equipo."""
        eq = self.get_object()
        motivo = request.data.get('motivo')
        if motivo not in dict(MovimientoEquipo._meta.get_field('motivo').choices):
            return self._error('Motivo no válido.')
        MovimientoEquipo.objects.create(
            equipo=eq, motivo=motivo,
            destino=request.data.get('destino', ''),
            solicitante=request.data.get('solicitante', ''),
            estado_salida=request.data.get('estado_salida', ''),
            responsable_salida=request.data.get('responsable_salida', ''),
            fecha_salida=timezone.now(),
            observaciones=request.data.get('observaciones', ''))
        return self._data(eq, request)
    registrar_movimiento.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def registrar_retorno(self, request, pk=None):
        """Retorno del equipo: cierra un movimiento abierto."""
        eq = self.get_object()
        try:
            mov = eq.movimientos.get(pk=request.data.get('movimiento_id'))
        except (MovimientoEquipo.DoesNotExist, ValueError, TypeError):
            return self._error('Movimiento no encontrado.')
        mov.fecha_retorno = timezone.now()
        mov.estado_retorno = request.data.get('estado_retorno', mov.estado_retorno)
        mov.responsable_retorno = request.data.get('responsable_retorno', '')
        if request.data.get('observaciones'):
            mov.observaciones = request.data['observaciones']
        mov.save()
        return self._data(eq, request)
    registrar_retorno.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def registrar_informe(self, request, pk=None):
        """Informe de mantenimiento / comprobación / caracterización con archivo adjunto."""
        eq = self.get_object()
        tipo = request.data.get('tipo')
        if tipo not in dict(InformeEquipo._meta.get_field('tipo').choices):
            return self._error('Tipo de informe no válido.')
        inf = InformeEquipo(
            equipo=eq, tipo=tipo,
            solicitante=request.data.get('solicitante', ''),
            lugar=request.data.get('lugar', ''),
            detalle=request.data.get('detalle', ''),
            conclusiones=request.data.get('conclusiones', ''),
            responsable=request.data.get('responsable', ''),
        )
        if request.data.get('fecha_revision'):
            inf.fecha_revision = request.data['fecha_revision']
        if request.data.get('fecha_emision'):
            inf.fecha_emision = request.data['fecha_emision']
        if 'conforme' in request.data:
            inf.conforme = self._es_si(request.data.get('conforme'), None)
        if request.FILES.get('archivo'):
            inf.archivo = request.FILES['archivo']
        inf.save()
        data = self._data(eq, request).data
        return Response({**data, 'informe_creado': inf.numero}, status=status.HTTP_201_CREATED)
    registrar_informe.operacion = 'crear'

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        from django.db.models import Count
        qs = Equipo.objects.filter(is_active=True)
        hoy = timezone.now().date()
        return Response({
            'por_estado': dict(qs.values_list('estado').annotate(c=Count('id'))),
            'vencidos': qs.filter(requiere_calibracion=True,
                                  fecha_proxima_calibracion__lt=hoy).count(),
            'por_vencer_30': qs.filter(requiere_calibracion=True,
                                       fecha_proxima_calibracion__gte=hoy,
                                       fecha_proxima_calibracion__lte=hoy + _timedelta(days=30)).count(),
        })
    resumen.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def ficha_pdf(self, request, pk=None):
        """Genera el PDF de la Ficha Técnica (Hoja de Vida — página 1)."""
        eq = self.get_object()
        from .ficha_pdf import generar_ficha_pdf
        pdf = generar_ficha_pdf(eq)
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="Hoja de Vida {eq.codigo}.pdf"'
        return resp
    ficha_pdf.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def bitacora_pdf(self, request, pk=None):
        """PDF de una bitácora (mantenimientos, calibraciones, etc.) según ?tipo=."""
        eq = self.get_object()
        tipo = request.query_params.get('tipo', '')
        titulo = request.query_params.get('titulo', '')
        from .ficha_pdf import generar_bitacora_pdf
        registros = list(eq.registros.filter(tipo=tipo).order_by('fecha', 'id')) if tipo else []
        pdf = generar_bitacora_pdf(eq, tipo, titulo, registros)
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{(titulo or tipo)} {eq.codigo}.pdf"'
        return resp
    bitacora_pdf.operacion = 'leer'


class CartaTrazabilidadViewSet(viewsets.ModelViewSet):
    """Cartas de trazabilidad por magnitud."""
    queryset = CartaTrazabilidad.objects.all()
    serializer_class = CartaTrazabilidadSerializer
    permission_classes = [PermisoModular]
    modulo = 'equipos'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == 'list' and self.request.query_params.get('incluir_inactivos') != '1':
            qs = qs.filter(is_active=True)
        if self.request.query_params.get('magnitud'):
            qs = qs.filter(magnitud=self.request.query_params['magnitud'])
        return qs

    @action(detail=True, methods=['get'])
    def carta_pdf(self, request, pk=None):
        """PDF del árbol de trazabilidad (diagrama con cajas y conectores)."""
        from django.db.models import Max
        from .ficha_pdf import generar_carta_trazabilidad_pdf
        carta = self.get_object()
        # Fecha de actualización = última modificación de la carta o de cualquiera de sus eslabones
        ult_nodo = carta.nodos.filter(is_active=True).aggregate(m=Max('updated_at'))['m']
        candidatas = [d for d in (carta.updated_at, ult_nodo) if d]
        if candidatas:
            carta.fecha_actualizacion = max(candidatas).date()
        nodos = []
        for n in carta.nodos.filter(is_active=True).order_by('orden', 'id').prefetch_related('padres'):
            nodos.append({
                'id': n.id, 'orden': n.orden, 'nivel': n.nivel,
                'padres': list(n.padres.values_list('id', flat=True)),
                'entidad': n.entidad, 'descripcion': n.descripcion, 'codigo': n.codigo,
                'procedimiento': n.procedimiento, 'certificado': n.certificado,
                'incertidumbre': n.incertidumbre, 'nota': n.nota,
            })
        pdf = generar_carta_trazabilidad_pdf(carta, nodos)
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="carta_trazabilidad_{carta.magnitud or carta.pk}.pdf"'
        return resp
    carta_pdf.operacion = 'leer'

    def destroy(self, request, *args, **kwargs):
        c = self.get_object(); c.is_active = False; c.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NodoTrazabilidadViewSet(viewsets.ModelViewSet):
    """Eslabones (cajas) del árbol de una carta de trazabilidad."""
    queryset = NodoTrazabilidad.objects.select_related('equipo', 'carta')
    serializer_class = NodoTrazabilidadSerializer
    permission_classes = [PermisoModular]
    modulo = 'equipos'

    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        if self.request.query_params.get('carta'):
            qs = qs.filter(carta_id=self.request.query_params['carta'])
        return qs

    def create(self, request, *args, **kwargs):
        # Control de cambios: sin permiso de aprobar, el alta del nodo queda pendiente.
        if not _puede_aprobar_equipos(request):
            ser = self.get_serializer(data=request.data)
            ser.is_valid(raise_exception=True)
            return _crear_solicitud_equipo(
                request, entidad='nodo', operacion='crear',
                payload={k: v for k, v in request.data.items()},
                resumen=f'Nuevo nodo de trazabilidad: {request.data.get("descripcion") or request.data.get("entidad") or ""}')
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not _puede_aprobar_equipos(request):
            nodo = self.get_object()
            ser = self.get_serializer(nodo, data=request.data, partial=kwargs.get('partial', False))
            ser.is_valid(raise_exception=True)
            return _crear_solicitud_equipo(
                request, entidad='nodo', operacion='editar', entidad_id=nodo.pk,
                payload={k: v for k, v in request.data.items()},
                resumen=f'Edición de nodo: {nodo.descripcion or nodo.entidad or nodo.pk}')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        n = self.get_object()
        if not _puede_aprobar_equipos(request):
            return _crear_solicitud_equipo(
                request, entidad='nodo', operacion='eliminar', entidad_id=n.pk,
                resumen=f'Eliminar nodo de trazabilidad: {n.descripcion or n.entidad or n.pk}')
        # Baja lógica: arrastra a los hijos para no dejar nodos huérfanos colgando
        def baja(nodo):
            for h in nodo.hijos.filter(is_active=True):
                baja(h)
            nodo.is_active = False
            nodo.save(update_fields=['is_active', 'updated_at'])
        baja(n)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def rellenar_desde_equipo(self, request, pk=None):
        """Copia al nodo los datos de calibración del equipo enlazado."""
        n = self.get_object()
        if not n.equipo:
            return Response({'detail': 'El nodo no está enlazado a ningún equipo del inventario.'},
                            status=status.HTTP_400_BAD_REQUEST)
        n.rellenar_desde_equipo()
        n.updated_by = request.user
        n.save()
        return Response(NodoTrazabilidadSerializer(n, context={'request': request}).data)
    rellenar_desde_equipo.operacion = 'editar'


from .models import ClasificacionEquipo, MagnitudEquipo  # noqa: E402
from .serializers import (  # noqa: E402
    ClasificacionEquipoSerializer, MagnitudEquipoSerializer,
)


class MagnitudEquipoViewSet(viewsets.ModelViewSet):
    """Catálogo gestionable de magnitudes (módulo Equipos). Renombrar propaga a los equipos."""
    queryset = MagnitudEquipo.objects.all()
    serializer_class = MagnitudEquipoSerializer
    permission_classes = [PermisoModular]
    modulo = 'equipos'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('incluir_inactivos') != '1':
            qs = qs.filter(is_active=True)
        return qs

    def perform_update(self, serializer):
        anterior = serializer.instance.nombre
        obj = serializer.save()
        if obj.nombre != anterior:
            Equipo.objects.filter(magnitud=anterior).update(magnitud=obj.nombre)
            CartaTrazabilidad.objects.filter(magnitud=anterior).update(magnitud=obj.nombre)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object(); obj.is_active = False; obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ClasificacionEquipoViewSet(viewsets.ModelViewSet):
    """Catálogo gestionable de clasificaciones (módulo Equipos). Renombrar propaga a los equipos."""
    queryset = ClasificacionEquipo.objects.all()
    serializer_class = ClasificacionEquipoSerializer
    permission_classes = [PermisoModular]
    modulo = 'equipos'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('incluir_inactivos') != '1':
            qs = qs.filter(is_active=True)
        return qs

    def perform_update(self, serializer):
        anterior = serializer.instance.nombre
        obj = serializer.save()
        if obj.nombre != anterior:
            Equipo.objects.filter(clasificacion=anterior).update(clasificacion=obj.nombre)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object(); obj.is_active = False; obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SolicitudCambioEquipoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Bandeja de control de cambios de equipos: lista las solicitudes (por defecto
    las pendientes) y permite aprobarlas (se aplica el cambio real) o rechazarlas
    (se descarta). Aprobar/rechazar requiere el permiso 'aprobar' del módulo.
    """
    queryset = SolicitudCambioEquipo.objects.select_related('equipo', 'created_by', 'resuelto_por')
    serializer_class = SolicitudCambioEquipoSerializer
    permission_classes = [PermisoModular]
    modulo = 'equipos'

    def get_queryset(self):
        qs = super().get_queryset()
        estado = self.request.query_params.get('estado', 'pendiente')
        if estado and estado != 'todas':
            qs = qs.filter(estado=estado)
        if self.request.query_params.get('equipo'):
            qs = qs.filter(equipo_id=self.request.query_params['equipo'])
        if self.request.query_params.get('mias') == '1':
            qs = qs.filter(created_by=self.request.user)
        return qs

    @action(detail=False, methods=['get'])
    def mis_devueltas_count(self, request):
        """N.° de solicitudes propias devueltas para corrección (distintivo del solicitante)."""
        n = SolicitudCambioEquipo.objects.filter(
            created_by=request.user, estado='devuelta').count()
        return Response({'devueltas': n})
    mis_devueltas_count.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def pendientes_count(self, request):
        """N.° de solicitudes pendientes (para el distintivo del buzón)."""
        return Response({'pendientes': SolicitudCambioEquipo.objects.filter(estado='pendiente').count()})
    pendientes_count.operacion = 'leer'

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        """Aplica el cambio propuesto y marca la solicitud como aprobada."""
        from rest_framework.exceptions import ValidationError
        sol = self.get_object()
        if sol.estado != 'pendiente':
            return self._error('La solicitud ya fue resuelta.')
        try:
            self._aplicar(sol, request)
        except ValidationError as e:
            return Response({'detail': 'No se pudo aplicar el cambio (datos inválidos).',
                             'errores': e.detail}, status=status.HTTP_400_BAD_REQUEST)
        sol.estado = 'aprobada'
        sol.resuelto_por = request.user
        sol.resuelto_at = timezone.now()
        sol.observaciones = request.data.get('observaciones', '') or ''
        sol.save()
        return Response(SolicitudCambioEquipoSerializer(sol, context={'request': request}).data)
    aprobar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        """Descarta el cambio propuesto y marca la solicitud como rechazada."""
        sol = self.get_object()
        if sol.estado != 'pendiente':
            return self._error('La solicitud ya fue resuelta.')
        sol.estado = 'rechazada'
        sol.resuelto_por = request.user
        sol.resuelto_at = timezone.now()
        sol.observaciones = request.data.get('observaciones', '') or ''
        sol.save()
        return Response(SolicitudCambioEquipoSerializer(sol, context={'request': request}).data)
    rechazar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def devolver(self, request, pk=None):
        """Devuelve la solicitud al solicitante para corrección (no se aplica nada)."""
        sol = self.get_object()
        if sol.estado != 'pendiente':
            return self._error('La solicitud ya fue resuelta.')
        sol.estado = 'devuelta'
        sol.resuelto_por = request.user
        sol.resuelto_at = timezone.now()
        sol.observaciones = request.data.get('observaciones', '') or ''
        sol.save()
        return Response(SolicitudCambioEquipoSerializer(sol, context={'request': request}).data)
    devolver.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def reenviar(self, request, pk=None):
        """El solicitante corrige (opcionalmente actualiza el payload) y reenvía a pendiente."""
        sol = self.get_object()
        if sol.created_by_id != request.user.id:
            return self._error('Solo quien creó la solicitud puede reenviarla.')
        if sol.estado != 'devuelta':
            return self._error('Solo se pueden reenviar solicitudes devueltas.')
        nuevo = request.data.get('payload')
        if isinstance(nuevo, dict):
            sol.payload = nuevo
        sol.estado = 'pendiente'
        sol.resuelto_por = None
        sol.resuelto_at = None
        sol.save()
        return Response(SolicitudCambioEquipoSerializer(sol, context={'request': request}).data)
    reenviar.operacion = 'editar'

    def _error(self, msg):
        return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

    def _aplicar(self, sol, request):
        """Ejecuta la operación real según la entidad/operación de la solicitud."""
        import os
        ent, op = sol.entidad, sol.operacion
        pl = sol.payload or {}
        user = request.user

        # --- Equipo: editar ficha ---
        if ent == 'equipo' and op == 'editar':
            eq = sol.equipo
            ser = EquipoSerializer(eq, data=pl, partial=True, context={'request': request})
            ser.is_valid(raise_exception=True)
            ser.save(updated_by=user)
            if sol.archivo:
                eq.imagen.save(os.path.basename(sol.archivo.name), sol.archivo, save=True)
            return

        # --- Equipo: alta ---
        if ent == 'equipo' and op == 'crear':
            ser = EquipoSerializer(data=pl, context={'request': request})
            ser.is_valid(raise_exception=True)
            eq = ser.save(created_by=user, updated_by=user)
            if sol.archivo:
                eq.imagen.save(os.path.basename(sol.archivo.name), sol.archivo, save=True)
            fecha_ult = pl.get('fecha_ultima_calibracion') or None
            n_cert = pl.get('n_certificado') or ''
            if fecha_ult or n_cert:
                from datetime import date as _date
                def _parse(v):
                    return _date.fromisoformat(v) if isinstance(v, str) and v else (v or None)
                fult = _parse(fecha_ult)
                prox = _parse(pl.get('fecha_proxima_calibracion'))
                if not prox and fult and eq.periodicidad_dias:
                    prox = fult + _timedelta(days=eq.periodicidad_dias)
                RegistroEquipo.objects.create(
                    equipo=eq, tipo='calibracion', numero_documento=n_cert,
                    frecuencia=(f'{eq.periodicidad_dias} días' if eq.periodicidad_dias else ''),
                    fecha=fult, fecha_proxima=prox)
                eq.actualizar_calibracion()
            return

        # --- Equipo: dar de baja ---
        if ent == 'equipo' and op == 'baja':
            eq = sol.equipo
            if eq:
                eq.estado = 'baja'; eq.updated_by = user; eq.save()
            return

        # --- Registro de bitácora: crear ---
        if ent == 'registro' and op == 'crear':
            eq = sol.equipo
            reg = RegistroEquipo(
                equipo=eq, tipo=pl.get('tipo', ''),
                frecuencia=pl.get('frecuencia', ''), numero_documento=pl.get('numero_documento', ''),
                descripcion=pl.get('descripcion', ''), observaciones=pl.get('observaciones', ''),
                vb=pl.get('vb', ''), created_by=user, updated_by=user)
            if pl.get('fecha'):
                reg.fecha = pl['fecha']
            if pl.get('fecha_proxima'):
                reg.fecha_proxima = pl['fecha_proxima']
            if sol.archivo:
                reg.archivo = sol.archivo
            reg.save()
            if reg.tipo == 'calibracion':
                eq.actualizar_calibracion()
            return

        # --- Intervalo de calibración: guardar matriz ---
        if ent == 'intervalo':
            aplicar_matriz_intervalo(pl.get('equipo'), pl.get('celdas') or [], user)
            return

        # --- Nodo de trazabilidad ---
        if ent == 'nodo':
            from .models import NodoTrazabilidad
            if op == 'crear':
                ser = NodoTrazabilidadSerializer(data=pl, context={'request': request})
                ser.is_valid(raise_exception=True)
                ser.save(created_by=user, updated_by=user)
            elif op == 'editar':
                nodo = NodoTrazabilidad.objects.filter(pk=sol.entidad_id).first()
                if nodo:
                    ser = NodoTrazabilidadSerializer(nodo, data=pl, partial=True, context={'request': request})
                    ser.is_valid(raise_exception=True)
                    ser.save(updated_by=user)
            elif op == 'eliminar':
                nodo = NodoTrazabilidad.objects.filter(pk=sol.entidad_id).first()
                if nodo:
                    def _baja(n):
                        for h in n.hijos.filter(is_active=True):
                            _baja(h)
                        n.is_active = False
                        n.save(update_fields=['is_active', 'updated_at'])
                    _baja(nodo)
            return


class PuntoIntervaloViewSet(viewsets.ModelViewSet):
    """Puntos nominales para el intervalo de calibración (método OIML D10)."""
    queryset = PuntoIntervalo.objects.all().prefetch_related('resultados')
    serializer_class = PuntoIntervaloSerializer
    permission_classes = [PermisoModular]
    modulo = 'equipos'

    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        if self.request.query_params.get('equipo'):
            qs = qs.filter(equipo_id=self.request.query_params['equipo'])
        return qs.order_by('orden', 'id')

    def destroy(self, request, *args, **kwargs):
        p = self.get_object(); p.is_active = False; p.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Puntos del patrón con su cálculo + el intervalo del patrón (menor periodo)."""
        eq_id = request.query_params.get('equipo')
        if not eq_id:
            return Response({'detail': 'Falta el equipo.'}, status=status.HTTP_400_BAD_REQUEST)
        puntos = PuntoIntervalo.objects.filter(equipo_id=eq_id, is_active=True).order_by('orden', 'id')
        data = PuntoIntervaloSerializer(puntos, many=True, context={'request': request}).data
        periodos = [p['calculo']['periodo'] for p in data if p['calculo']['periodo'] is not None]
        return Response({'puntos': data, 'intervalo_patron': min(periodos) if periodos else None})
    resumen.operacion = 'leer'

    @action(detail=False, methods=['post'])
    def guardar_matriz(self, request):
        """
        Guardado masivo de la matriz (años × puntos). Recibe {equipo, celdas:[{punto,
        anio, resultado, incertidumbre, emp}]}. Hace upsert de las celdas con datos y
        elimina las que ya no vienen (celdas que el usuario dejó en blanco).
        """
        eq_id = request.data.get('equipo')
        celdas = request.data.get('celdas') or []
        if not eq_id:
            return Response({'detail': 'Falta el equipo.'}, status=status.HTTP_400_BAD_REQUEST)
        if not _puede_aprobar_equipos(request):
            eq = Equipo.objects.filter(pk=eq_id).first()
            return _crear_solicitud_equipo(
                request, entidad='intervalo', operacion='editar', equipo=eq,
                payload={'equipo': eq_id, 'celdas': celdas},
                resumen=f'Intervalo de calibración de {eq.codigo if eq else ""} ({len(celdas)} valores)')
        aplicar_matriz_intervalo(eq_id, celdas, request.user)

        puntos = PuntoIntervalo.objects.filter(equipo_id=eq_id, is_active=True).order_by('orden', 'id')
        data = PuntoIntervaloSerializer(puntos, many=True, context={'request': request}).data
        periodos = [p['calculo']['periodo'] for p in data if p['calculo']['periodo'] is not None]
        return Response({'puntos': data, 'intervalo_patron': min(periodos) if periodos else None})
    guardar_matriz.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def intervalo_pdf(self, request):
        """PDF del Intervalo de Calibración (MET-PRO-04-r08) del patrón."""
        from .ficha_pdf import generar_intervalo_pdf
        eq = Equipo.objects.filter(pk=request.query_params.get('equipo')).first()
        if not eq:
            return Response({'detail': 'Equipo no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        puntos = PuntoIntervalo.objects.filter(equipo=eq, is_active=True).order_by('orden', 'id')
        data = PuntoIntervaloSerializer(puntos, many=True, context={'request': request}).data
        pdf = generar_intervalo_pdf(eq, data)
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="intervalo_calibracion_{eq.codigo}.pdf"'
        return resp
    intervalo_pdf.operacion = 'leer'


class ResultadoIntervaloViewSet(viewsets.ModelViewSet):
    """Resultados anuales de un punto de intervalo de calibración."""
    queryset = ResultadoIntervalo.objects.all()
    serializer_class = ResultadoIntervaloSerializer
    permission_classes = [PermisoModular]
    modulo = 'equipos'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('punto'):
            qs = qs.filter(punto_id=self.request.query_params['punto'])
        return qs.order_by('anio', 'id')
