"""
eSYNAPSE 360 — M6: Gestión Documental (Fase 1).
Control de versiones, flujo de aprobación y estados según
SIGE_Flujos_Detallados.md sección M6.
"""
from django.db import models

from core.models import AuditableModel

NORMAS_APLICABLES = [
    ('iso_9001', 'ISO 9001'),
    ('iso_14001', 'ISO 14001'),
    ('iso_45001', 'ISO 45001 / Ley 29783'),
    ('iso_17025', 'NTP ISO/IEC 17025'),
]

SOPORTES = [
    ('digital', 'Digital'),
    ('fisico', 'Físico'),
]

TIPOS_DOCUMENTO = [
    ('politica', 'Política'),
    ('manual', 'Manual'),
    ('reglamento', 'Reglamento'),
    ('plan', 'Plan'),
    ('programa', 'Programa'),
    ('procedimiento', 'Procedimiento'),
    ('formato', 'Formato'),
    ('pets', 'PETS'),
    ('instructivo', 'Instructivo'),
    ('registro', 'Registro'),
]

ORIGENES_DOCUMENTO = [
    ('interno', 'Interno'),
    ('externo', 'Externo'),
]

ESTADOS_VERSION = [
    ('borrador', 'En elaboración'),
    ('en_revision', 'En revisión'),
    ('en_aprobacion', 'En aprobación'),
    ('vigente', 'Vigente'),
    ('obsoleto', 'Obsoleto'),
    ('rechazado', 'Rechazado'),
]


class Documento(AuditableModel):
    """
    Registro maestro del documento. Las versiones viven en VersionDocumento.
    Un documento nunca se elimina: se desactiva (is_active=False).
    """
    codigo = models.CharField('Código', max_length=30, unique=True)
    titulo = models.CharField('Título', max_length=255)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPOS_DOCUMENTO)
    # Documento padre: un formato/registro/PETS/instructivo cuelga de un
    # procedimiento o manual (jerarquía documental ISO).
    padre = models.ForeignKey(
        'self', verbose_name='Documento padre', on_delete=models.PROTECT,
        null=True, blank=True, related_name='hijos',
    )
    proceso = models.CharField('Proceso vinculado', max_length=100, blank=True)
    normas_aplicables = models.JSONField(
        'Normas aplicables', default=list, blank=True,
        help_text='Lista de claves de NORMAS_APLICABLES (ej: ["iso_9001", "iso_17025"])',
    )
    soporte = models.CharField('Soporte', max_length=10, choices=SOPORTES, default='digital')
    origen = models.CharField('Origen', max_length=10, choices=ORIGENES_DOCUMENTO, default='interno')
    # Solo documentos externos (SIG-PRO-01 sección 6.7):
    entidad_emisora = models.CharField(
        'Entidad emisora', max_length=150, blank=True,
        help_text='INACAL-DA, ISO, MINTRA, fabricante, etc. Solo para documentos externos.',
    )
    dias_verificacion = models.PositiveSmallIntegerField(
        'Frecuencia de verificación (días)', default=7,
        help_text='Cada cuántos días debe verificarse la vigencia del documento externo',
    )
    ultima_verificacion = models.DateTimeField('Última verificación', null=True, blank=True)
    objetivo = models.TextField('Objetivo', blank=True)
    alcance = models.TextField('Alcance', blank=True)
    meses_revision = models.PositiveSmallIntegerField(
        'Frecuencia de revisión (meses)', default=12,
        help_text='Cada cuántos meses debe revisarse el documento una vez vigente',
    )
    anos_retencion = models.PositiveSmallIntegerField(
        'Tiempo de retención (años)', default=5,
        help_text='Años que el documento y sus registros deben conservarse',
    )
    archivado = models.BooleanField(
        'Archivado', default=False,
        help_text='Retirado del uso activo; se conserva durante su periodo de retención',
    )
    fecha_archivado = models.DateTimeField('Fecha de archivado', null=True, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ['codigo']

    def __str__(self):
        return f'{self.codigo} — {self.titulo}'

    @property
    def version_vigente(self):
        return self.versiones.filter(estado='vigente').first()

    @property
    def version_en_proceso(self):
        return self.versiones.filter(
            estado__in=['borrador', 'en_revision', 'en_aprobacion']
        ).first()


class VersionDocumento(AuditableModel):
    """
    Versión específica de un documento con su archivo y su flujo:
    Borrador → En revisión → En aprobación → Vigente → Obsoleto.
    Un documento vigente NO se edita: se crea una nueva versión.
    """
    documento = models.ForeignKey(
        Documento, verbose_name='Documento', on_delete=models.PROTECT,
        related_name='versiones',
    )
    version = models.CharField('Versión', max_length=10)  # ej: 00, 01, 02
    archivo = models.FileField('Archivo', upload_to='documentos/%Y/')
    resumen_cambios = models.TextField('Resumen de cambios', blank=True)
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS_VERSION, default='borrador')

    elaborado_por = models.ForeignKey(
        'core.Usuario', verbose_name='Elaborado por', on_delete=models.PROTECT,
        related_name='versiones_elaboradas', null=True, blank=True,
    )
    revisado_por = models.ForeignKey(
        'core.Usuario', verbose_name='Revisado por', on_delete=models.PROTECT,
        related_name='versiones_revisadas', null=True, blank=True,
    )
    aprobado_por = models.ForeignKey(
        'core.Usuario', verbose_name='Aprobado por', on_delete=models.PROTECT,
        related_name='versiones_aprobadas', null=True, blank=True,
    )
    comentarios_revision = models.TextField('Comentarios de revisión', blank=True)
    # Candado de etapa: tras una devolución queda True y obliga a adjuntar el
    # documento corregido antes de poder reenviar a revisión.
    requiere_recarga = models.BooleanField('Requiere recarga del corregido', default=False)

    archivo_publicado = models.FileField(
        'PDF firmado (copia controlada)', upload_to='documentos/publicados/%Y/',
        null=True, blank=True,
    )
    hash_publicado = models.CharField('SHA-256 del PDF publicado', max_length=64, blank=True)
    fecha_revision = models.DateTimeField('Fecha de revisión', null=True, blank=True)
    fecha_aprobacion = models.DateTimeField('Fecha de aprobación', null=True, blank=True)
    fecha_vigencia = models.DateField('Vigente desde', null=True, blank=True)
    fecha_proxima_revision = models.DateField('Próxima revisión', null=True, blank=True)

    class Meta:
        verbose_name = 'Versión de documento'
        verbose_name_plural = 'Versiones de documentos'
        constraints = [
            models.UniqueConstraint(fields=['documento', 'version'], name='unique_documento_version'),
        ]
        ordering = ['-id']

    def __str__(self):
        return f'{self.documento.codigo} v{self.version} ({self.get_estado_display()})'


class VerificacionExterna(AuditableModel):
    """
    Verificación periódica de vigencia de documentos externos
    Seguimiento de la vigencia de los documentos externos.
    """
    documento = models.ForeignKey(
        Documento, verbose_name='Documento', on_delete=models.PROTECT,
        related_name='verificaciones',
    )
    vigente = models.BooleanField('Sigue vigente', default=True)
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        verbose_name = 'Verificación de documento externo'
        verbose_name_plural = 'Verificaciones de documentos externos'
        ordering = ['-created_at']

    def __str__(self):
        estado = 'vigente' if self.vigente else 'DESACTUALIZADO'
        return f'{self.documento.codigo} — {estado} ({self.created_at:%Y-%m-%d})'


# ============================================================
# M8 — HALLAZGOS
# ============================================================

TIPOS_HALLAZGO = [
    ('nc_mayor', 'NC Mayor'),
    ('nc_menor', 'NC Menor'),
    ('observacion', 'Observación'),
    ('odm', 'Oportunidad de Mejora'),
]

FUENTES_HALLAZGO = [
    ('auditoria_interna', 'Auditoría interna'),
    ('auditoria_externa', 'Auditoría externa'),
    ('inspeccion', 'Inspección'),
    ('queja', 'Queja'),
    ('seguimiento', 'Seguimiento de procesos'),
    ('indicador', 'Indicador'),
    ('riesgo', 'Riesgo materializado'),
    ('otro', 'Otro'),
]

ESTADOS_HALLAZGO = [
    ('registrado', 'Registrado'),
    ('en_analisis', 'En análisis'),
    ('en_tratamiento', 'En tratamiento'),
    ('cerrado', 'Cerrado'),
    ('reabierto', 'Reabierto'),
]

PREFIJOS_HALLAZGO = {
    'nc_mayor': 'NC',
    'nc_menor': 'NC',
    'observacion': 'OBS',
    'odm': 'ODM',
}


class Hallazgo(AuditableModel):
    """
    M8 — Hallazgos: NC, observaciones y oportunidades de mejora.
    Código correlativo automático por tipo y año (ej: NC-2026-001).
    """
    codigo = models.CharField('Código', max_length=20, unique=True, editable=False)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPOS_HALLAZGO)
    fuente = models.CharField('Fuente', max_length=30, choices=FUENTES_HALLAZGO)
    proceso = models.CharField('Proceso afectado', max_length=100)
    descripcion = models.TextField('Descripción del hallazgo')
    requisito = models.CharField(
        'Requisito incumplido', max_length=200, blank=True,
        help_text='Cláusula de norma o requisito legal (ej: ISO 17025 7.8.2)',
    )
    lugar = models.CharField('Lugar de detección', max_length=150, blank=True)
    fecha_deteccion = models.DateField('Fecha de detección')
    evidencia = models.FileField('Evidencia', upload_to='hallazgos/%Y/', blank=True, null=True)
    responsable = models.ForeignKey(
        'core.Usuario', verbose_name='Responsable del tratamiento',
        on_delete=models.PROTECT, related_name='hallazgos_asignados',
        null=True, blank=True,
    )
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS_HALLAZGO, default='registrado')
    analisis = models.TextField('Análisis del hallazgo', blank=True)
    correccion = models.TextField('Corrección inmediata aplicada', blank=True)
    comentarios_cierre = models.TextField('Comentarios de cierre', blank=True)
    cerrado_por = models.ForeignKey(
        'core.Usuario', verbose_name='Cerrado por', on_delete=models.PROTECT,
        related_name='hallazgos_cerrados', null=True, blank=True,
    )
    fecha_cierre = models.DateTimeField('Fecha de cierre', null=True, blank=True)
    requiere_ac = models.BooleanField(
        'Requiere acción correctiva', default=False,
        help_text='Las NC Mayores la requieren automáticamente (se vincula en M9)',
    )
    auditoria = models.ForeignKey(
        'esynapse_sig.Auditoria', verbose_name='Auditoría de origen', on_delete=models.PROTECT,
        related_name='hallazgos', null=True, blank=True,
    )
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Hallazgo'
        verbose_name_plural = 'Hallazgos'
        ordering = ['-id']

    def __str__(self):
        return f'{self.codigo} — {self.get_tipo_display()}'

    @staticmethod
    def generar_codigo(tipo):
        from django.utils import timezone
        prefijo = PREFIJOS_HALLAZGO.get(tipo, 'HAL')
        anio = timezone.now().year
        # Correlativo por prefijo y año, formato PREFIJO-NNN-YYYY
        nums = []
        for cod in Hallazgo.objects.filter(
                codigo__startswith=f'{prefijo}-', codigo__endswith=f'-{anio}'
        ).values_list('codigo', flat=True):
            partes = cod.split('-')
            if len(partes) == 3 and partes[0] == prefijo and partes[2] == str(anio):
                try:
                    nums.append(int(partes[1]))
                except ValueError:
                    pass
        siguiente = max(nums) + 1 if nums else 1
        return f'{prefijo}-{siguiente:03d}-{anio}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo(self.tipo)
        if self.tipo == 'nc_mayor':
            self.requiere_ac = True
        super().save(*args, **kwargs)


# ============================================================
# FIRMA ELECTRÓNICA DE DOCUMENTOS (sección 0.4 de flujos)
# ============================================================

ROLES_FIRMA = [
    ('elaborado', 'Elaborado'),
    ('revisado', 'Revisado'),
    ('aprobado', 'Aprobado'),
]


class FirmaVersion(AuditableModel):
    """
    Firma electrónica de una versión de documento: quién, cuándo, desde qué IP
    y el hash SHA-256 del archivo en el momento de firmar. La contraseña del
    usuario actúa como segundo factor (se verifica, nunca se almacena).
    """
    version = models.ForeignKey(
        VersionDocumento, verbose_name='Versión', on_delete=models.PROTECT,
        related_name='firmas',
    )
    rol = models.CharField('Rol de firma', max_length=15, choices=ROLES_FIRMA)
    usuario = models.ForeignKey(
        'core.Usuario', verbose_name='Firmante', on_delete=models.PROTECT,
        related_name='firmas_documentos',
    )
    cargo = models.CharField('Cargo al firmar', max_length=100, blank=True)
    ip = models.GenericIPAddressField('IP', null=True, blank=True)
    hash_archivo = models.CharField('SHA-256 del archivo firmado', max_length=64)

    class Meta:
        verbose_name = 'Firma electrónica'
        verbose_name_plural = 'Firmas electrónicas'
        constraints = [
            models.UniqueConstraint(fields=['version', 'rol'], name='unique_firma_version_rol'),
        ]
        ordering = ['id']

    def __str__(self):
        return f'{self.version} — {self.get_rol_display()} por {self.usuario}'


ETAPAS_OBSERVACION = [
    ('revision', 'Revisión'),
    ('aprobacion', 'Aprobación'),
]

ACCIONES_OBSERVACION = [
    ('devuelto', 'Devuelto a elaboración'),
    ('rechazado', 'Rechazado definitivamente'),
]


class ObservacionVersion(AuditableModel):
    """
    Historial de observaciones de revisión/aprobación de una versión.
    Cada devolución o rechazo queda como entrada independiente, con
    comentario y archivo adjunto opcional (ej: el documento con anotaciones,
    resaltados o tachados del revisor). Evidencia de revisión real ante auditorías.
    """
    version = models.ForeignKey(
        VersionDocumento, verbose_name='Versión', on_delete=models.PROTECT,
        related_name='observaciones',
    )
    etapa = models.CharField('Etapa', max_length=15, choices=ETAPAS_OBSERVACION)
    accion = models.CharField('Acción', max_length=15, choices=ACCIONES_OBSERVACION)
    comentarios = models.TextField('Comentarios')
    archivo = models.FileField(
        'Archivo con anotaciones', upload_to='documentos/observaciones/%Y/',
        blank=True, null=True,
    )
    resuelta = models.BooleanField('Resuelta', default=False)

    class Meta:
        verbose_name = 'Observación de versión'
        verbose_name_plural = 'Observaciones de versiones'
        ordering = ['-id']

    def __str__(self):
        return f'{self.version} — {self.get_etapa_display()}: {self.get_accion_display()}'


ORIGENES_ARCHIVO = [
    ('elaboracion', 'Cargado en elaboración'),
    ('correccion', 'Corrección del elaborador'),
    ('anotado_revision', 'Anotado por el revisor'),
    ('anotado_aprobacion', 'Anotado por el aprobador'),
    ('nueva_version', 'Nueva versión'),
]


class ArchivoVersion(AuditableModel):
    """
    Bitácora append-only de los archivos de una versión. Cada subida (carga
    inicial, corrección, archivo anotado del revisor/aprobador, nueva versión)
    queda guardada como un registro propio e inmutable, con su etapa, origen,
    autor y hash. Nada se sobrescribe: el documento se conserva tal como estaba
    en cada paso. Evidencia de trazabilidad ante auditorías.
    """
    version = models.ForeignKey(
        VersionDocumento, verbose_name='Versión', on_delete=models.PROTECT,
        related_name='historial_archivos',
    )
    archivo = models.FileField('Archivo', upload_to='documentos/historial/%Y/')
    origen = models.CharField('Origen', max_length=20, choices=ORIGENES_ARCHIVO)
    etapa = models.CharField('Etapa al registrar', max_length=20, blank=True)
    hash_archivo = models.CharField('SHA-256', max_length=64, blank=True)

    class Meta:
        verbose_name = 'Archivo de versión (bitácora)'
        verbose_name_plural = 'Bitácora de archivos de versiones'
        ordering = ['-id']

    def __str__(self):
        return f'{self.version} — {self.get_origen_display()}'


# ============================================================
# M9 — SOLICITUDES DE ACCIÓN CORRECTIVA (SIG-PRO-11)
# ============================================================

FUENTES_SAC = [
    ('auditoria_interna', 'Auditoría interna'),
    ('auditoria_externa', 'Auditoría externa'),
    ('revision_direccion', 'Revisión por la Dirección'),
    ('queja', 'Queja'),
    ('otros', 'Otros'),
]

SIGNIFICANCIA_SAC = [
    ('bajo', 'Bajo'),
    ('alto', 'Alto'),
]

ESTADOS_SAC = [
    ('registrada', 'Registrada'),
    ('en_analisis', 'En análisis de causa'),
    ('en_implementacion', 'En implementación'),
    ('en_verificacion', 'En verificación de eficacia'),
    ('cerrada_conforme', 'Cerrada conforme'),
    ('cerrada_sin_ac', 'Cerrada (solo corrección)'),
]


class SolicitudAC(AuditableModel):
    """
    M9 — Solicitud de Acción Correctiva (SIG-PRO-11-r01).
    Código SAC-NN-YYYY. Ciclo: Registrada → (evaluación 6.4) →
    En análisis → En implementación → En verificación → Cerrada.
    """
    codigo = models.CharField('Código', max_length=20, unique=True, editable=False)
    hallazgo = models.ForeignKey(
        Hallazgo, verbose_name='Hallazgo vinculado (M8)', on_delete=models.PROTECT,
        related_name='solicitudes_ac', null=True, blank=True,
    )
    # 1. Procedencia (r01)
    fuente = models.CharField('Procedencia', max_length=30, choices=FUENTES_SAC)
    fuente_detalle = models.CharField('Detalle de procedencia', max_length=200, blank=True)
    normas_aplicables = models.JSONField('Normas aplicables', default=list, blank=True)
    auditor = models.CharField('Auditor', max_length=150, blank=True)
    auditado = models.CharField('Auditado', max_length=150, blank=True)
    requisito_auditado = models.CharField('Requisito auditado', max_length=200, blank=True)
    # 2. No conformidad
    descripcion_nc = models.TextField('Descripción de la No Conformidad')
    # 3-4. Evaluación (6.4)
    significancia = models.CharField('Nivel de significancia', max_length=10,
                                     choices=SIGNIFICANCIA_SAC, blank=True)
    analisis_extension = models.TextField('Análisis de la extensión', blank=True)
    requiere_ac = models.BooleanField('Requiere acción correctiva', null=True, blank=True)
    justificacion_evaluacion = models.TextField('Justificación de la evaluación', blank=True)
    # 6. Análisis de causa — 5 porqués (Anexo 1)
    porques = models.JSONField('5 Porqués', default=list, blank=True)
    causa_raiz = models.TextField('Causa raíz', blank=True)
    # 9. Actualizaciones
    aplica_cambios_sig = models.BooleanField('¿Aplica cambios al SIG?', null=True, blank=True)
    aplica_actualizar_riesgos = models.BooleanField(
        '¿Aplica actualizar matriz de riesgos?', null=True, blank=True)
    # Responsables
    responsable = models.ForeignKey(
        'core.Usuario', verbose_name='Responsable del tratamiento', on_delete=models.PROTECT,
        related_name='sac_asignadas', null=True, blank=True,
    )
    verificador = models.ForeignKey(
        'core.Usuario', verbose_name='Verificador de eficacia', on_delete=models.PROTECT,
        related_name='sac_a_verificar', null=True, blank=True,
    )
    # 8. Eficacia y 10. Conformidad
    estado = models.CharField('Estado', max_length=25, choices=ESTADOS_SAC, default='registrada')
    evaluacion_eficacia = models.TextField('Evaluación de la eficacia', blank=True)
    resultado_eficaz = models.BooleanField('Resultado eficaz', null=True, blank=True)
    fecha_verificacion = models.DateTimeField('Fecha de verificación', null=True, blank=True)
    fecha_cierre = models.DateTimeField('Fecha de cierre', null=True, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Solicitud de Acción Correctiva'
        verbose_name_plural = 'Solicitudes de Acción Correctiva'
        ordering = ['-id']

    def __str__(self):
        return f'{self.codigo} — {self.get_estado_display()}'

    @staticmethod
    def generar_codigo():
        from django.utils import timezone
        anio = timezone.now().year
        # Correlativo por año, formato SAC-NNN-YYYY
        nums = []
        for cod in SolicitudAC.objects.filter(
                codigo__startswith='SAC-', codigo__endswith=f'-{anio}'
        ).values_list('codigo', flat=True):
            partes = cod.split('-')
            if len(partes) == 3 and partes[2] == str(anio):
                try:
                    nums.append(int(partes[1]))
                except ValueError:
                    pass
        n = max(nums) + 1 if nums else 1
        return f'SAC-{n:03d}-{anio}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo()
        super().save(*args, **kwargs)


TIPOS_ACCION_SAC = [
    ('correccion', 'Corrección'),
    ('correctiva', 'Acción correctiva'),
]

ESTADOS_ACCION_SAC = [
    ('pendiente', 'Pendiente'),
    ('completada', 'Completada'),
]


class AccionSAC(AuditableModel):
    """
    Acción de una SAC: corrección inmediata (sección 5 del r01) o
    acción correctiva (sección 7). Con fecha, responsable y evidencia.
    """
    solicitud = models.ForeignKey(
        SolicitudAC, verbose_name='Solicitud', on_delete=models.PROTECT,
        related_name='acciones',
    )
    tipo = models.CharField('Tipo', max_length=15, choices=TIPOS_ACCION_SAC)
    descripcion = models.TextField('Descripción de la acción')
    fecha_propuesta = models.DateField('Fecha propuesta')
    responsable = models.ForeignKey(
        'core.Usuario', verbose_name='Responsable', on_delete=models.PROTECT,
        related_name='acciones_sac', null=True, blank=True,
    )
    estado = models.CharField('Estado', max_length=15, choices=ESTADOS_ACCION_SAC,
                              default='pendiente')
    fecha_completada = models.DateField('Fecha de ejecución', null=True, blank=True)
    verificacion = models.TextField('Verificación de la acción', blank=True)
    evidencia = models.FileField('Evidencia', upload_to='sac/evidencias/%Y/',
                                 blank=True, null=True)

    class Meta:
        verbose_name = 'Acción de SAC'
        verbose_name_plural = 'Acciones de SAC'
        ordering = ['fecha_propuesta', 'id']

    def __str__(self):
        return f'{self.solicitud.codigo} — {self.get_tipo_display()}: {self.descripcion[:40]}'


# ============================================================
# M10 — AUDITORÍAS INTERNAS (SIG-PRO-16)
# ============================================================

MODALIDADES_AUDITORIA = [
    ('presencial', 'Presencial (in situ)'),
    ('remota', 'Remota'),
    ('hibrido', 'Híbrido'),
]

TIPOS_AUDITORIA = [
    ('programada', 'Programada'),
    ('extraordinaria', 'Extraordinaria'),
]

ESTADOS_AUDITORIA = [
    ('programada', 'Programada'),
    ('planificada', 'Planificada'),
    ('en_ejecucion', 'En ejecución'),
    ('en_informe', 'En informe'),
    ('cerrada', 'Cerrada'),
]

ROLES_EQUIPO = [
    ('lider', 'Auditor líder'),
    ('auditor', 'Auditor'),
    ('experto', 'Experto técnico'),
    ('observador', 'Observador'),
]

RESULTADOS_ITEM = [
    ('pendiente', 'Pendiente'),
    ('cumple', 'Cumple'),
    ('no_cumple', 'No cumple'),
    ('na', 'No aplica'),
    ('observa', 'Observación'),
]


class RequisitoNorma(models.Model):
    """Catálogo de cláusulas de las normas; base de las listas de verificación."""
    norma = models.CharField('Norma', max_length=20, choices=NORMAS_APLICABLES)
    codigo = models.CharField('Cláusula', max_length=15)
    titulo = models.CharField('Título', max_length=255)
    es_seccion = models.BooleanField('Es sección', default=False)
    orden = models.PositiveIntegerField('Orden', default=0)

    class Meta:
        verbose_name = 'Requisito de norma'
        verbose_name_plural = 'Catálogo de requisitos de normas'
        ordering = ['norma', 'orden']
        constraints = [models.UniqueConstraint(fields=['norma', 'codigo'], name='unique_norma_codigo')]

    def __str__(self):
        return f'{dict(NORMAS_APLICABLES).get(self.norma, self.norma)} {self.codigo} {self.titulo}'


class ProgramaAuditoria(AuditableModel):
    """Programa anual de auditorías (SIG-PRO-16-r01)."""
    anio = models.PositiveIntegerField('Año', unique=True)
    estado = models.CharField('Estado', max_length=15,
                              choices=[('borrador', 'Borrador'), ('aprobado', 'Aprobado')],
                              default='borrador')
    aprobado_por = models.ForeignKey('core.Usuario', on_delete=models.PROTECT,
                                     related_name='programas_aprobados', null=True, blank=True)
    fecha_aprobacion = models.DateTimeField('Fecha de aprobación', null=True, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Programa anual de auditorías'
        verbose_name_plural = 'Programas anuales de auditorías'
        ordering = ['-anio']

    def __str__(self):
        return f'Programa {self.anio}'


class Auditoria(AuditableModel):
    """M10 — Auditoría interna (SIG-PRO-16). Código AI-NN-YYYY."""
    codigo = models.CharField('Código', max_length=20, unique=True, editable=False)
    programa = models.ForeignKey(ProgramaAuditoria, on_delete=models.PROTECT,
                                 related_name='auditorias', null=True, blank=True)
    tipo = models.CharField('Tipo', max_length=15, choices=TIPOS_AUDITORIA, default='programada')
    normas_aplicables = models.JSONField('Normas / criterios', default=list, blank=True)
    objetivo = models.TextField('Objetivo', blank=True)
    alcance = models.TextField('Alcance', blank=True)
    criterios = models.TextField('Criterios de auditoría', blank=True)
    documentos_referencia = models.TextField('Documentos de referencia', blank=True)
    areas_procesos = models.TextField('Áreas / procesos a auditar', blank=True)
    modalidad = models.CharField('Modalidad', max_length=12, choices=MODALIDADES_AUDITORIA,
                                 default='presencial')
    auditor_lider = models.ForeignKey('core.Usuario', on_delete=models.PROTECT,
                                      related_name='auditorias_lideradas', null=True, blank=True)
    mes_programado = models.PositiveSmallIntegerField('Mes programado', null=True, blank=True)
    fecha_programada = models.DateField('Fecha programada', null=True, blank=True)
    fecha_inicio = models.DateField('Inicio', null=True, blank=True)
    fecha_fin = models.DateField('Fin', null=True, blank=True)
    reprogramada = models.BooleanField('Reprogramada', default=False)
    motivo_reprogramacion = models.CharField('Motivo de reprogramación', max_length=255, blank=True)
    estado = models.CharField('Estado', max_length=15, choices=ESTADOS_AUDITORIA, default='programada')
    # Informe (SIG-PRO-16-r04)
    fortalezas = models.TextField('Fortalezas', blank=True)
    debilidades = models.TextField('Debilidades', blank=True)
    conclusiones = models.TextField('Conclusiones', blank=True)
    fecha_informe = models.DateTimeField('Fecha de informe', null=True, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Auditoría interna'
        verbose_name_plural = 'Auditorías internas'
        ordering = ['-id']

    def __str__(self):
        return self.codigo

    @staticmethod
    def generar_codigo():
        from django.utils import timezone
        anio = timezone.now().year
        sufijo = f'-{anio}'
        ultimo = (Auditoria.objects.filter(codigo__endswith=sufijo)
                  .order_by('-codigo').values_list('codigo', flat=True).first())
        n = int(ultimo.split('-')[1]) + 1 if ultimo else 1
        return f'AI-{n:02d}{sufijo}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo()
        super().save(*args, **kwargs)


class EquipoAuditoria(AuditableModel):
    auditoria = models.ForeignKey(Auditoria, on_delete=models.PROTECT, related_name='equipo')
    usuario = models.ForeignKey('core.Usuario', on_delete=models.PROTECT,
                                related_name='participaciones_auditoria', null=True, blank=True)
    nombre_externo = models.CharField('Nombre (externo)', max_length=150, blank=True)
    rol = models.CharField('Rol', max_length=12, choices=ROLES_EQUIPO)
    cargo = models.CharField('Cargo', max_length=120, blank=True)

    class Meta:
        verbose_name = 'Integrante del equipo auditor'
        verbose_name_plural = 'Equipo auditor'
        ordering = ['id']

    def __str__(self):
        return f'{self.auditoria.codigo} — {self.get_rol_display()}'


class ActaAuditoria(AuditableModel):
    auditoria = models.ForeignKey(Auditoria, on_delete=models.PROTECT, related_name='actas')
    tipo = models.CharField('Tipo', max_length=10,
                            choices=[('apertura', 'Apertura'), ('cierre', 'Cierre')])
    participantes = models.JSONField('Participantes', default=list, blank=True)
    contenido = models.TextField('Contenido', blank=True)
    observaciones_auditado = models.TextField('Observaciones del área auditada', blank=True)
    archivo = models.FileField('Acta firmada', upload_to='auditorias/actas/%Y/', null=True, blank=True)

    class Meta:
        verbose_name = 'Acta de auditoría'
        verbose_name_plural = 'Actas de auditoría'
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['auditoria', 'tipo'], name='unique_acta_tipo')]

    def __str__(self):
        return f'{self.auditoria.codigo} — Acta {self.get_tipo_display()}'


class ListaVerificacion(AuditableModel):
    auditoria = models.ForeignKey(Auditoria, on_delete=models.PROTECT, related_name='listas')
    norma = models.CharField('Norma', max_length=20, choices=NORMAS_APLICABLES)

    class Meta:
        verbose_name = 'Lista de verificación'
        verbose_name_plural = 'Listas de verificación'
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['auditoria', 'norma'], name='unique_lista_norma')]

    def __str__(self):
        return f'{self.auditoria.codigo} — {self.get_norma_display()}'


class ItemVerificacion(AuditableModel):
    lista = models.ForeignKey(ListaVerificacion, on_delete=models.PROTECT, related_name='items')
    codigo = models.CharField('Cláusula', max_length=15)
    titulo = models.CharField('Requisito', max_length=255)
    es_seccion = models.BooleanField('Es sección', default=False)
    orden = models.PositiveIntegerField('Orden', default=0)
    resultado = models.CharField('Resultado', max_length=12, choices=RESULTADOS_ITEM, default='pendiente')
    evidencia = models.TextField('Evidencia', blank=True)
    observacion = models.TextField('Observación', blank=True)

    class Meta:
        verbose_name = 'Ítem de verificación'
        verbose_name_plural = 'Ítems de verificación'
        ordering = ['lista', 'orden']

    def __str__(self):
        return f'{self.lista} {self.codigo}'


# ============================================================
# M13 — EQUIPOS / CONTROL DEL EQUIPAMIENTO (MET-PRO-04)
# ============================================================

MAGNITUDES_EQUIPO = [
    ('masa', 'Masa'),
    ('temperatura', 'Temperatura'),
    ('electricidad', 'Electricidad'),
    ('presion', 'Presión'),
    ('longitud', 'Longitud'),
    ('grandes_volumenes', 'Grandes Volúmenes y Flujo'),
    ('analisis_quimico', 'Análisis Químico'),
]

PREFIJO_MAGNITUD = {
    'masa': 'M', 'temperatura': 'TH', 'electricidad': 'ET', 'presion': 'FP',
    'longitud': 'LA', 'grandes_volumenes': 'GV', 'analisis_quimico': 'AQ',
}

CLASIFICACIONES_EQUIPO = [
    ('patron_referencia', 'Patrón de Referencia'),
    ('patron_verificacion', 'Patrón de Verificación'),
    ('patron_trabajo', 'Patrón de Trabajo'),
    ('equipamiento', 'Equipamiento Auxiliar'),
]

ESTADOS_EQUIPO = [
    ('operativo', 'Operativo'),
    ('calibrado', 'Calibrado'),
    ('inoperativo', 'Inoperativo / Fuera de servicio'),
    ('baja', 'De baja'),
]


class Equipo(AuditableModel):
    """
    M13 — Equipo o patrón del laboratorio (Hoja de Vida + Inventario,
    MET-PRO-04-r01/r02). Código por magnitud (M-001, TH-01, ...).
    """
    codigo = models.CharField('Código', max_length=20, unique=True,
                              help_text='Lo asigna el laboratorio (p. ej. M-001, TH-01).')
    magnitud = models.CharField('Magnitud', max_length=20, choices=MAGNITUDES_EQUIPO)
    clasificacion = models.CharField('Clasificación', max_length=20, choices=CLASIFICACIONES_EQUIPO,
                                     default='equipamiento')
    nombre = models.CharField('Nombre del equipo', max_length=150)
    marca = models.CharField('Marca', max_length=100, blank=True)
    modelo = models.CharField('Modelo', max_length=100, blank=True)
    serie = models.CharField('N° de serie', max_length=100, blank=True)
    procedencia = models.CharField('Procedencia', max_length=100, blank=True)
    # Especificaciones técnicas
    intervalo_indicacion = models.CharField('Intervalo de indicación / Valor nominal', max_length=120, blank=True)
    division_escala = models.CharField('División de escala (d) / verificación (e)', max_length=80, blank=True)
    clase_exactitud = models.CharField('Clase de exactitud', max_length=80, blank=True)
    resolucion = models.CharField('Resolución', max_length=80, blank=True)
    cantidad = models.CharField('Alcance / Cantidad', max_length=40, blank=True)
    material = models.CharField('Material', max_length=80, blank=True)
    tipo_indicacion = models.CharField('Tipo de indicación', max_length=80, blank=True)
    laboratorio = models.CharField('Ubicación / Laboratorio', max_length=120, blank=True)
    instructivo = models.CharField('Instructivo', max_length=120, blank=True)
    manual = models.CharField('Manual', max_length=120, blank=True)
    criterio_aceptacion = models.TextField('Criterio de aceptación', blank=True)
    exactitud_asignada = models.CharField('Exactitud asignada', max_length=120, blank=True)
    inicio_servicio = models.DateField('Inicio de servicio', null=True, blank=True)
    # Estado operativo
    estado = models.CharField('Estado', max_length=15, choices=ESTADOS_EQUIPO, default='operativo')
    motivo_inoperativo = models.CharField('Motivo (inoperativo)', max_length=255, blank=True)
    fecha_fuera_servicio = models.DateField('Fecha fuera de servicio', null=True, blank=True)
    # Calibración (regla "patrón vigente")
    requiere_calibracion = models.BooleanField(
        'Requiere calibración', default=True,
        help_text='Equipos con efecto significativo en el resultado de la calibración',
    )
    n_certificado = models.CharField('N° de certificado de calibración', max_length=120, blank=True)
    proveedor_calibracion = models.CharField('Proveedor de calibración', max_length=150, blank=True)
    fecha_ultima_calibracion = models.DateField('Última calibración', null=True, blank=True)
    fecha_proxima_calibracion = models.DateField('Próxima calibración', null=True, blank=True)
    periodicidad_dias = models.PositiveSmallIntegerField('Periodicidad (días)', null=True, blank=True)
    certificado = models.FileField('Certificado de calibración', upload_to='equipos/certificados/%Y/',
                                   null=True, blank=True)
    imagen = models.FileField('Imagen del equipo', upload_to='equipos/imagenes/%Y/',
                              null=True, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering = ['codigo']

    def __str__(self):
        return f'{self.codigo} — {self.nombre}'

    @property
    def es_patron(self):
        return self.clasificacion in ('patron_referencia', 'patron_verificacion', 'patron_trabajo')

    @property
    def calibracion_vigente(self):
        """True si tiene próxima calibración futura; None si no aplica/no tiene fecha."""
        if not self.requiere_calibracion:
            return None
        if not self.fecha_proxima_calibracion:
            return None
        from django.utils import timezone
        return self.fecha_proxima_calibracion >= timezone.now().date()

    def actualizar_calibracion(self):
        """
        Recalcula los campos de calibración del equipo a partir del último
        registro de calibración de su hoja de vida (RegistroEquipo tipo
        'calibracion'). Alimenta la regla "patrón vigente" y el calendario.
        """
        ult = (self.registros.filter(tipo='calibracion', fecha__isnull=False)
               .order_by('-fecha', '-id').first())
        if ult:
            self.fecha_ultima_calibracion = ult.fecha
            self.fecha_proxima_calibracion = ult.fecha_proxima
            self.n_certificado = ult.numero_documento or self.n_certificado
            if self.estado in ('operativo', 'calibrado'):
                self.estado = 'calibrado'
        else:
            self.fecha_ultima_calibracion = None
            self.fecha_proxima_calibracion = None
        self.save(update_fields=['fecha_ultima_calibracion', 'fecha_proxima_calibracion',
                                 'n_certificado', 'estado', 'updated_at'])


TIPOS_REGISTRO_EQUIPO = [
    ('calibracion', 'Calibración'),
    ('mantenimiento', 'Mantenimiento'),
    ('verificacion', 'Verificación'),
    ('comprobacion_intermedia', 'Comprobación Intermedia'),
    ('caracterizacion', 'Caracterización'),
    ('suceso', 'Historial de Sucesos'),
]


class RegistroEquipo(AuditableModel):
    """
    Bitácora de la Hoja de Vida (MET-PRO-04-r01). Un registro por fila de cada
    pestaña del Excel: Calibración, Mantenimiento, Verificación, Comprobación
    Intermedia, Caracterización e Historial de Sucesos.

    Las 5 primeras comparten estructura (N°, Frecuencia, N° de documento, Fecha,
    Próxima fecha, Observaciones, V°B°). El Historial de Sucesos reutiliza los
    mismos campos: 'descripcion' = Sucesos, 'fecha' = Fecha del suceso,
    'fecha_proxima' = Fecha de solución.
    """
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='registros')
    tipo = models.CharField('Tipo de registro', max_length=25, choices=TIPOS_REGISTRO_EQUIPO)
    frecuencia = models.CharField('Frecuencia', max_length=80, blank=True)
    numero_documento = models.CharField('N° de certificado / informe', max_length=120, blank=True)
    descripcion = models.TextField('Sucesos / detalle', blank=True)
    fecha = models.DateField('Fecha', null=True, blank=True)
    fecha_proxima = models.DateField('Próxima fecha / fecha de solución', null=True, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    vb = models.CharField('V°B° (responsable)', max_length=150, blank=True)
    archivo = models.FileField('Documento adjunto', upload_to='equipos/registros/%Y/',
                               null=True, blank=True)

    class Meta:
        verbose_name = 'Registro de hoja de vida'
        verbose_name_plural = 'Registros de hoja de vida'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.equipo.codigo} — {self.get_tipo_display()} ({self.fecha})'


TIPOS_ACTIVIDAD = [
    ('mantenimiento', 'Mantenimiento'),
    ('calibracion', 'Calibración'),
    ('comprobacion_intermedia', 'Comprobación Intermedia'),
    ('comprobacion_funcional', 'Comprobación Funcional'),
    ('caracterizacion', 'Caracterización'),
]


class ActividadPrograma(AuditableModel):
    """Programa anual de actividades por equipo (MET-PRO-04-r03)."""
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name='actividades')
    tipo = models.CharField('Tipo', max_length=25, choices=TIPOS_ACTIVIDAD)
    anio = models.PositiveIntegerField('Año')
    frecuencia = models.CharField('Frecuencia', max_length=60, blank=True)
    meses = models.JSONField('Meses programados', default=list, blank=True)  # [1..12]

    class Meta:
        verbose_name = 'Actividad programada'
        verbose_name_plural = 'Programa de actividades'
        ordering = ['anio', 'tipo']

    def __str__(self):
        return f'{self.equipo.codigo} — {self.get_tipo_display()} {self.anio}'


MOTIVOS_MOVIMIENTO = [
    ('campo', 'Campo'),
    ('calibracion', 'Calibración'),
    ('reparacion', 'Reparación'),
    ('prestamo', 'Préstamo'),
    ('mantenimiento', 'Mantenimiento'),
    ('otros', 'Otros'),
]

ESTADOS_FISICOS = [
    ('bueno', 'Bueno'),
    ('regular', 'Regular'),
    ('malo', 'Malo'),
]


class MovimientoEquipo(AuditableModel):
    """Control de salida y entrada del equipamiento (MET-PRO-04-r09)."""
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name='movimientos')
    motivo = models.CharField('Motivo de salida', max_length=15, choices=MOTIVOS_MOVIMIENTO)
    destino = models.CharField('Destino', max_length=150, blank=True)
    solicitante = models.CharField('Solicitante', max_length=150, blank=True)
    estado_salida = models.CharField('Estado a la salida', max_length=10, choices=ESTADOS_FISICOS, blank=True)
    fecha_salida = models.DateTimeField('Fecha y hora de salida', null=True, blank=True)
    responsable_salida = models.CharField('Responsable (salida)', max_length=150, blank=True)
    # Retorno
    fecha_retorno = models.DateTimeField('Fecha y hora de retorno', null=True, blank=True)
    estado_retorno = models.CharField('Estado al retorno', max_length=10, choices=ESTADOS_FISICOS, blank=True)
    responsable_retorno = models.CharField('Responsable (retorno)', max_length=150, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        verbose_name = 'Movimiento de equipo'
        verbose_name_plural = 'Movimientos de equipos'
        ordering = ['-id']

    def __str__(self):
        return f'{self.equipo.codigo} — {self.get_motivo_display()}'


TIPOS_INFORME_EQUIPO = [
    ('mantenimiento', 'Informe de Mantenimiento'),
    ('comprobacion_intermedia', 'Informe de Comprobación Intermedia'),
    ('caracterizacion', 'Informe de Caracterización'),
    ('comprobacion_funcional', 'Informe de Comprobación Funcional'),
]

PREFIJO_INFORME = {
    'mantenimiento': 'IM',
    'comprobacion_intermedia': 'ICI',
    'caracterizacion': 'IC',
    'comprobacion_funcional': 'ICF',
}


class InformeEquipo(AuditableModel):
    """
    Informes técnicos del equipo (MET-PRO-04-r05/r06/r07): mantenimiento,
    comprobación intermedia, caracterización. El cálculo metrológico vive en
    el archivo adjunto; el sistema registra el informe y sus datos clave.
    """
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name='informes')
    tipo = models.CharField('Tipo', max_length=25, choices=TIPOS_INFORME_EQUIPO)
    numero = models.CharField('N° de informe', max_length=40, unique=True, editable=False)
    solicitante = models.CharField('Solicitante', max_length=150, blank=True)
    fecha_revision = models.DateField('Fecha de revisión técnica', null=True, blank=True)
    fecha_emision = models.DateField('Fecha de emisión', null=True, blank=True)
    lugar = models.CharField('Lugar', max_length=150, blank=True)
    detalle = models.TextField('Motivo / método / intervención', blank=True)
    conclusiones = models.TextField('Conclusiones / resultados', blank=True)
    conforme = models.BooleanField('Conforme', null=True, blank=True)
    archivo = models.FileField('Archivo del informe / cálculo', upload_to='equipos/informes/%Y/',
                               null=True, blank=True)
    responsable = models.CharField('Responsable', max_length=150, blank=True)

    class Meta:
        verbose_name = 'Informe de equipo'
        verbose_name_plural = 'Informes de equipos'
        ordering = ['-id']

    def __str__(self):
        return self.numero

    @staticmethod
    def generar_numero(tipo, magnitud):
        from django.utils import timezone
        prefijo = PREFIJO_INFORME.get(tipo, 'INF')
        mag = PREFIJO_MAGNITUD.get(magnitud, magnitud).upper()
        anio = timezone.now().year
        base = f'{prefijo}-{mag}-'
        sufijo = f'-{anio}'
        nums = []
        for n in (InformeEquipo.objects.filter(numero__startswith=base, numero__endswith=sufijo)
                  .values_list('numero', flat=True)):
            partes = n.split('-')
            if len(partes) == 4:
                try:
                    nums.append(int(partes[2]))
                except ValueError:
                    pass
        siguiente = max(nums) + 1 if nums else 1
        return f'{prefijo}-{mag}-{siguiente:03d}-{anio}'

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.generar_numero(self.tipo, self.equipo.magnitud)
        super().save(*args, **kwargs)


class CartaTrazabilidad(AuditableModel):
    """Carta de trazabilidad metrológica por magnitud (MET-PRO-04-r04)."""
    magnitud = models.CharField('Magnitud', max_length=20, choices=MAGNITUDES_EQUIPO)
    procedimiento_calibracion = models.CharField('Procedimiento de calibración', max_length=150, blank=True)
    contenido = models.TextField('Contenido / cadena de trazabilidad', blank=True)
    archivo = models.FileField('Archivo', upload_to='equipos/trazabilidad/%Y/', null=True, blank=True)
    fecha_actualizacion = models.DateField('Fecha de actualización', null=True, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Carta de trazabilidad'
        verbose_name_plural = 'Cartas de trazabilidad'
        ordering = ['magnitud']

    def __str__(self):
        return f'Trazabilidad {self.get_magnitud_display()}'
