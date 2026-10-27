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
from rest_framework import mixins, status, viewsets
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

    def update(self, request, *args, **kwargs):
        """La edición directa solo cambia el código (corrección); el resto de la ficha se edita con «editar_ficha»,
        que pide contraseña. Un documento archivado no se modifica."""
        doc = self.get_object()
        if doc.archivado:
            return Response({'detail': f'El documento {doc.codigo} está archivado: desarchívelo para volver a '
                                       f'trabajar con él.'}, status=status.HTTP_400_BAD_REQUEST)
        otros = set(request.data.keys()) - {'codigo'}
        if otros:
            return Response({'detail': 'Los datos de la ficha se editan con «Editar ficha» (con contraseña).'},
                            status=status.HTTP_400_BAD_REQUEST)
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

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
        if doc.archivado:
            return Response({'detail': f'El documento {doc.codigo} está archivado: desarchívelo para volver a trabajar con él.'},
                            status=status.HTTP_400_BAD_REQUEST)
        password = request.data.get('password') or ''
        if not password:
            return Response({'detail': 'Debe confirmar con su contraseña para editar.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(password):
            return Response({'detail': 'Contraseña incorrecta. No se guardaron los cambios.'},
                            status=status.HTTP_400_BAD_REQUEST)

        EDITABLES = ('titulo', 'tipo', 'proceso', 'proceso_catalogo', 'objetivo', 'alcance',
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
        resumen = str(request.data.get('resumen_cambios') or '').strip()
        if resumen and request.user.check_password(resumen):
            return Response({'detail': 'El resumen de cambios coincide con su contraseña: no la escriba aquí '
                                       '(quedaría visible en el historial). Redacte el resumen de los cambios.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if doc.archivado:
            return Response({'detail': f'El documento {doc.codigo} está archivado: desarchívelo para volver a trabajar con él.'},
                            status=status.HTTP_400_BAD_REQUEST)
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
        # El archivo cambió: las firmas previas de esta versión ya no aplican (quedan anuladas, no se borran)
        for f in v.firmas.all():
            f.anular('Se reemplazó el archivo de la versión', request.user)
        v.save()
        self._bitacora(v, contenido, nombre, 'correccion')
        return Response(VersionDocumentoSerializer(v, context={'request': request}).data)
    reemplazar_archivo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def enviar_revision(self, request, pk=None):
        """En elaboración → En revisión. La hace quien elabora."""
        doc = self.get_object()
        if doc.archivado:
            return Response({'detail': f'El documento {doc.codigo} está archivado: desarchívelo para volver a trabajar con él.'},
                            status=status.HTTP_400_BAD_REQUEST)
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
        if doc.archivado:
            return Response({'detail': f'El documento {doc.codigo} está archivado: desarchívelo para volver a trabajar con él.'},
                            status=status.HTTP_400_BAD_REQUEST)
        bloqueo = self._solo_interno(doc)
        if bloqueo:
            return bloqueo
        v, err = self._version_o_error(doc, ['en_revision'], 'No hay versión en revisión.')
        if err:
            return err
        firmo_elaborado = v.firmas.filter(rol='elaborado', usuario=request.user).exists()
        if (v.elaborado_por_id == request.user.id or firmo_elaborado) and not request.user.is_superuser:
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
        if doc.archivado:
            return Response({'detail': f'El documento {doc.codigo} está archivado: desarchívelo para volver a trabajar con él.'},
                            status=status.HTTP_400_BAD_REQUEST)
        bloqueo = self._solo_interno(doc)
        if bloqueo:
            return bloqueo
        v, err = self._version_o_error(doc, ['en_aprobacion'], 'No hay versión pendiente de aprobación.')
        if err:
            return err
        if v.firmas.filter(rol='elaborado', usuario=request.user).exists() and not request.user.is_superuser:
            return Response({'detail': 'Quien elaboró la versión no puede aprobarla.'},
                            status=status.HTTP_400_BAD_REQUEST)
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
                    for f in FirmaVersion.objects.filter(version=v, rol='aprobado'):
                        f.anular('No se pudo publicar: archivo editable sin conversión a PDF', request.user)
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
                for f in FirmaVersion.objects.filter(version=v, rol='aprobado'):
                    f.anular('No se pudo publicar: el PDF de la versión no es válido', request.user)
                return Response(
                    {'detail': 'El archivo de esta versión no es un PDF válido o está dañado. '
                               'Reemplácelo con un PDF correcto antes de aprobar.'},
                    status=status.HTTP_400_BAD_REQUEST)

        from django.core.files.base import ContentFile
        # La versión vigente anterior pasa a Obsoleto (se conserva el historial)
        doc.versiones.filter(estado='vigente').update(estado='obsoleto')
        hoy = timezone.localdate()
        v.estado = 'vigente'
        v.aprobado_por = request.user
        v.fecha_aprobacion = timezone.now()
        v.fecha_vigencia = hoy
        v.fecha_proxima_revision = hoy + timedelta(days=doc.meses_revision * 30)
        v.archivo_publicado.save(f'{doc.codigo}_Ver{v.version}_firmado.pdf', ContentFile(pdf_final), save=False)
        v.hash_publicado = hash_sha256(pdf_final)
        v.save()
        # El contenido de la ficha del proceso no cambia solo: su responsable
        # recibe el aviso de revisarla.
        if doc.proceso_catalogo_id:
            from procesos.models import avisar_ficha_por_revisar
            avisar_ficha_por_revisar(doc.proceso_catalogo,
                                     f'Se aprobó la versión {v.version} de {doc.codigo} — {doc.titulo}.',
                                     origen='documento', usuario=request.user)
        return Response(VersionDocumentoSerializer(v, context={'request': request}).data)
    aprobar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def devolver(self, request, pk=None):
        """En aprobación → vuelve a En elaboración para correcciones."""
        doc = self.get_object()
        if doc.archivado:
            return Response({'detail': f'El documento {doc.codigo} está archivado: desarchívelo para volver a trabajar con él.'},
                            status=status.HTTP_400_BAD_REQUEST)
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
        if doc.archivado:
            return Response({'detail': f'El documento {doc.codigo} está archivado: desarchívelo para volver a trabajar con él.'},
                            status=status.HTTP_400_BAD_REQUEST)
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
        resumen = str(request.data.get('resumen_cambios') or '').strip()
        if resumen and request.user.check_password(resumen):
            return Response({'detail': 'El resumen de cambios coincide con su contraseña: no la escriba aquí '
                                       '(quedaría visible en el historial). Redacte el resumen de los cambios.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if doc.archivado:
            return Response({'detail': f'El documento {doc.codigo} está archivado: desarchívelo para volver a trabajar con él.'},
                            status=status.HTTP_400_BAD_REQUEST)
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
                fecha_vigencia=timezone.localdate(),
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
        if doc.archivado:
            return Response({'detail': f'El documento {doc.codigo} está archivado: desarchívelo para volver a trabajar con él.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if doc.origen != 'externo':
            return Response({'detail': 'La verificación de vigencia aplica solo a documentos externos.'},
                            status=status.HTTP_400_BAD_REQUEST)
        verificacion = VerificacionExterna.objects.create(
            documento=doc,
            vigente=self._es_si(request.data.get('vigente'), True),
            observaciones=request.data.get('observaciones', ''),
        )
        doc.ultima_verificacion = timezone.now()
        doc.save()
        return Response(VerificacionExternaSerializer(verificacion).data, status=status.HTTP_201_CREATED)
    verificar_vigencia.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def externos_por_verificar(self, request):
        """Documentos externos cuya verificación de vigencia está pendiente o vencida."""
        ahora = timezone.localtime()
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
        limite = timezone.localdate() + timedelta(days=30)
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
            'vencido': v.fecha_proxima_revision < timezone.localdate(),
        } for v in versiones]
        return Response(data)
    por_vencer.operacion = 'leer'


# ============================================================
# M8 — HALLAZGOS
# ============================================================
from .models import Hallazgo, TIPOS_HALLAZGO as TIPOS_HALLAZGO_CHOICES  # noqa: E402
from .serializers import HallazgoListaSerializer, HallazgoSerializer  # noqa: E402


class HallazgoViewSet(viewsets.ModelViewSet):
    """
    M8 — Hallazgos: registro único de no conformidades, observaciones y
    oportunidades de mejora. Las NC se tratan en una solicitud de acción
    correctiva (nueva o una abierta del mismo problema) y se cierran cuando esa
    solicitud se cierra. Las observaciones y oportunidades de mejora se derivan
    a Riesgos y Oportunidades.
    """
    queryset = Hallazgo.objects.all().select_related('responsable', 'cerrado_por', 'created_by', 'sac__responsable')
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
        if p.get('abiertos') == '1':
            qs = qs.exclude(estado='cerrado')
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

    def _error(self, mensaje):
        return Response({'detail': mensaje}, status=status.HTTP_400_BAD_REQUEST)

    def _data(self, h, request, codigo=status.HTTP_200_OK):
        return Response(HallazgoSerializer(h, context={'request': request}).data, status=codigo)

    def update(self, request, *args, **kwargs):
        """Corregir el registro solo mientras su etapa esté abierta. El tipo no
        se cambia aquí: se reclasifica con motivo."""
        h = self.get_object()
        if 'tipo' in request.data and request.data.get('tipo') != h.tipo:
            return self._error('El tipo no se edita: use «Reclasificar» e indique el motivo.')
        if not h.registro_abierto():
            cambiados = [c for c in Hallazgo.CAMPOS_REGISTRO if c in request.data]
            return self._error(h.mensaje_registro_cerrado(cambiados[0] if cambiados else ''))
        return super().update(request, *args, **kwargs)

    @staticmethod
    def _auditoria_pendiente(h):
        """Un hallazgo de auditoría se trata después de comunicarse en la
        reunión de cierre; antes aún puede reclasificarse o descartarse."""
        a = h.auditoria
        if a and a.estado not in ('en_informe', 'cerrada'):
            return (f'El hallazgo aún está en consolidación en la auditoría {a.codigo}: se deriva '
                    f'después de la reunión de cierre.')
        return ''

    @action(detail=True, methods=['post'])
    def reclasificar(self, request, pk=None):
        """Cambia el tipo de un hallazgo registrado a mano, con motivo. Si cambia
        de prefijo toma un código nuevo; el anterior queda en el historial."""
        h = self.get_object()
        if h.auditoria_id:
            return self._error(h.mensaje_registro_cerrado())
        if not h.registro_abierto():
            return self._error(h.mensaje_registro_cerrado())
        tipo = request.data.get('tipo')
        if tipo not in dict(TIPOS_HALLAZGO_CHOICES):
            return self._error('Tipo de hallazgo no válido.')
        if tipo == h.tipo:
            return self._error('El hallazgo ya tiene ese tipo.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la reclasificación.')
        from .models import PREFIJOS_HALLAZGO
        anterior = h.codigo
        if PREFIJOS_HALLAZGO.get(tipo) != PREFIJOS_HALLAZGO.get(h.tipo):
            h.codigo = Hallazgo.generar_codigo(tipo, h.anio_codigo())
        h.reclasificaciones = list(h.reclasificaciones or []) + [{
            'fecha': timezone.localtime().isoformat(timespec='minutes'),
            'usuario': request.user.get_full_name() or request.user.username,
            'de': h.get_tipo_display(), 'a': dict(TIPOS_HALLAZGO_CHOICES)[tipo],
            'codigo_anterior': anterior, 'motivo': motivo,
        }]
        h.tipo = tipo
        h.save()
        return self._data(h, request)
    reclasificar.operacion = 'editar'

    def _validar_derivacion(self, h):
        if not h.es_nc:
            return ('Solo las No Conformidades se tratan con una solicitud de acción correctiva; '
                    'las observaciones y oportunidades de mejora se derivan a Riesgos y Oportunidades.')
        if h.sac_id:
            return f'Este hallazgo ya se trata en la {h.sac.codigo}.'
        if h.estado == 'cerrado':
            return 'El hallazgo está cerrado.'
        return self._auditoria_pendiente(h)

    @action(detail=True, methods=['post'])
    def generar_sac(self, request, pk=None):
        """Registra la NC en una solicitud de acción correctiva nueva, precargada
        con su procedencia, descripción y requisito."""
        h = self.get_object()
        err = self._validar_derivacion(h)
        if err:
            return self._error(err)
        from .models import SolicitudAC
        fuentes_sac = {'auditoria_interna', 'auditoria_externa', 'revision_direccion', 'queja'}
        sac = SolicitudAC.objects.create(
            hallazgo=h,
            fuente=h.fuente if h.fuente in fuentes_sac else 'otros',
            fuente_detalle='' if h.fuente in fuentes_sac else h.get_fuente_display(),
            normas_aplicables=normas_de_sac(getattr(h.auditoria, 'normas_aplicables', None)),
            descripcion_nc=h.descripcion,
            requisito_auditado=h.requisito,
        )
        h.sac = sac
        h.estado = 'en_tratamiento'
        h.save()
        resp = self._data(h, request, status.HTTP_201_CREATED)
        resp.data['sac_creada'] = sac.codigo
        return resp
    generar_sac.operacion = 'crear'

    @action(detail=True, methods=['post'])
    def vincular_sac(self, request, pk=None):
        """Suma la NC, como nueva ocurrencia, a una solicitud de acción
        correctiva abierta sobre el mismo problema (no se duplican solicitudes)."""
        h = self.get_object()
        err = self._validar_derivacion(h)
        if err:
            return self._error(err)
        from .models import SolicitudAC
        sac = SolicitudAC.objects.filter(pk=request.data.get('sac_id'), is_active=True).first()
        if not sac:
            return self._error('Solicitud de acción correctiva no encontrada.')
        if sac.estado in ('cerrada_conforme', 'cerrada_sin_ac'):
            return self._error(f'La {sac.codigo} está cerrada; genere una solicitud nueva.')
        h.sac = sac
        h.estado = 'en_tratamiento'
        h.save()
        return self._data(h, request)
    vincular_sac.operacion = 'editar'

    @action(detail=True, methods=['get'])
    def sac_abiertas(self, request, pk=None):
        """Solicitudes abiertas a las que puede sumarse esta NC; primero las del
        mismo requisito o proceso, para detectar duplicados."""
        from .models import SolicitudAC
        h = self.get_object()
        qs = (SolicitudAC.objects.filter(is_active=True)
              .exclude(estado__in=('cerrada_conforme', 'cerrada_sin_ac')).order_by('-id'))
        req = (h.requisito or '').strip().lower()
        proc = (h.proceso or '').strip().lower()

        def afin(s):
            texto = f'{s.requisito_auditado} {s.descripcion_nc}'.lower()
            return bool((req and req in texto) or (proc and proc in texto))
        datos = [{'id': s.id, 'codigo': s.codigo, 'estado_display': s.get_estado_display(),
                  'descripcion': (s.descripcion_nc or '')[:160], 'requisito': s.requisito_auditado,
                  'similar': afin(s)} for s in qs]
        datos.sort(key=lambda d: not d['similar'])
        return Response(datos)
    sac_abiertas.operacion = 'leer'

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
    Registrada → evaluar → En análisis → aprobar_plan
    → En implementación → En verificación → verificar_eficacia
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
        """Desactiva una solicitud registrada por error. Solo antes del análisis de causa; la No Conformidad que
        trataba vuelve a «registrado» para poder tratarse en otra solicitud."""
        sac = self.get_object()
        if sac.estado != 'registrada':
            return Response({'detail': 'La solicitud ya avanzó del registro: no se desactiva; ciérrela según su '
                                       'flujo.'}, status=status.HTTP_400_BAD_REQUEST)
        sac.is_active = False
        sac.save()
        from .models import Hallazgo
        for h in Hallazgo.objects.filter(sac=sac):
            h.sac = None
            if h.estado == 'en_tratamiento':
                h.estado = 'registrado'
            h.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    _FUENTE_HALLAZGO = {'auditoria_interna': 'auditoria_interna', 'auditoria_externa': 'auditoria_externa',
                        'revision_direccion': 'revision_direccion', 'queja': 'queja', 'otros': 'otro'}

    def create(self, request, *args, **kwargs):
        """Registra la solicitud. Toda SAC trata una No Conformidad del registro
        de hallazgos: la elegida (si aún no se trata en otra solicitud) o una
        que se crea aquí mismo con su clasificación (NC mayor o menor)."""
        datos = request.data
        hallazgo_id = datos.get('hallazgo') or None
        if hallazgo_id:
            h = Hallazgo.objects.filter(pk=hallazgo_id, is_active=True).first()
            if not h:
                return self._error('Hallazgo no encontrado.')
            if not h.es_nc:
                return self._error('Solo las No Conformidades se tratan con una solicitud de acción correctiva.')
            if h.sac_id:
                return self._error(f'El hallazgo {h.codigo} ya se trata en la {h.sac.codigo}.')
            if h.auditoria_id and h.auditoria.estado not in ('en_informe', 'cerrada'):
                return self._error(f'{h.codigo} aún está en consolidación en la auditoría {h.auditoria.codigo}.')
        else:
            tipo_nc = datos.get('tipo_nc')
            if tipo_nc not in ('nc_mayor', 'nc_menor'):
                return self._error('Indique la clasificación de la No Conformidad (NC mayor o NC menor).')
            if not (datos.get('proceso') or '').strip():
                return self._error('Indique el proceso afectado por la No Conformidad.')
        if hallazgo_id:
            # La solicitud hereda la descripción y el requisito de la NC si no se indican.
            datos = {k: datos.get(k) for k in datos.keys()}
            if hasattr(request.data, 'getlist') and 'normas_aplicables' in request.data:
                datos['normas_aplicables'] = request.data.getlist('normas_aplicables')
            datos['descripcion_nc'] = (datos.get('descripcion_nc') or '').strip() or h.descripcion
            datos['requisito_auditado'] = (datos.get('requisito_auditado') or '').strip() or h.requisito
        ser = self.get_serializer(data=datos)
        ser.is_valid(raise_exception=True)
        if not hallazgo_id:
            h = Hallazgo.objects.create(
                tipo=datos['tipo_nc'], fuente=self._FUENTE_HALLAZGO.get(ser.validated_data.get('fuente'), 'otro'),
                proceso=datos['proceso'].strip(), descripcion=ser.validated_data.get('descripcion_nc', ''),
                requisito=ser.validated_data.get('requisito_auditado', ''),
                lugar=(datos.get('lugar') or '').strip(),
                fecha_deteccion=(datos.get('fecha_deteccion') or ser.validated_data.get('fecha_registro')
                                 or timezone.localdate()),
                responsable=ser.validated_data.get('responsable'), created_by=request.user)
        sac = ser.save(hallazgo=h)
        h.sac = sac
        h.estado = 'en_tratamiento'
        h.save()
        return Response(SolicitudACSerializer(sac, context={'request': request}).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """El registro (procedencia y descripción de la NC) se corrige solo
        mientras la solicitud está Registrada."""
        sac = self.get_object()
        if 'hallazgo' in request.data and str(request.data.get('hallazgo') or '') != str(sac.hallazgo_id or ''):
            return self._error('La NC de origen no se cambia; para otra ocurrencia use «Sumar a SAC abierta» en Hallazgos.')
        if 'registro' not in sac.etapas_abiertas():
            campos = [c for c in SolicitudAC.CAMPOS_REGISTRO if c in request.data]
            if campos:
                nombre = SolicitudAC._meta.get_field(campos[0]).verbose_name
                return self._error(f'La etapa de registro está cerrada ({sac.get_estado_display().lower()}): '
                                   f'no se modifica «{nombre}».')
        return super().update(request, *args, **kwargs)

    @staticmethod
    def _es_si(valor, defecto=None):
        if valor is None:
            return defecto
        return str(valor).strip().lower() in ('1', 'true', 'si', 'sí', 'yes', 'on')

    def _error(self, mensaje):
        return Response({'detail': mensaje}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Solicitud de Acción Correctiva impresa con el formato del procedimiento."""
        from .ficha_pdf import generar_sac_pdf
        sac = self.get_object()
        resp = HttpResponse(generar_sac_pdf(sac), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{sac.codigo}.pdf"'
        return resp
    pdf.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def seguimiento_pdf(self, request):
        """Seguimiento a solicitudes de acciones correctivas y no conformidades:
        las solicitudes del listado (con los mismos filtros de la pantalla)."""
        from .ficha_pdf import generar_seguimiento_sac_pdf
        qs = self.filter_queryset(self.get_queryset()).filter(is_active=True).select_related(
            'responsable', 'hallazgo').order_by('id')
        solicitudes = list(qs)
        resp = HttpResponse(generar_seguimiento_sac_pdf(solicitudes, _ultima_modificacion_sac(solicitudes)),
                            content_type='application/pdf')
        resp['Content-Disposition'] = 'inline; filename="seguimiento_acciones_correctivas.pdf"'
        return resp
    seguimiento_pdf.operacion = 'leer'

    @action(detail=True, methods=['post'])
    def evaluar(self, request, pk=None):
        """
        Evaluación de la necesidad de AC.
        Body: {significancia, analisis_extension, requiere_ac, justificacion}
        requiere_ac=True → En análisis | False → En implementación (solo correcciones).
        """
        sac = self.get_object()
        if sac.estado != 'registrada':
            return self._error('La evaluación solo aplica a solicitudes Registradas.')
        requiere = request.data.get('requiere_ac')
        if requiere is None:
            return self._error('Debe indicar si requiere acción correctiva.')
        # El Área SIG designa al responsable del tratamiento.
        if request.data.get('responsable'):
            from core.models import Usuario
            resp = Usuario.objects.filter(pk=request.data.get('responsable'), is_active=True).first()
            if not resp:
                return self._error('Responsable no válido.')
            sac.responsable = resp
        if not sac.responsable_id:
            return self._error('Designe al responsable del tratamiento de la No Conformidad.')
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
        Análisis de causa (5 Porqués).
        Body: {porques: [{pregunta, respuesta}, ...], causa_raiz, aplica_cambios_sig, aplica_actualizar_riesgos}
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
            # Cada «¿por qué?» es un par pregunta / respuesta que redacta el
            # analista; se aceptan también textos sueltos (registros anteriores).
            limpios = []
            for p in porques:
                if isinstance(p, dict):
                    par = {'pregunta': str(p.get('pregunta') or '').strip(),
                           'respuesta': str(p.get('respuesta') or '').strip()}
                    if par['pregunta'] or par['respuesta']:
                        limpios.append(par)
                elif str(p).strip():
                    limpios.append(str(p).strip())
            sac.porques = limpios
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
        if sac.estado in SolicitudAC.CERRADAS:
            return self._error('La solicitud está cerrada.')
        tipo = request.data.get('tipo')
        if not sac.puede_agregar(tipo):
            if tipo == 'correctiva':
                return self._error('Las acciones correctivas se definen en el análisis de causa, antes de aprobar el plan.')
            return self._error(f'En la etapa «{sac.get_estado_display()}» ya no se agregan correcciones.')
        ser = AccionSACSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(solicitud=sac, ciclo=sac.ciclo)
        sac = SolicitudAC.objects.prefetch_related('acciones').get(pk=sac.pk)
        return Response(SolicitudACSerializer(sac, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)
    agregar_accion.operacion = 'editar'

    def _accion_editable(self, sac, request):
        accion = sac.acciones.filter(pk=request.data.get('accion_id'), is_active=True).first()
        if not accion:
            return None, self._error('Acción no encontrada.')
        if not accion.editable():
            motivo = ('ya fue completada' if accion.estado != 'pendiente'
                      else 'es de un ciclo anterior' if accion.ciclo != sac.ciclo
                      else f'su etapa está cerrada ({sac.get_estado_display().lower()})')
            return None, self._error(f'La {accion.get_tipo_display().lower()} no se modifica: {motivo}.')
        return accion, None

    @action(detail=True, methods=['post'])
    def editar_accion(self, request, pk=None):
        """Corrige una corrección o acción correctiva mientras su etapa sigue abierta.
        Body: {accion_id, descripcion, fecha_propuesta, responsable}"""
        sac = self.get_object()
        accion, error = self._accion_editable(sac, request)
        if error:
            return error
        datos = {k: request.data[k] for k in ('descripcion', 'fecha_propuesta', 'responsable') if k in request.data}
        ser = AccionSACSerializer(accion, data=datos, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save(updated_by=request.user)
        sac = SolicitudAC.objects.prefetch_related('acciones').get(pk=sac.pk)
        return Response(SolicitudACSerializer(sac, context={'request': request}).data)
    editar_accion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_accion(self, request, pk=None):
        """Quita (baja lógica) una acción pendiente mientras su etapa sigue abierta. Body: {accion_id}"""
        sac = self.get_object()
        accion, error = self._accion_editable(sac, request)
        if error:
            return error
        accion.is_active = False
        accion.updated_by = request.user
        accion.save(update_fields=['is_active', 'updated_by', 'updated_at'])
        sac = SolicitudAC.objects.prefetch_related('acciones').get(pk=sac.pk)
        return Response(SolicitudACSerializer(sac, context={'request': request}).data)
    quitar_accion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def aprobar_plan(self, request, pk=None):
        """
        Aprueba el análisis y las acciones; designa verificador.
        Requiere causa raíz y al menos una acción correctiva.
        Body: {verificador: id}
        """
        sac = self.get_object()
        if sac.estado != 'en_analisis':
            return self._error('Solo puede aprobarse el plan de una solicitud En análisis.')
        if not sac.causa_raiz.strip():
            return self._error('Registre la causa raíz antes de aprobar el plan.')
        if not sac.acciones.filter(tipo='correctiva', ciclo=sac.ciclo, is_active=True).exists():
            return self._error('El plan debe incluir al menos una acción correctiva.')
        verificador_id = request.data.get('verificador')
        if not verificador_id:
            return self._error('Designe al responsable de verificar la eficacia.')
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
        Marca una acción como completada, con evidencia adjunta.
        Body multipart: {accion_id, verificacion, evidencia (archivo)}
        Cuando todas las acciones quedan completadas → En verificación
        (o cierre directo si la SAC no requería AC).
        """
        sac = self.get_object()
        if sac.estado != 'en_implementacion':
            return self._error('Las acciones se completan en estado En implementación.')
        try:
            accion = sac.acciones.get(pk=request.data.get('accion_id'), is_active=True)
        except (AccionSAC.DoesNotExist, ValueError, TypeError):
            return self._error('Acción no encontrada.')
        if accion.estado == 'completada':
            return self._error('Esa acción ya está completada.')
        if not (request.data.get('verificacion') or '').strip():
            return self._error('Describa la verificación de lo ejecutado antes de completar la acción.')
        accion.estado = 'completada'
        accion.fecha_completada = timezone.localdate()
        accion.verificacion = request.data.get('verificacion', '')
        if request.FILES.get('evidencia'):
            accion.evidencia = request.FILES['evidencia']
        accion.save()
        if not sac.acciones.filter(estado='pendiente', is_active=True).exists():
            if sac.requiere_ac:
                sac.estado = 'en_verificacion'
            else:
                sac.estado = 'cerrada_sin_ac'
                sac.fecha_cierre = timezone.now()
            sac.save()
            if sac.estado == 'cerrada_sin_ac':
                _cerrar_hallazgos_de_sac(sac, request.user, 'Corrección implementada; no requirió acción correctiva.')
        sac = SolicitudAC.objects.prefetch_related('acciones').get(pk=sac.pk)
        return Response(SolicitudACSerializer(sac, context={'request': request}).data)
    completar_accion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def reabrir_accion(self, request, pk=None):
        """
        Reabre una acción completada por error, con motivo, mientras la solicitud
        está en implementación o esperando la verificación de la eficacia (vuelve
        a implementación). Lo completado antes queda en el historial de la acción.
        Body: {accion_id, motivo}
        """
        sac = self.get_object()
        accion = sac.acciones.filter(pk=request.data.get('accion_id'), is_active=True).first()
        if not accion:
            return self._error('Acción no encontrada.')
        if not accion.reabrible():
            if accion.estado != 'completada':
                return self._error('La acción no está completada.')
            return self._error(f'Ya no se reabre: la solicitud está {sac.get_estado_display().lower()}.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la reapertura.')
        accion.reaperturas = list(accion.reaperturas or []) + [{
            'fecha': timezone.localtime().isoformat(timespec='minutes'),
            'usuario': request.user.get_full_name() or request.user.username,
            'motivo': motivo, 'verificacion': accion.verificacion,
            'fecha_completada': str(accion.fecha_completada or ''),
            'evidencia': accion.evidencia.name if accion.evidencia else '',
        }]
        accion.estado = 'pendiente'
        accion.fecha_completada = None
        accion.updated_by = request.user
        accion.save()
        if sac.estado == 'en_verificacion':
            sac.estado = 'en_implementacion'
            sac.save(update_fields=['estado', 'updated_at'])
        sac = SolicitudAC.objects.prefetch_related('acciones').get(pk=sac.pk)
        return Response(SolicitudACSerializer(sac, context={'request': request}).data)
    reabrir_accion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def verificar_eficacia(self, request, pk=None):
        """
        Verificación de eficacia. Body: {eficaz: bool, evaluacion}.
        Eficaz → Cerrada conforme (+ cierra el hallazgo M8 vinculado).
        No eficaz → vuelve a En análisis (+ reabre el hallazgo si estaba cerrado).
        """
        sac = self.get_object()
        if sac.estado != 'en_verificacion':
            return self._error('La solicitud no está en verificación de eficacia.')
        if (sac.verificador_id and sac.verificador_id != request.user.pk
                and not _puede_aprobar(request, 'acciones_correctivas')):
            return self._error(f'La eficacia la verifica {sac.verificador.get_full_name() or sac.verificador.username}, '
                               'designado al aprobar el plan.')
        evaluacion = (request.data.get('evaluacion') or '').strip()
        if not evaluacion:
            return self._error('Registre la evaluación de la eficacia.')
        eficaz = self._es_si(request.data.get('eficaz'), None)
        if eficaz is None:
            return self._error('Indique si las acciones fueron eficaces.')
        sac.evaluacion_eficacia = evaluacion
        sac.resultado_eficaz = eficaz
        sac.fecha_verificacion = timezone.now()
        sac.verificado_por = request.user
        if eficaz:
            sac.estado = 'cerrada_conforme'
            sac.fecha_cierre = timezone.now()
            sac.save()
            _cerrar_hallazgos_de_sac(sac, request.user, 'Acciones verificadas como eficaces.')
        else:
            # Si no fue eficaz, se revisa el análisis de causa y se definen nuevas acciones;
            # la solicitud y sus hallazgos siguen abiertos. El ciclo no eficaz
            # queda en el historial (no se sobrescribe).
            sac.ciclos_anteriores = list(sac.ciclos_anteriores or []) + [{
                'ciclo': sac.ciclo, 'fecha': timezone.localtime().isoformat(timespec='minutes'),
                'porques': list(sac.porques or []), 'causa_raiz': sac.causa_raiz,
                'evaluacion': evaluacion,
                'verificado_por': request.user.get_full_name() or request.user.username,
                'extension': sac.analisis_extension,
                'aplica_cambios_sig': sac.aplica_cambios_sig,
                'aplica_actualizar_riesgos': sac.aplica_actualizar_riesgos,
            }]
            sac.ciclo += 1
            sac.estado = 'en_analisis'
            # El nuevo ciclo empieza con el análisis en blanco: el anterior ya quedó
            # en el historial y la pantalla permite partir de él para revisarlo.
            sac.porques = []
            sac.causa_raiz = ''
            sac.save()
        sac = SolicitudAC.objects.prefetch_related('acciones').get(pk=sac.pk)
        return Response(SolicitudACSerializer(sac, context={'request': request}).data)
    verificar_eficacia.operacion = 'editar'


def _ultima_modificacion_sac(solicitudes):
    """Fecha de actualización del seguimiento: la última modificación real de las
    solicitudes listadas (la solicitud, sus acciones o su NC de origen). Sin
    solicitudes, None (el PDF usa la fecha del día)."""
    from django.db.models import Max
    if not solicitudes:
        return None
    ids = [s.pk for s in solicitudes]
    fechas = [s.updated_at for s in solicitudes if s.updated_at]
    fechas.append(AccionSAC.objects.filter(solicitud_id__in=ids).aggregate(m=Max('updated_at'))['m'])
    fechas.append(Hallazgo.objects.filter(solicitudes_ac__id__in=ids).aggregate(m=Max('updated_at'))['m'])
    fechas = [f for f in fechas if f]
    return timezone.localtime(max(fechas)).date() if fechas else None


def normas_de_sac(normas):
    """Normas de la solicitud: el SIG integrado son las tres normas de sistemas
    de gestión (casillas ISO 9001, 14001 y 45001 del formato)."""
    salida = []
    for n in normas or []:
        for x in (['iso_9001', 'iso_14001', 'iso_45001'] if n == 'sig_integrado' else [n]):
            if x not in salida:
                salida.append(x)
    return salida


def _cerrar_hallazgos_de_sac(sac, usuario, motivo):
    """Al cerrarse una solicitud de acción correctiva se cierran las NC que
    trata (la de origen y las ocurrencias sumadas)."""
    from django.db.models import Q
    for h in Hallazgo.objects.filter(Q(sac=sac) | Q(pk=sac.hallazgo_id), is_active=True).exclude(estado='cerrado'):
        h.estado = 'cerrado'
        h.cerrado_por = usuario
        h.fecha_cierre = timezone.now()
        h.comentarios_cierre = f'Cerrado con la {sac.codigo}: {motivo}'
        h.save()


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


class FormatoImpresoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    Formatos PDF que genera el sistema y su vínculo con la lista maestra.
    Cualquier usuario autenticado puede consultarlos; solo administradores
    cambian el vínculo (la caja de control de los PDF depende de él).
    """
    from .models import FormatoImpreso as _FI
    from .serializers import FormatoImpresoSerializer as _FIS
    queryset = _FI.objects.filter(is_active=True).select_related('documento')
    serializer_class = _FIS
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_permissions(self):
        from core.permissions import SoloAdministradores
        from rest_framework.permissions import IsAuthenticated
        return [SoloAdministradores()] if self.request.method == 'PATCH' else [IsAuthenticated()]


class RequisitoNormaViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo de cláusulas de las normas (solo lectura)."""
    queryset = RequisitoNorma.objects.all()
    serializer_class = RequisitoNormaSerializer
    permission_classes = [PermisoModular]
    modulo = 'auditorias'
    # El catálogo completo de una norma se usa en los selectores de cláusulas
    # (la de 17025 tiene 183 filas): se entrega entero, sin paginar.
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset().order_by('norma', 'orden')
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
        p = self.get_object()
        if p.bloqueado:
            return Response({'detail': 'El programa está aprobado. Ábralo para modificación antes de desactivarlo.'},
                            status=status.HTTP_400_BAD_REQUEST)
        p.is_active = False; p.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        p = self.get_object()
        if p.bloqueado:
            return Response({'detail': 'El programa está aprobado y es de solo lectura. Use "Modificar programa".'},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        """Aprueba el programa anual (desde borrador o en modificación) y lo deja
        de solo lectura. Sin permiso de aprobar, queda como solicitud pendiente
        para que un aprobador la apruebe, devuelva o rechace."""
        p = self.get_object()
        if p.estado == 'aprobado':
            return Response({'detail': 'El programa ya está aprobado.'}, status=status.HTTP_400_BAD_REQUEST)
        if not p.auditorias.filter(is_active=True).exists():
            return Response({'detail': 'El programa no tiene auditorías; agregue al menos una antes de aprobar.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not _puede_aprobar(request, 'auditorias'):
            if SolicitudCambioEquipo.objects.filter(modulo='auditorias', entidad='programa_auditoria',
                                                    entidad_id=p.pk, estado='pendiente').exists():
                return Response({'detail': 'Ya existe una solicitud de aprobación pendiente para este programa.'},
                                status=status.HTTP_400_BAD_REQUEST)
            rev = f' (revisión {p.revision + 1})' if p.estado == 'en_modificacion' else ''
            return _crear_solicitud_equipo(
                request, entidad='programa_auditoria', operacion='aprobar', entidad_id=p.pk,
                resumen=f'Aprobación del programa anual de auditorías {p.anio}{rev}', modulo='auditorias')
        aprobar_programa(p, request.user)
        return Response(ProgramaAuditoriaSerializer(p, context={'request': request}).data)
    aprobar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def abrir_modificacion(self, request, pk=None):
        """Aprobado → En modificación. Reabre el programa para cambios, con motivo
        obligatorio; al terminar debe aprobarse de nuevo (sube la revisión)."""
        p = self.get_object()
        if p.estado != 'aprobado':
            return Response({'detail': 'Solo se abre para modificación un programa aprobado.'},
                            status=status.HTTP_400_BAD_REQUEST)
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return Response({'detail': 'Indique el motivo de la modificación.'}, status=status.HTTP_400_BAD_REQUEST)
        p.estado = 'en_modificacion'
        p.modificado_por = request.user
        p.fecha_modificacion = timezone.now()
        p.motivo_modificacion = motivo
        p.save()
        return Response(ProgramaAuditoriaSerializer(p, context={'request': request}).data)
    abrir_modificacion.operacion = 'editar'

    @action(detail=True, methods=['get'])
    def programa_pdf(self, request, pk=None):
        """Programa anual de auditorías."""
        from .ficha_pdf import generar_programa_anual_pdf
        p = self.get_object()
        resp = HttpResponse(generar_programa_anual_pdf(p), content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="programa_auditorias_{p.anio}.pdf"'
        return resp
    programa_pdf.operacion = 'leer'


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
            if p.get('programa'):
                qs = qs.filter(programa_id=p['programa'])
            if p.get('sin_programa') == '1':
                qs = qs.filter(programa__isnull=True)
            if p.get('buscar'):
                from django.db.models import Q
                b = p['buscar']
                qs = qs.filter(Q(codigo__icontains=b) | Q(areas_procesos__icontains=b) |
                               Q(objetivo__icontains=b))
        return qs

    # --- Programa aprobado = solo lectura para lo que define el programa ---

    def create(self, request, *args, **kwargs):
        prog_id = request.data.get('programa')
        if prog_id:
            prog = ProgramaAuditoria.objects.filter(pk=prog_id).first()
            msg = _programa_bloqueado(prog)
            if msg:
                return self._error(msg)
        return super().create(request, *args, **kwargs)

    @staticmethod
    def _campos_cambiados(a, data, campos):
        """Campos de `campos` presentes en `data` cuyo valor difiere del guardado.
        Enviar el mismo valor no cuenta como cambio (la pantalla reenvía todo)."""
        cambiados = []
        for c in campos:
            if c not in data:
                continue
            nuevo = data.get(c)
            if c in ('programa', 'auditor_lider'):
                actual = getattr(a, f'{c}_id')
                nuevo = int(nuevo) if nuevo not in (None, '') else None
            elif c == 'mes_programado':
                actual = getattr(a, c)
                nuevo = int(nuevo) if nuevo not in (None, '') else None
            elif c in ('fecha_elaboracion_plan', 'fecha_programada'):
                actual = getattr(a, c)
                actual = actual.isoformat() if actual else None
                nuevo = nuevo or None
            else:
                actual = getattr(a, c)
                if isinstance(actual, str):
                    nuevo = '' if nuevo is None else str(nuevo)
            if nuevo != actual:
                cambiados.append(c)
        return cambiados

    def update(self, request, *args, **kwargs):
        a = self.get_object()
        # Etapas cerradas = solo lectura: se rechaza cualquier cambio en un
        # campo de una etapa ya superada, indicando cuál.
        todos = [c for cfg in Auditoria.ETAPAS.values() for c in cfg['campos']]
        for c in self._campos_cambiados(a, request.data, todos):
            etapa = a.campo_bloqueado(c)
            if etapa:
                return self._error(a.mensaje_etapa_cerrada(etapa) + f' Campo: {c}.')
        if a.programa_id and a.programa.bloqueado:
            # Programa aprobado: además se bloquean los campos que lo definen,
            # aunque la auditoría siga en etapa Programa.
            cambiados = self._campos_cambiados(a, request.data, ProgramaAuditoria.CAMPOS_PROGRAMA)
            if cambiados:
                return self._error(_programa_bloqueado(a.programa) + f' Campos bloqueados: {", ".join(cambiados)}.')
        return super().update(request, *args, **kwargs)

    def _exigir_etapa(self, a, etapa):
        """Respuesta de error si la etapa ya está cerrada; None si sigue abierta."""
        if not a.etapa_abierta(etapa):
            return self._error(a.mensaje_etapa_cerrada(etapa))
        return None

    def destroy(self, request, *args, **kwargs):
        a = self.get_object()
        if a.programa_id and a.programa.bloqueado:
            return self._error(_programa_bloqueado(a.programa))
        a.is_active = False; a.save()
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
        """Aprobar y comunicar el plan (Programada → Planificada). El plan lo
        aprueba el auditor líder (o quien tenga permiso de aprobar); requiere
        objetivo, alcance, auditor líder y al menos una entrevista programada."""
        a = self.get_object()
        if a.estado != 'programada':
            return self._error('El plan ya fue aprobado.')
        a.sincronizar_lider(incorporar_anterior=True)
        if not a.objetivo.strip() or not a.alcance.strip():
            return self._error('Para aprobar el plan: defina objetivo y alcance.')
        if not a.equipo.filter(rol='lider').exists():
            return self._error('Para aprobar el plan: agregue al auditor líder en el Equipo auditor (rol Líder).')
        if not [e for e in (a.cronograma_entrevistas or []) if isinstance(e, dict) and (e.get('fecha') or e.get('area'))]:
            return self._error('Para aprobar el plan: registre al menos una entrevista en el cronograma.')
        es_lider = a.auditor_lider_id == request.user.pk or a.equipo.filter(rol='lider', usuario=request.user).exists()
        if not (es_lider or _puede_aprobar(request, 'auditorias')):
            return self._error('El plan lo aprueba el auditor líder.')
        a.estado = 'planificada'
        a.plan_aprobado_por = request.user
        a.fecha_aprobacion_plan = timezone.now()
        if not a.fecha_elaboracion_plan:
            from datetime import date
            a.fecha_elaboracion_plan = timezone.localdate()
        a.save()
        return self._data(a, request)
    planificar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def iniciar(self, request, pk=None):
        """Planificada → Reunión de apertura (cierra los documentos de trabajo)."""
        a = self.get_object()
        if a.estado != 'planificada':
            return self._error('Solo se inicia una auditoría con el plan aprobado.')
        a.estado = 'apertura'
        if not a.fecha_inicio:
            a.fecha_inicio = timezone.localdate()
        a.save()
        return self._data(a, request)
    iniciar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def reprogramar(self, request, pk=None):
        """Mueve la fecha/mes con motivo registrado."""
        a = self.get_object()
        if a.estado not in ('programada', 'planificada'):
            return self._error('Solo se reprograma una auditoría que aún no se ha ejecutado.')
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo de la reprogramación.')
        nuevo_mes = request.data.get('mes_programado') or request.data.get('mes_reprogramado')
        if not nuevo_mes:
            return self._error('Indique el nuevo mes.')
        nuevo_mes = int(nuevo_mes)
        if not 1 <= nuevo_mes <= 12:
            return self._error('El mes debe estar entre 1 y 12.')
        # El mes programado original se conserva (fila "Programado" del
        # programa anual); el nuevo va a la fila "Reprogramado".
        a.reprogramada = True
        a.motivo_reprogramacion = motivo
        a.mes_reprogramado = nuevo_mes
        if request.data.get('fecha_programada'):
            a.fecha_programada = request.data['fecha_programada']
        a.save()
        return self._data(a, request)
    reprogramar.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def agregar_integrante(self, request, pk=None):
        a = self.get_object()
        if (err := self._exigir_etapa(a, 'plan')):
            return err
        rol = request.data.get('rol')
        if rol not in dict([('lider', 1), ('auditor', 1), ('experto', 1), ('observador', 1)]):
            return self._error('Rol no válido.')
        usuario_id = request.data.get('usuario') or None
        usuario = None
        if usuario_id:
            from core.models import Usuario
            usuario = Usuario.objects.filter(pk=usuario_id, is_active=True).first()
        # El cargo se toma del indicado; si no viene y es usuario interno, se
        # hereda del cargo registrado del usuario.
        if not usuario and not (request.data.get('nombre_externo') or '').strip():
            return self._error('Indique el usuario o el nombre del integrante externo.')
        if rol == 'lider':
            actual = a.integrante_lider()
            if actual:
                nombre = (actual.usuario.get_full_name() or actual.usuario.username) if actual.usuario else actual.nombre_externo
                return self._error(f'La auditoría ya tiene auditor líder ({nombre}). Quítelo del equipo para designar a otro.')
        cargo = request.data.get('cargo', '') or (getattr(usuario, 'cargo', '') if usuario else '')
        EquipoAuditoria.objects.create(
            auditoria=a, usuario=usuario,
            nombre_externo=request.data.get('nombre_externo', ''),
            rol=rol, cargo=cargo)
        # El auditor líder del equipo se refleja como auditor líder de la
        # auditoría (sincroniza el campo que valida la planificación).
        if rol == 'lider':
            a.sincronizar_lider()
        resp = self._data(a, request)
        # Independencia del auditor: se avisa (no se bloquea) si la persona
        # pertenece al área o laboratorio que se va a auditar.
        aviso = _aviso_independencia(usuario, a, rol)
        if aviso:
            resp.data['aviso'] = aviso
        return resp
    agregar_integrante.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def quitar_integrante(self, request, pk=None):
        a = self.get_object()
        if (err := self._exigir_etapa(a, 'plan')):
            return err
        for integrante in EquipoAuditoria.objects.filter(auditoria=a, pk=request.data.get('integrante_id')):
            integrante.is_active = False  # baja lógica: queda como registro de quién integró el equipo
            integrante.updated_by = request.user
            integrante.save()
        a.sincronizar_lider()
        return self._data(a, request)
    quitar_integrante.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def restaurar_integrante(self, request, pk=None):
        """Vuelve al equipo auditor a un integrante dado de baja (mientras el plan esté abierto)."""
        a = self.get_object()
        if (err := self._exigir_etapa(a, 'plan')):
            return err
        m = EquipoAuditoria.todos.filter(auditoria=a, pk=request.data.get('integrante_id'), is_active=False).first()
        if not m:
            return self._error('Integrante dado de baja no encontrado.')
        if m.rol == 'lider' and a.equipo.filter(rol='lider').exists():
            return self._error('Ya hay un auditor líder en el equipo.')
        m.is_active = True
        m.updated_by = request.user
        m.save()
        a.sincronizar_lider()
        return self._data(a, request)
    restaurar_integrante.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def registrar_acta(self, request, pk=None):
        """Registra el acta de la reunión de apertura o de cierre y avanza la
        auditoría: la apertura da inicio a la ejecución; el cierre congela los
        hallazgos comunicados y pasa al informe. Un acta registrada no se edita."""
        a = self.get_object()
        tipo = request.data.get('tipo')
        if tipo not in ('apertura', 'cierre'):
            return self._error('Tipo de acta no válido (apertura/cierre).')
        if (err := self._exigir_etapa(a, 'apertura' if tipo == 'apertura' else 'cierre')):
            return err
        participantes = request.data.get('participantes', [])
        if isinstance(participantes, str):
            import json as _json
            try:
                participantes = _json.loads(participantes)
            except ValueError:
                participantes = []
        participantes = [p for p in participantes if isinstance(p, dict) and (p.get('nombre') or '').strip()]
        if not participantes:
            return self._error('Registre los participantes de la reunión.')
        if not (request.data.get('contenido') or '').strip():
            return self._error('Complete el contenido del acta (sección 2).')
        acta, _ = ActaAuditoria.objects.update_or_create(
            auditoria=a, tipo=tipo,
            defaults={
                'participantes': participantes,
                'contenido': request.data.get('contenido', ''),
                'seccion3': request.data.get('seccion3', ''),
                'observaciones_auditado': request.data.get('observaciones_auditado', ''),
            })
        if request.FILES.get('archivo'):
            acta.archivo = request.FILES['archivo']
            acta.save()
        if tipo == 'apertura':
            a.estado = 'en_ejecucion'
            if not a.fecha_inicio:
                a.fecha_inicio = timezone.localdate()
        else:
            a.estado = 'en_informe'
            if not a.fecha_fin:
                a.fecha_fin = timezone.localdate()
        a.save()
        return self._data(a, request)
    registrar_acta.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def generar_lista(self, request, pk=None):
        """Crea la lista de verificación de una norma con sus cláusulas del
        catálogo. Es un documento de trabajo: se prepara con el plan aprobado."""
        a = self.get_object()
        if (err := self._exigir_etapa(a, 'documentos')):
            return err
        norma = request.data.get('norma')
        if norma not in ('iso_9001', 'iso_14001', 'iso_45001', 'iso_17025', 'sig_integrado'):
            return self._error('Norma no válida.')
        if ListaVerificacion.objects.filter(auditoria=a, norma=norma).exists():
            return self._error('Ya existe la lista de verificación de esa norma.')
        lista = ListaVerificacion.objects.create(auditoria=a, norma=norma)
        reqs = RequisitoNorma.objects.filter(norma=norma).order_by('orden')
        # ISO 9001 / 14001 / 45001 auditadas solas: sus preguntas (bloque
        # 'lista'); las demás filas de esas normas son títulos para selectores.
        if reqs.filter(bloque='lista').exists():
            reqs = reqs.filter(bloque='lista')
        ItemVerificacion.objects.bulk_create([
            ItemVerificacion(lista=lista, codigo=r.codigo, titulo=r.titulo, es_seccion=r.es_seccion,
                             bloque='requisitos' if r.bloque == 'lista' else r.bloque,
                             formato=r.formato, orden=r.orden)
            for r in reqs])
        return self._data(a, request)
    generar_lista.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def evaluar_item(self, request, pk=None):
        """Ítem de la lista de verificación. En la preparación (documentos de
        trabajo) solo se anota el documento de referencia; la evaluación
        (evidencia y conclusión) se registra durante la ejecución."""
        a = self.get_object()
        if not (a.etapa_abierta('documentos') or a.etapa_abierta('ejecucion')):
            return self._error(a.mensaje_etapa_cerrada('ejecucion'))
        try:
            item = ItemVerificacion.objects.get(pk=request.data.get('item_id'), lista__auditoria=a)
        except ItemVerificacion.DoesNotExist:
            return self._error('Ítem no encontrado.')
        res = request.data.get('resultado', item.resultado)
        if res not in ('pendiente', 'cumple', 'no_cumple', 'na', 'observa'):
            return self._error('Resultado no válido.')
        if not a.etapa_abierta('ejecucion'):
            evalua = (res != item.resultado
                      or request.data.get('evidencia', item.evidencia) != item.evidencia
                      or request.data.get('observacion', item.observacion) != item.observacion)
            if evalua:
                return self._error('La evaluación se registra durante la ejecución, después de la reunión de apertura.')
        if res not in ItemVerificacion.RESULTADOS_CON_HALLAZGO:
            # Ya no es No cumple ni Observación: deja de originar un hallazgo.
            item.hallazgo = None
            item.motivo_descarte = ''
        item.resultado = res
        item.documento_referencia = request.data.get('documento_referencia', item.documento_referencia)
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
        if not (a.etapa_abierta('ejecucion') or a.etapa_abierta('conclusiones')):
            return self._error(a.mensaje_etapa_cerrada('ejecucion'))
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
            fecha_deteccion=timezone.localdate(),
            auditoria=a,
            requiere_ac=(tipo in ('nc_mayor', 'nc_menor')),
        )
        items, err = self._items_de_hallazgo(a, request.data.get('item_ids'))
        if err:
            return err
        h.save()
        for it in items:
            it.hallazgo = h
            it.motivo_descarte = ''
            it.save()
        return self._data(a, request)
    registrar_hallazgo.operacion = 'crear'

    def _items_de_hallazgo(self, a, ids):
        """Ítems de la lista (de esta auditoría) evaluados como No cumple u
        Observación, que pueden originar un hallazgo."""
        ids = [i for i in (ids or []) if str(i).isdigit()]
        if not ids:
            return [], None
        items = list(ItemVerificacion.objects.filter(pk__in=ids, lista__auditoria=a, es_seccion=False))
        if len(items) != len(set(map(int, ids))):
            return None, self._error('Algún ítem no pertenece a esta auditoría.')
        if any(it.resultado not in ItemVerificacion.RESULTADOS_CON_HALLAZGO for it in items):
            return None, self._error('Solo originan hallazgos los ítems evaluados como No cumple u Observación.')
        return items, None

    def _etapa_hallazgos(self, a):
        if not (a.etapa_abierta('ejecucion') or a.etapa_abierta('conclusiones')):
            return self._error('Los hallazgos ya se comunicaron en la reunión de cierre: son de solo lectura.')
        return None

    @action(detail=True, methods=['post'])
    def vincular_items(self, request, pk=None):
        """Suma ítems de la lista a un hallazgo ya registrado (un mismo problema
        que incumple varios requisitos)."""
        a = self.get_object()
        if (err := self._etapa_hallazgos(a)):
            return err
        h = _Hallazgo.objects.filter(pk=request.data.get('hallazgo_id'), auditoria=a, is_active=True).first()
        if not h:
            return self._error('Hallazgo no encontrado.')
        items, err = self._items_de_hallazgo(a, request.data.get('item_ids'))
        if err:
            return err
        if not items:
            return self._error('Elige al menos un ítem.')
        for it in items:
            it.hallazgo = h
            it.motivo_descarte = ''
            it.save()
        return self._data(a, request)
    vincular_items.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def descartar_items(self, request, pk=None):
        """El ítem evaluado como No cumple u Observación no genera hallazgo
        (no se sostiene con evidencia, ya está cubierto, etc.). Motivo obligatorio."""
        a = self.get_object()
        if (err := self._etapa_hallazgos(a)):
            return err
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique por qué no genera hallazgo.')
        items, err = self._items_de_hallazgo(a, request.data.get('item_ids'))
        if err:
            return err
        if not items:
            return self._error('Elige al menos un ítem.')
        for it in items:
            it.hallazgo = None
            it.motivo_descarte = motivo
            it.save()
        return self._data(a, request)
    descartar_items.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def reabrir_item(self, request, pk=None):
        """Devuelve un ítem a "pendiente de clasificar" (se desvincula de su
        hallazgo o se anula su descarte)."""
        a = self.get_object()
        if (err := self._etapa_hallazgos(a)):
            return err
        it = ItemVerificacion.objects.filter(pk=request.data.get('item_id'), lista__auditoria=a).first()
        if not it:
            return self._error('Ítem no encontrado.')
        it.hallazgo = None
        it.motivo_descarte = ''
        it.save()
        return self._data(a, request)
    reabrir_item.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def editar_hallazgo(self, request, pk=None):
        """Consolidación: corrige o reclasifica un hallazgo antes de la reunión
        de cierre. Si cambia de tipo y de prefijo, toma el código del nuevo tipo
        (aún no se ha comunicado formalmente)."""
        a = self.get_object()
        if not (a.etapa_abierta('ejecucion') or a.etapa_abierta('conclusiones')):
            return self._error('Los hallazgos ya se comunicaron en la reunión de cierre: son de solo lectura.')
        h = _Hallazgo.objects.filter(pk=request.data.get('hallazgo_id'), auditoria=a, is_active=True).first()
        if not h:
            return self._error('Hallazgo no encontrado.')
        tipo = request.data.get('tipo', h.tipo)
        if tipo not in ('nc_mayor', 'nc_menor', 'observacion', 'odm'):
            return self._error('Tipo de hallazgo no válido.')
        descripcion = (request.data.get('descripcion', h.descripcion) or '').strip()
        if not descripcion:
            return self._error('La descripción del hallazgo es obligatoria.')
        from .models import PREFIJOS_HALLAZGO
        if PREFIJOS_HALLAZGO.get(tipo) != PREFIJOS_HALLAZGO.get(h.tipo):
            h.codigo = _Hallazgo.generar_codigo(tipo, h.anio_codigo())
        h.tipo = tipo
        h.descripcion = descripcion
        h.requisito = request.data.get('requisito', h.requisito)
        h.save()
        return self._data(a, request)
    editar_hallazgo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def anular_hallazgo(self, request, pk=None):
        """Consolidación: descarta un hallazgo que no se sostiene con evidencia
        (baja lógica; no se borra)."""
        a = self.get_object()
        if not (a.etapa_abierta('ejecucion') or a.etapa_abierta('conclusiones')):
            return self._error('Los hallazgos ya se comunicaron en la reunión de cierre: son de solo lectura.')
        h = _Hallazgo.objects.filter(pk=request.data.get('hallazgo_id'), auditoria=a, is_active=True).first()
        if not h:
            return self._error('Hallazgo no encontrado.')
        h.is_active = False
        h.save()
        # Sus ítems de origen vuelven a "pendiente de clasificar": hay que
        # decidir de nuevo (otro hallazgo o descarte con motivo).
        ItemVerificacion.objects.filter(hallazgo=h).update(hallazgo=None)
        return self._data(a, request)
    anular_hallazgo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def terminar_ejecucion(self, request, pk=None):
        """En ejecución → Conclusiones: el equipo auditor se reúne a consolidar
        y clasificar los hallazgos."""
        a = self.get_object()
        if a.estado != 'en_ejecucion':
            return self._error('La auditoría no está en ejecución.')
        a.estado = 'conclusiones'
        a.save()
        return self._data(a, request)
    terminar_ejecucion.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def validar_hallazgos(self, request, pk=None):
        """Conclusiones → Reunión de cierre. Requiere las conclusiones de la
        auditoría (grado de conformidad), que se presentan en la reunión."""
        a = self.get_object()
        if a.estado != 'conclusiones':
            return self._error('La auditoría no está en conclusiones.')
        pendientes = list(a.items_pendientes())
        if pendientes:
            codigos = '; '.join(it.referencia_texto() for it in pendientes[:8]) + ('…' if len(pendientes) > 8 else '')
            return self._error(f'Quedan {len(pendientes)} ítem(s) de la lista evaluados como No cumple u Observación '
                               f'sin clasificar ({codigos}): regístrelos como hallazgo, súmelos a uno o descártelos con motivo.')
        conclusiones = (request.data.get('conclusiones') or a.conclusiones or '').strip()
        if not conclusiones:
            return self._error('Registre las conclusiones de la auditoría antes de pasar a la reunión de cierre.')
        a.conclusiones = conclusiones
        a.estado = 'reunion_cierre'
        a.save()
        return self._data(a, request)
    validar_hallazgos.operacion = 'editar'


    @action(detail=True, methods=['post'])
    def cerrar(self, request, pk=None):
        """En informe → Cerrada. Requiere conclusiones. Sin permiso de aprobar,
        el cierre queda como solicitud pendiente (aprobar / devolver / rechazar)."""
        a = self.get_object()
        if a.estado != 'en_informe':
            return self._error('Solo se cierra una auditoría que ya tiene informe.')
        conclusiones = (a.conclusiones or '').strip()
        if not conclusiones:
            return self._error('La auditoría no tiene conclusiones registradas.')
        if not _puede_aprobar(request, 'auditorias'):
            if SolicitudCambioEquipo.objects.filter(modulo='auditorias', entidad='informe_auditoria',
                                                    entidad_id=a.pk, estado='pendiente').exists():
                return self._error('Ya existe una solicitud de cierre pendiente para esta auditoría.')
            # Las conclusiones ya se validaron y comunicaron en la reunión de
            # cierre: el aprobador recibe el informe tal cual; si lo devuelve,
            # se corrigen los campos del informe y se reenvía.
            return _crear_solicitud_equipo(
                request, entidad='informe_auditoria', operacion='aprobar', entidad_id=a.pk,
                payload={},
                resumen=f'Cierre del informe de auditoría {a.codigo}', modulo='auditorias')
        a.estado = 'cerrada'
        a.fecha_informe = a.fecha_informe or timezone.now()
        a.save()
        return self._data(a, request)
    cerrar.operacion = 'editar'

    def _pdf(self, pdf, nombre):
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{nombre}.pdf"'
        return resp

    @action(detail=True, methods=['get'])
    def plan_pdf(self, request, pk=None):
        """Plan de auditoría."""
        from .ficha_pdf import generar_plan_auditoria_pdf
        a = self.get_object()
        return self._pdf(generar_plan_auditoria_pdf(a), f'plan_{a.codigo}')
    plan_pdf.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def informe_pdf(self, request, pk=None):
        """Informe de auditoría."""
        from .ficha_pdf import generar_informe_auditoria_pdf
        a = self.get_object()
        return self._pdf(generar_informe_auditoria_pdf(a), f'informe_{a.codigo}')
    informe_pdf.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def acta_pdf(self, request, pk=None):
        """Acta de apertura o cierre. ?tipo=apertura|cierre."""
        from .ficha_pdf import generar_acta_pdf
        a = self.get_object()
        tipo = request.query_params.get('tipo', 'apertura')
        acta = a.actas.filter(tipo=tipo).first()
        if not acta:
            # Acta provisional en memoria para imprimir aunque aún no se registre
            acta = ActaAuditoria(auditoria=a, tipo=tipo)
        return self._pdf(generar_acta_pdf(acta), f'acta_{tipo}_{a.codigo}')
    acta_pdf.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def lista_pdf(self, request, pk=None):
        """Lista de verificación de una norma. ?norma=..."""
        from .ficha_pdf import generar_lista_verificacion_pdf
        a = self.get_object()
        norma = request.query_params.get('norma')
        lista = a.listas.filter(norma=norma).first() if norma else a.listas.first()
        if not lista:
            return self._error('No existe la lista de verificación solicitada. Genérela primero.')
        return self._pdf(generar_lista_verificacion_pdf(lista), f'lista_{lista.norma}_{a.codigo}')
    lista_pdf.operacion = 'leer'

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


def _puede_aprobar(request, modulo='equipos'):
    """True si el usuario puede aprobar cambios del módulo indicado."""
    return request.user.tiene_permiso(modulo, 'aprobar')


def aprobar_programa(programa, usuario):
    """Aprueba el programa anual y lo deja de solo lectura. Si venía de una
    modificación, sube el número de revisión."""
    if programa.estado == 'en_modificacion':
        programa.revision = (programa.revision or 0) + 1
    programa.estado = 'aprobado'
    programa.aprobado_por = usuario
    programa.fecha_aprobacion = timezone.now()
    programa.save()


def _programa_bloqueado(programa):
    """Mensaje de bloqueo si el programa está aprobado (solo lectura); '' si no."""
    if programa and programa.bloqueado:
        return (f'El programa anual {programa.anio} está aprobado y es de solo lectura. '
                f'Para cambiarlo use "Modificar programa" (quedará pendiente de nueva aprobación).')
    return ''


def _aviso_independencia(usuario, auditoria, rol):
    """
    Independencia del auditor: devuelve un texto de aviso si la persona
    pertenece al área o laboratorio que se va a auditar (no bloquea; la
    decisión queda registrada en quien la asigna). Los observadores no aplican.
    """
    import unicodedata
    if not usuario or rol == 'observador':
        return ''

    def norm(s):
        s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
        return ' '.join(s.split())

    objetivo = norm(getattr(auditoria, 'areas_procesos', ''))
    if not objetivo:
        return ''
    coincidencias = []
    for etiqueta, valor in (('área', getattr(usuario, 'area', '')), ('laboratorio', getattr(usuario, 'laboratorio', ''))):
        v = norm(valor)
        if v and len(v) >= 3 and v in objetivo:
            coincidencias.append(f'{etiqueta} "{valor}"')
    if not coincidencias:
        return ''
    nombre = usuario.get_full_name() or usuario.username
    return (f'Posible falta de independencia: {nombre} pertenece a {" y ".join(coincidencias)}, '
            f'que está dentro del alcance a auditar. Un auditor no debe auditar su propio trabajo (ISO 19011). '
            f'Revise la asignación o deje constancia de la justificación.')


def _puede_aprobar_equipos(request):
    return _puede_aprobar(request, 'equipos')


def _crear_solicitud_equipo(request, *, entidad, operacion, equipo=None,
                            entidad_id=None, payload=None, archivo=None, resumen='', modulo='equipos'):
    """
    Registra un cambio pendiente de aprobación y responde 202. Lo usan los puntos
    de guardado (equipos y competencia) cuando el usuario no tiene permiso de aprobar.
    """
    sol = SolicitudCambioEquipo(
        modulo=modulo, equipo=equipo, entidad=entidad, operacion=operacion, entidad_id=entidad_id,
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
    # Incluye los dados de baja: un punto y año tiene un solo registro (se reactiva si vuelve a tener datos).
    existentes = {(r.punto_id, r.anio): r for r in
                  ResultadoIntervalo.todos.filter(punto_id__in=puntos_validos)}
    for k, r in existentes.items():
        if k not in entrantes and r.is_active:
            r.is_active = False  # celda vaciada: baja lógica
            r.updated_by = usuario
            r.save()
    for (pid, anio), vals in entrantes.items():
        r = existentes.get((pid, anio))
        if r:
            r.resultado = vals['resultado']; r.incertidumbre = vals['incertidumbre']
            r.emp = vals['emp']; r.updated_by = usuario
            r.is_active = True
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
                               fecha_proxima_calibracion__lt=timezone.localdate())
            if p.get('por_vencer'):
                try:
                    dias = int(p['por_vencer'])
                except ValueError:
                    dias = 30
                hoy = timezone.localdate()
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

    def _baja(self, eq):
        """Un equipo dado de baja queda fuera del inventario activo: su hoja de
        vida es de solo lectura."""
        if eq.estado == 'baja':
            return self._error(f'El equipo {eq.codigo} está dado de baja: su hoja de vida es de solo lectura.')
        return None

    @action(detail=True, methods=['post'])
    def registrar_calibracion(self, request, pk=None):
        """Registra la calibración: certificado, fecha y próxima (regla patrón vigente). Cambia la vigencia del patrón
        sin bitácora: solo quien aprueba en Equipos; el resto registra la calibración en la hoja de vida (pendiente de
        aprobación)."""
        eq = self.get_object()
        if (err := self._baja(eq)):
            return err
        if not _puede_aprobar_equipos(request):
            return Response({'detail': 'Registre la calibración en la hoja de vida (pestaña Calibración): queda '
                                       'pendiente de aprobación.'}, status=status.HTTP_403_FORBIDDEN)
        from datetime import date as _d
        try:
            f_ult = _d.fromisoformat(str(request.data.get('fecha_ultima_calibracion'))[:10]) \
                if request.data.get('fecha_ultima_calibracion') else None
            f_prox = _d.fromisoformat(str(request.data.get('fecha_proxima_calibracion'))[:10]) \
                if request.data.get('fecha_proxima_calibracion') else None
        except ValueError:
            return self._error('Fecha no válida.')
        if f_ult and f_prox and f_prox <= f_ult:
            return self._error('La próxima calibración debe ser posterior a la fecha de calibración.')
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
        if (err := self._baja(eq)):
            return err
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
        if (err := self._baja(eq)):
            return err
        # Control de cambios: quitar una fila de la hoja de vida (p. ej. una calibración) sin permiso de aprobar queda
        # pendiente; al aprobarse, el registro eliminado queda íntegro en el log de auditoría.
        if not _puede_aprobar_equipos(request):
            return _crear_solicitud_equipo(
                request, entidad='registro', operacion='eliminar', equipo=eq, entidad_id=reg.pk,
                payload={'tipo': reg.tipo, 'numero_documento': reg.numero_documento,
                         'fecha': str(reg.fecha or '')},
                resumen=f'Quitar de la hoja de vida de {eq.codigo}: {reg.get_tipo_display()} '
                        f'{reg.numero_documento or ""} ({reg.fecha or "sin fecha"})')
        era_calibracion = reg.tipo == 'calibracion'
        reg.is_active = False  # baja lógica: el registro se conserva
        reg.updated_by = request.user
        reg.save()
        if era_calibracion:
            eq.actualizar_calibracion()
        return self._data(eq, request)
    eliminar_registro.operacion = 'eliminar'

    @action(detail=True, methods=['post'])
    def restaurar(self, request, pk=None):
        """Restaura una fila de la hoja de vida o una actividad del programa dadas de baja. Body: {entidad: registro |
        actividad, id}. Es un cambio de la hoja de vida: lo hace quien aprueba en Equipos."""
        eq = self.get_object()
        if (err := self._baja(eq)):
            return err
        if not _puede_aprobar_equipos(request):
            return Response({'detail': 'Restaurar requiere el permiso de aprobar en Equipos.'},
                            status=status.HTTP_403_FORBIDDEN)
        entidad, oid = request.data.get('entidad'), request.data.get('id')
        if entidad == 'registro':
            reg = RegistroEquipo.todos.filter(equipo=eq, pk=oid, is_active=False).first()
            if not reg:
                return self._error('Registro dado de baja no encontrado.')
            reg.is_active, reg.updated_by = True, request.user
            reg.save()
            if reg.tipo == 'calibracion':
                eq.actualizar_calibracion()
        elif entidad == 'actividad':
            act = ActividadPrograma.todos.filter(equipo=eq, pk=oid, is_active=False).first()
            if not act:
                return self._error('Actividad dada de baja no encontrada.')
            if ActividadPrograma.objects.filter(equipo=eq, tipo=act.tipo, anio=act.anio).exists():
                return self._error(f'Ya hay una actividad vigente de {act.get_tipo_display().lower()} en {act.anio}.')
            act.is_active, act.updated_by = True, request.user
            act.save()
        else:
            return self._error('Indique qué se restaura.')
        return self._data(eq, request)
    restaurar.operacion = 'aprobar'

    @action(detail=True, methods=['post'])
    def marcar_inoperativo(self, request, pk=None):
        """Fuera de servicio: aísla el equipo. Levantar trabajo no conforme aparte."""
        eq = self.get_object()
        if (err := self._baja(eq)):
            return err
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            return self._error('Indique el motivo por el que el equipo queda fuera de servicio.')
        eq.estado = 'inoperativo'
        eq.motivo_inoperativo = motivo
        eq.fecha_fuera_servicio = timezone.localdate()
        eq.save()
        return self._data(eq, request)
    marcar_inoperativo.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def reactivar(self, request, pk=None):
        eq = self.get_object()
        if (err := self._baja(eq)):
            return err
        if eq.estado != 'inoperativo':
            return self._error('Solo se reactiva un equipo fuera de servicio.')
        # Sacar un equipo de servicio es inmediato (seguridad); devolverlo al servicio lo decide quien aprueba.
        if not _puede_aprobar_equipos(request):
            return Response({'detail': 'Devolver el equipo al servicio requiere el permiso de aprobar en Equipos.'},
                            status=status.HTTP_403_FORBIDDEN)
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
            qs = qs.filter(requiere_calibracion=True, fecha_proxima_calibracion__lt=timezone.localdate())
        if p.get('por_vencer'):   # mismo filtro que la lista: vence dentro de N días
            try:
                dias = int(p['por_vencer'])
            except ValueError:
                dias = 30
            hoy = timezone.localdate()
            qs = qs.filter(requiere_calibracion=True, fecha_proxima_calibracion__gte=hoy,
                           fecha_proxima_calibracion__lte=hoy + _timedelta(days=dias))
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
        if (err := self._baja(eq)):
            return err
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
            equipo=eq, tipo=tipo, anio=int(request.data.get('anio') or timezone.localdate().year),
            frecuencia=request.data.get('frecuencia', ''), meses=meses)
        return self._data(eq, request)
    agregar_actividad.operacion = 'editar'

    @action(detail=True, methods=['post'])
    def programar(self, request, pk=None):
        """Programa Anual: upsert de una actividad (equipo+tipo+año) con frecuencia y meses."""
        eq = self.get_object()
        if (err := self._baja(eq)):
            return err
        tipo = request.data.get('tipo')
        if tipo not in dict(ActividadPrograma._meta.get_field('tipo').choices):
            return self._error('Tipo de actividad no válido.')
        anio = int(request.data.get('anio') or timezone.localdate().year)
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
            for act in ActividadPrograma.objects.filter(equipo=eq, tipo=tipo, anio=anio):
                act.is_active = False  # se retira del programa (baja lógica)
                act.updated_by = request.user
                act.save()
        else:
            ActividadPrograma.objects.update_or_create(
                equipo=eq, tipo=tipo, anio=anio,
                defaults={'frecuencia': frecuencia, 'meses': meses})
        return Response({'ok': True})
    programar.operacion = 'editar'

    @action(detail=False, methods=['get'])
    def programa(self, request):
        """Programa Anual consolidado: equipos (de un laboratorio) con sus actividades del año."""
        anio = int(request.query_params.get('anio') or timezone.localdate().year)
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
        anio = int(request.query_params.get('anio') or timezone.localdate().year)
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
        if (err := self._baja(eq)):
            return err
        motivo = request.data.get('motivo')
        if motivo not in dict(MovimientoEquipo._meta.get_field('motivo').choices):
            return self._error('Motivo no válido.')
        abierto = eq.movimientos.filter(fecha_retorno__isnull=True).first()
        if abierto:
            return self._error('El equipo ya está fuera (salida sin retorno registrado): registre primero su retorno.')
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
        if mov.fecha_retorno:
            return self._error('El retorno de esa salida ya está registrado.')
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
        if (err := self._baja(eq)):
            return err
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
        hoy = timezone.localdate()
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
        """PDF de la Ficha Técnica (solo esa pestaña). ?completa=1: la Hoja de Vida entera con sus bitácoras."""
        eq = self.get_object()
        from .ficha_pdf import generar_ficha_pdf
        completa = request.query_params.get('completa') == '1'
        pdf = generar_ficha_pdf(eq, completa=completa)
        resp = HttpResponse(pdf, content_type='application/pdf')
        nombre = 'Hoja de Vida' if completa else 'Ficha Tecnica'
        resp['Content-Disposition'] = f'inline; filename="{nombre} {eq.codigo}.pdf"'
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
            carta.fecha_actualizacion = timezone.localtime(max(candidatas)).date()
        nodos = []
        for n in carta.nodos.filter(is_active=True).order_by('orden', 'id').prefetch_related('padres'):
            nodos.append({
                'id': n.id, 'orden': n.orden, 'nivel': n.nivel,
                'padres': list(n.padres.values_list('id', flat=True)),
                'entidad': n.entidad, 'descripcion': n.descripcion, 'codigo': n.codigo,
                'procedimiento': n.procedimiento, 'certificado': n.certificado,
                'incertidumbre': n.incertidumbre, 'nota': n.nota, 'equipo': n.equipo_id,
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
        qs = super().get_queryset().filter(modulo=self.modulo)
        # Los filtros de bandeja (estado, equipo, mías) aplican solo al listado.
        # Las acciones sobre una solicitud concreta (aprobar, devolver, reenviar…)
        # deben encontrarla en cualquier estado.
        if self.action != 'list':
            return qs
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
            modulo=self.modulo, created_by=request.user, estado='devuelta').count()
        return Response({'devueltas': n})
    mis_devueltas_count.operacion = 'leer'

    @action(detail=False, methods=['get'])
    def pendientes_count(self, request):
        """N.° de solicitudes pendientes (para el distintivo del buzón)."""
        return Response({'pendientes': SolicitudCambioEquipo.objects.filter(modulo=self.modulo, estado='pendiente').count()})
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
        if ent == 'registro' and op == 'eliminar':
            reg = RegistroEquipo.objects.filter(pk=sol.entidad_id, equipo=sol.equipo).first()
            if reg:
                era_calibracion = reg.tipo == 'calibracion'
                reg.is_active = False  # baja lógica
                reg.updated_by = user
                reg.save()
                if era_calibracion:
                    sol.equipo.actualizar_calibracion()
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

        # --- Competencia: autorización ---
        if ent == 'autorizacion':
            from .models import Autorizacion
            if op == 'crear':
                ser = AutorizacionSerializer(data=pl, context={'request': request})
                ser.is_valid(raise_exception=True)
                ser.save(created_by=user, updated_by=user)
            elif op == 'editar':
                a = Autorizacion.objects.filter(pk=sol.entidad_id).first()
                if a:
                    ser = AutorizacionSerializer(a, data=pl, partial=True, context={'request': request})
                    ser.is_valid(raise_exception=True)
                    ser.save(updated_by=user)
            elif op == 'eliminar':
                a = Autorizacion.objects.filter(pk=sol.entidad_id).first()
                if a:
                    a.is_active = False; a.updated_by = user; a.save(update_fields=['is_active', 'updated_at'])
            return

        # --- Auditorías: aprobación del programa anual ---
        if ent == 'programa_auditoria':
            p = ProgramaAuditoria.objects.filter(pk=sol.entidad_id).first()
            if p and p.estado != 'aprobado':
                aprobar_programa(p, user)
            return

        # --- Auditorías: cierre del informe ---
        if ent == 'informe_auditoria':
            a = Auditoria.objects.filter(pk=sol.entidad_id).first()
            if a and a.estado == 'en_informe':
                if not (a.conclusiones or '').strip():
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'conclusiones': ['El informe no tiene conclusiones.']})
                a.fecha_informe = a.fecha_informe or timezone.now()
                a.estado = 'cerrada'
                a.updated_by = user
                a.save()
            return

        # --- Competencia: proceso de entrenamiento ---
        if ent == 'entrenamiento':
            from .models import ProcesoEntrenamiento
            if op == 'crear':
                ser = ProcesoEntrenamientoSerializer(data=pl, context={'request': request})
                ser.is_valid(raise_exception=True)
                ser.save(created_by=user, updated_by=user)
            elif op == 'editar':
                pe = ProcesoEntrenamiento.objects.filter(pk=sol.entidad_id).first()
                if pe:
                    ser = ProcesoEntrenamientoSerializer(pe, data=pl, partial=True, context={'request': request})
                    ser.is_valid(raise_exception=True)
                    ser.save(updated_by=user)
            elif op == 'eliminar':
                pe = ProcesoEntrenamiento.objects.filter(pk=sol.entidad_id).first()
                if pe and pe.concluido:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'detail': 'Un entrenamiento concluido no se elimina.'})
                if pe:
                    pe.is_active = False; pe.updated_by = user; pe.save(update_fields=['is_active', 'updated_at'])
            return

        # --- Competencia: evaluación de seguimiento ---
        if ent == 'seguimiento':
            from .models import EvaluacionSeguimiento
            ev = None
            if op == 'crear':
                ser = EvaluacionSeguimientoSerializer(data=pl, context={'request': request})
                ser.is_valid(raise_exception=True)
                ev = ser.save(created_by=user, updated_by=user)
            elif op == 'editar':
                ev = EvaluacionSeguimiento.objects.filter(pk=sol.entidad_id).first()
                if ev:
                    ser = EvaluacionSeguimientoSerializer(ev, data=pl, partial=True, context={'request': request})
                    ser.is_valid(raise_exception=True)
                    ev = ser.save(updated_by=user)
            elif op == 'eliminar':
                ev = EvaluacionSeguimiento.objects.filter(pk=sol.entidad_id).first()
                if ev:
                    ev.is_active = False; ev.updated_by = user; ev.save(update_fields=['is_active', 'updated_at'])
                return
            if ev:
                aplicar_decision_seguimiento(ev, user)
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
        """PDF del Intervalo de Calibración del patrón."""
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


class ResultadoIntervaloViewSet(viewsets.ReadOnlyModelViewSet):
    """Resultados anuales de un punto de intervalo de calibración (consulta). Se modifican con «guardar_matriz» de los
    puntos, que pasa por el control de cambios."""
    queryset = ResultadoIntervalo.objects.all()
    serializer_class = ResultadoIntervaloSerializer
    permission_classes = [PermisoModular]
    modulo = 'equipos'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('punto'):
            qs = qs.filter(punto_id=self.request.query_params['punto'])
        return qs.order_by('anio', 'id')


# ============================================================
# M12 — Competencia técnica y autorización del personal
# ============================================================
from .models import (  # noqa: E402
    MetodoCalibracion, ControlValidez, Autorizacion,
    ProcesoEntrenamiento, EvaluacionSeguimiento,
)
from .serializers import (  # noqa: E402
    MetodoCalibracionSerializer, ControlValidezSerializer, AutorizacionSerializer,
    ProcesoEntrenamientoSerializer, EvaluacionSeguimientoSerializer,
)


class MetodoCalibracionViewSet(viewsets.ModelViewSet):
    """Catálogo gestionable de métodos / procedimientos de calibración."""
    queryset = MetodoCalibracion.objects.all()
    serializer_class = MetodoCalibracionSerializer
    permission_classes = [PermisoModular]
    modulo = 'competencia_tecnica'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('incluir_inactivos') != '1':
            qs = qs.filter(is_active=True)
        if self.request.query_params.get('magnitud'):
            qs = qs.filter(magnitud=self.request.query_params['magnitud'])
        return qs

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object(); obj.is_active = False; obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ControlValidezViewSet(viewsets.ModelViewSet):
    """Catálogo gestionable de controles de aseguramiento de la validez de resultados."""
    queryset = ControlValidez.objects.all()
    serializer_class = ControlValidezSerializer
    permission_classes = [PermisoModular]
    modulo = 'competencia_tecnica'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('incluir_inactivos') != '1':
            qs = qs.filter(is_active=True)
        return qs

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object(); obj.is_active = False; obj.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class _CompetenciaViewSet(viewsets.ModelViewSet):
    """Base de Competencia: fija created_by/updated_by y hace baja lógica."""
    permission_classes = [PermisoModular]
    modulo = 'competencia_tecnica'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object(); obj.is_active = False
        obj.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class _GateCompetencia:
    """Candado de aprobación (crear/editar/eliminar) para las entidades de competencia."""
    entidad_solicitud = None

    def _res_sol(self, op):
        et = {'autorizacion': 'autorización', 'entrenamiento': 'proceso de entrenamiento',
              'seguimiento': 'evaluación de seguimiento'}.get(self.entidad_solicitud, self.entidad_solicitud)
        return f'Competencia: {op} de {et}'

    def create(self, request, *args, **kwargs):
        if not _puede_aprobar(request, 'competencia_tecnica'):
            ser = self.get_serializer(data=request.data)
            ser.is_valid(raise_exception=True)
            return _crear_solicitud_equipo(request, modulo='competencia_tecnica', entidad=self.entidad_solicitud,
                                           operacion='crear', payload={k: v for k, v in request.data.items()},
                                           resumen=self._res_sol('nueva'))
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not _puede_aprobar(request, 'competencia_tecnica'):
            obj = self.get_object()
            ser = self.get_serializer(obj, data=request.data, partial=kwargs.get('partial', False))
            ser.is_valid(raise_exception=True)
            return _crear_solicitud_equipo(request, modulo='competencia_tecnica', entidad=self.entidad_solicitud,
                                           operacion='editar', entidad_id=obj.pk,
                                           payload={k: v for k, v in request.data.items()}, resumen=self._res_sol('edición'))
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not _puede_aprobar(request, 'competencia_tecnica'):
            obj = self.get_object()
            return _crear_solicitud_equipo(request, modulo='competencia_tecnica', entidad=self.entidad_solicitud,
                                           operacion='eliminar', entidad_id=obj.pk, resumen=self._res_sol('eliminación'))
        return super().destroy(request, *args, **kwargs)


class AutorizacionViewSet(_GateCompetencia, _CompetenciaViewSet):
    """Autorizaciones de competencia técnica (por método y funciones)."""
    entidad_solicitud = 'autorizacion'
    queryset = Autorizacion.objects.select_related('usuario', 'metodo', 'autorizado_por')
    serializer_class = AutorizacionSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        p = self.request.query_params
        if p.get('usuario'):
            qs = qs.filter(usuario_id=p['usuario'])
        if p.get('estado'):
            qs = qs.filter(estado=p['estado'])
        if p.get('metodo'):
            qs = qs.filter(metodo_id=p['metodo'])
        return qs

    @action(detail=False, methods=['get'])
    def seguimientos(self, request):
        """Autorizaciones vigentes cuyo seguimiento está por vencer o vencido."""
        out = []
        for a in Autorizacion.objects.filter(estado='vigente', is_active=True).select_related('usuario', 'metodo'):
            if a.estado_seguimiento in ('por_vencer', 'vencido'):
                out.append(AutorizacionSerializer(a, context={'request': request}).data)
        return Response(out)
    seguimientos.operacion = 'leer'

    @action(detail=True, methods=['get'])
    def autorizacion_pdf(self, request, pk=None):
        """Carta de Autorización del Personal."""
        from .ficha_pdf import generar_autorizacion_pdf
        aut = self.get_object()
        pdf = generar_autorizacion_pdf(aut)
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="autorizacion_{aut.pk}.pdf"'
        return resp
    autorizacion_pdf.operacion = 'leer'


class ProcesoEntrenamientoViewSet(_GateCompetencia, _CompetenciaViewSet):
    """Entrenamiento y trabajo bajo supervisión previos a la autorización."""
    entidad_solicitud = 'entrenamiento'
    queryset = ProcesoEntrenamiento.objects.select_related('usuario', 'metodo', 'tutor', 'control_validez')
    serializer_class = ProcesoEntrenamientoSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        if self.request.query_params.get('usuario'):
            qs = qs.filter(usuario_id=self.request.query_params['usuario'])
        return qs

    def destroy(self, request, *args, **kwargs):
        if self.get_object().concluido:
            return Response({'detail': 'Un entrenamiento concluido es parte del sustento de la autorización: '
                                       'no se elimina.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def entrenamiento_pdf(self, request, pk=None):
        """Entrenamiento y Supervisión de Actividades."""
        from .ficha_pdf import generar_entrenamiento_pdf
        proc = self.get_object()
        pdf = generar_entrenamiento_pdf(proc)
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="entrenamiento_{proc.pk}.pdf"'
        return resp
    entrenamiento_pdf.operacion = 'leer'

    @action(detail=False, methods=['post'])
    def subir_adjunto(self, request):
        """Sube el documento adjunto de una actividad y devuelve su URL y nombre."""
        from django.core.files.storage import default_storage
        f = request.FILES.get('archivo')
        if not f:
            return Response({'detail': 'Falta el archivo.'}, status=status.HTTP_400_BAD_REQUEST)
        ruta = default_storage.save(f'competencia/adjuntos/{timezone.now():%Y}/{f.name}', f)
        return Response({'url': default_storage.url(ruta), 'nombre': f.name})
    subir_adjunto.operacion = 'editar'


def aplicar_decision_seguimiento(ev, usuario):
    """El seguimiento mueve la fecha de último seguimiento y puede suspender/reautorizar. Solo el seguimiento más
    reciente decide: corregir uno antiguo no vuelve a aplicar su decisión ni retrocede la fecha."""
    from .models import EvaluacionSeguimiento
    a = ev.autorizacion
    if not a:
        return
    seguimientos = EvaluacionSeguimiento.objects.filter(autorizacion=a, is_active=True)
    ultimo = seguimientos.order_by('-fecha', '-id').first()
    fechas = [f for f in seguimientos.values_list('fecha', flat=True) if f]
    if fechas:
        a.fecha_ultimo_seguimiento = max(fechas)
    if ultimo is not None and ultimo.pk == ev.pk:
        if ev.decision == 'suspender':
            a.estado = 'suspendida'
        elif ev.decision == 'reautorizar':
            a.estado = 'vigente'
    a.updated_by = usuario
    a.save()


class EvaluacionSeguimientoViewSet(_GateCompetencia, _CompetenciaViewSet):
    """Seguimiento de la competencia (entrevistas / controles de validez) con decisión."""
    entidad_solicitud = 'seguimiento'
    queryset = EvaluacionSeguimiento.objects.select_related('usuario', 'evaluador', 'autorizacion', 'control_validez')
    serializer_class = EvaluacionSeguimientoSerializer

    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        p = self.request.query_params
        if p.get('usuario'):
            qs = qs.filter(usuario_id=p['usuario'])
        if p.get('autorizacion'):
            qs = qs.filter(autorizacion_id=p['autorizacion'])
        return qs

    def perform_create(self, serializer):
        ev = serializer.save(created_by=self.request.user, updated_by=self.request.user)
        self._aplicar_decision(ev)

    def perform_update(self, serializer):
        ev = serializer.save(updated_by=self.request.user)
        self._aplicar_decision(ev)

    def _aplicar_decision(self, ev):
        aplicar_decision_seguimiento(ev, self.request.user)

    @action(detail=True, methods=['get'])
    def seguimiento_pdf(self, request, pk=None):
        """Entrevista de Seguimiento al Personal."""
        from .ficha_pdf import generar_seguimiento_pdf
        seg = self.get_object()
        pdf = generar_seguimiento_pdf(seg)
        resp = HttpResponse(pdf, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="seguimiento_{seg.pk}.pdf"'
        return resp
    seguimiento_pdf.operacion = 'leer'


class SolicitudCambioCompetenciaViewSet(SolicitudCambioEquipoViewSet):
    """Bandeja de aprobación de cambios del módulo Competencia técnica (aprobar/devolver/rechazar/reenviar)."""
    modulo = 'competencia_tecnica'


class SolicitudCambioAuditoriaViewSet(SolicitudCambioEquipoViewSet):
    """Bandeja de aprobación de Auditorías: programa anual e informes de cierre."""
    modulo = 'auditorias'
