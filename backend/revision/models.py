"""
Revisión por la dirección del SIG (ISO 9001/14001/45001 9.3 · NTP-ISO/IEC 17025 8.9 · Ley 29783).

- Programa anual: las entradas y salidas de la revisión con su responsable y los meses programados y ejecutados.
- Revisión: preparación (datos del sistema y análisis de cada entrada) → reunión (asistencia firmada, salidas,
  acuerdos, conclusiones) → cerrada. Lo de una etapa cerrada no se modifica (ADR-0005).
- Plan de acción: los acuerdos de cada revisión con responsable, plazo, costo estimado, evidencia, estado y seguimiento
  semestral; se cierran con evidencia y visto bueno.
"""
from django.db import models
from django.utils import timezone

from core.models import AuditableModel

ENTRADAS = [
    ('a', 'Cambios en las cuestiones internas y externas pertinentes al laboratorio y en las necesidades y '
          'expectativas de las partes interesadas'),
    ('b', 'Cumplimiento de objetivos del Sistema Integrado de Gestión, incluidos los objetivos ambientales y de '
          'seguridad y salud en el trabajo'),
    ('c', 'Adecuación de las políticas y procedimientos'),
    ('d', 'Estado de las acciones de revisiones por la dirección anteriores'),
    ('e', 'Resultados de las auditorías internas recientes'),
    ('f', 'Acciones correctivas'),
    ('g', 'Evaluaciones por organismos externos'),
    ('h', 'Cambios en el volumen y tipo de trabajo o en el alcance de actividades del laboratorio'),
    ('i', 'Retroalimentación de los clientes y del personal'),
    ('j', 'Quejas y comunicaciones de las partes interesadas externas'),
    ('k', 'Eficacia de cualquier mejora implementada y oportunidades de mejora identificadas'),
    ('l', 'Adecuación de los recursos'),
    ('m', 'Resultados de la identificación de riesgos y oportunidades, y eficacia de las acciones tomadas para '
          'abordarlos'),
    ('n', 'Resultados del aseguramiento de la validez de los resultados'),
    ('o', 'Otros factores pertinentes, tales como las actividades de seguimiento y la formación'),
    ('p', 'Desempeño de los procesos, conformidad del servicio y resultados del seguimiento y la medición'),
    ('q', 'Desempeño de los proveedores externos'),
    ('r', 'Resultados de la evaluación del cumplimiento de los requisitos legales y otros requisitos'),
    ('s', 'Desempeño ambiental: aspectos ambientales significativos, residuos sólidos, energía eléctrica y agua'),
    ('t', 'Desempeño en seguridad y salud en el trabajo: incidentes, accidentes de trabajo y enfermedades '
          'ocupacionales'),
    ('u', 'Resultados de la identificación de peligros y la evaluación de riesgos de seguridad y salud en el trabajo'),
    ('v', 'Resultados de la consulta y la participación de los trabajadores'),
    ('w', 'Avance del Programa Anual SSOMA, simulacros y monitoreos de agentes ocupacionales'),
]
SALIDAS = [
    ('a', 'La conveniencia, la adecuación y la eficacia del Sistema Integrado de Gestión y de sus procesos'),
    ('b', 'La mejora de las actividades del laboratorio relacionadas con el cumplimiento de los requisitos de la '
          'NTP-ISO/IEC 17025'),
    ('c', 'La provisión de los recursos requeridos'),
    ('d', 'Cualquier necesidad de cambio'),
    ('e', 'Las oportunidades de mejora continua'),
    ('f', 'Las acciones necesarias cuando no se hayan alcanzado los objetivos'),
    ('g', 'Las oportunidades de mejorar la integración del Sistema Integrado de Gestión con otros procesos de negocio'),
    ('h', 'Las implicaciones para la dirección estratégica de la organización'),
    ('i', 'La comunicación de los resultados pertinentes a los trabajadores y al Comité de Seguridad y Salud en el '
          'Trabajo'),
    ('j', 'Otros temas de importancia'),
]
SALIDAS_OBLIGATORIAS = [c for c, _ in SALIDAS if c != 'j']
# Elemento de la revisión que origina un acuerdo: «e-a» (entrada a), «s-c» (salida c)…
ELEMENTOS = [(f'e-{c}', f'Entrada {c}) {t}') for c, t in ENTRADAS] + [(f's-{c}', f'Salida {c}) {t}') for c, t in SALIDAS]
TITULO_ELEMENTO = dict(ELEMENTOS)

TIPOS_REVISION = [('ordinaria', 'Ordinaria'), ('extraordinaria', 'Extraordinaria')]
MOTIVOS_EXTRAORDINARIA = [('contexto', 'Cambios significativos en el contexto'),
                          ('desempeno', 'Resultados críticos del desempeño'), ('normativo', 'Cambios normativos'),
                          ('reguladores', 'Requerimientos de organismos reguladores o de acreditación')]
ESTADOS_REVISION = [('preparacion', 'En preparación'), ('reunion', 'Reunión'), ('cerrada', 'Cerrada'),
                    ('anulada', 'Anulada')]
ESTADOS_ACUERDO = [('abierto', 'Abierto'), ('en_proceso', 'En proceso'), ('cerrado', 'Cerrado')]
# Firmas del informe (bloque de firmas del formato): sigla del puesto o nombre del puesto.
FIRMANTES_INFORME = [('GG', 'Gerente General'), ('GT', 'Gerente Técnico'), ('GCOM', 'Gerente Comercial'),
                     ('GSIG', 'Gerente SIG')]
SIGLAS_OBLIGATORIAS_CIERRE = ['GSIG', 'GG']


def sigla_de_puesto(puesto):
    """Sigla del puesto; si no la tiene, la deduce del nombre para los gerentes del bloque de firmas."""
    if not puesto:
        return ''
    if puesto.sigla:
        return puesto.sigla.upper()
    for sigla, nombre in FIRMANTES_INFORME:
        if puesto.nombre.lower().startswith(nombre.lower()):
            return sigla
    return ''


class ProgramaRevision(AuditableModel):
    anio = models.PositiveIntegerField('Año', unique=True)
    fecha_elaboracion = models.DateField('Fecha de elaboración', default=timezone.localdate)
    observaciones = models.TextField('Observaciones', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Programa de revisión por la dirección'
        ordering = ['-anio']


class ItemProgramaRevision(AuditableModel):
    """Una entrada o salida de la agenda en el programa anual."""
    programa = models.ForeignKey(ProgramaRevision, on_delete=models.PROTECT, related_name='items')
    clave = models.CharField('Elemento', max_length=4, choices=ELEMENTOS)
    responsable = models.ForeignKey('organizacion.Puesto', verbose_name='Responsable de la información',
                                    on_delete=models.PROTECT, null=True, blank=True, related_name='items_revision')
    meses = models.JSONField('Meses programados', default=list, blank=True)
    ejecutados = models.JSONField('Meses ejecutados', default=list, blank=True)
    observaciones = models.CharField('Observaciones', max_length=300, blank=True)

    class Meta:
        verbose_name = 'Elemento del programa de revisión'
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['programa', 'clave'], name='item_programa_revision_unico')]


class Revision(AuditableModel):
    codigo = models.CharField('N° de informe', max_length=16, unique=True, editable=False)
    programa = models.ForeignKey(ProgramaRevision, on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='revisiones')
    tipo = models.CharField('Tipo', max_length=14, choices=TIPOS_REVISION, default='ordinaria')
    motivo_extraordinaria = models.CharField('Motivo (extraordinaria)', max_length=12, choices=MOTIVOS_EXTRAORDINARIA,
                                             blank=True)
    detalle_motivo = models.TextField('Detalle del motivo', blank=True)
    fecha = models.DateField('Fecha de la revisión', null=True, blank=True)
    lugar = models.CharField('Lugar / modalidad', max_length=150, blank=True)
    periodo_desde = models.DateField('Periodo evaluado desde', null=True, blank=True)
    periodo_hasta = models.DateField('Periodo evaluado hasta', null=True, blank=True)
    responsable_recopilacion = models.ForeignKey('organizacion.Trabajador',
                                                 verbose_name='Responsable de la recopilación de la información',
                                                 on_delete=models.PROTECT, null=True, blank=True,
                                                 related_name='revisiones_recopiladas')
    responsable_verificacion = models.ForeignKey('organizacion.Trabajador',
                                                 verbose_name='Responsable de la verificación de la información',
                                                 on_delete=models.PROTECT, null=True, blank=True,
                                                 related_name='revisiones_verificadas')
    conclusiones = models.TextField('Conclusiones', blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    comunicacion_fecha = models.DateField('Comunicación de resultados: fecha', null=True, blank=True)
    comunicacion_detalle = models.TextField('Comunicación de resultados a los trabajadores y al Comité de SST',
                                            blank=True)
    reunion_comite = models.ForeignKey('sst.ReunionComite', verbose_name='Reunión del Comité donde se comunicó',
                                       on_delete=models.PROTECT, null=True, blank=True,
                                       related_name='revisiones_direccion')
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS_REVISION, default='preparacion')
    datos_generados = models.DateTimeField('Datos del sistema generados', null=True, blank=True)
    firma_cierre = models.JSONField('Cierre registrado por', default=dict, blank=True)
    motivo_anulacion = models.TextField('Motivo de la anulación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    # Etapa cerrada = solo lectura (ADR-0005): estados en que cada etapa sigue abierta y campos que captura.
    ETAPAS = (
        ('preparacion', ('preparacion',),
         ('tipo', 'motivo_extraordinaria', 'detalle_motivo', 'fecha', 'lugar', 'periodo_desde', 'periodo_hasta',
          'responsable_recopilacion', 'responsable_verificacion', 'programa')),
        ('reunion', ('reunion',),
         ('conclusiones', 'observaciones', 'comunicacion_fecha', 'comunicacion_detalle', 'reunion_comite')),
    )
    NOMBRES_ETAPA = {'preparacion': 'preparación', 'reunion': 'reunión'}

    class Meta:
        verbose_name = 'Revisión por la dirección'
        verbose_name_plural = 'Revisiones por la dirección'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        if not self.codigo:
            anio = (self.fecha or timezone.localdate()).year
            nums = [int(c.split('-')[1]) for c in Revision.objects.filter(codigo__endswith=f'-{anio}')
                    .values_list('codigo', flat=True) if c.split('-')[1].isdigit()]
            self.codigo = f'IRD-{(max(nums) + 1) if nums else 1:02d}-{anio}'
        super().save(*args, **kwargs)

    def etapas_abiertas(self):
        return [n for n, estados, _ in self.ETAPAS if self.estado in estados]

    @classmethod
    def etapa_de_campo(cls, campo):
        for n, _, campos in cls.ETAPAS:
            if campo in campos:
                return n
        return None


class EntradaRevision(AuditableModel):
    revision = models.ForeignKey(Revision, on_delete=models.PROTECT, related_name='entradas')
    clave = models.CharField('Entrada', max_length=1, choices=ENTRADAS)
    # [{'titulo': str, 'filas': [[etiqueta, valor], …], 'nota': str}] generados de los módulos para el periodo
    datos = models.JSONField('Datos del sistema', default=list, blank=True)
    analisis = models.TextField('Análisis', blank=True)
    sin_actividad = models.BooleanField('Sin actividad en el periodo', default=False)

    class Meta:
        verbose_name = 'Entrada de la revisión'
        ordering = ['clave']
        constraints = [models.UniqueConstraint(fields=['revision', 'clave'], name='entrada_revision_unica')]

    @property
    def completa(self):
        return bool(self.sin_actividad or (self.analisis or '').strip())


class SalidaRevision(AuditableModel):
    revision = models.ForeignKey(Revision, on_delete=models.PROTECT, related_name='salidas')
    clave = models.CharField('Salida', max_length=1, choices=SALIDAS)
    texto = models.TextField('Decisiones y acciones', blank=True)

    class Meta:
        verbose_name = 'Salida de la revisión'
        ordering = ['clave']
        constraints = [models.UniqueConstraint(fields=['revision', 'clave'], name='salida_revision_unica')]


class AsistenteRevision(AuditableModel):
    revision = models.ForeignKey(Revision, on_delete=models.PROTECT, related_name='asistentes')
    trabajador = models.ForeignKey('organizacion.Trabajador', on_delete=models.PROTECT,
                                   related_name='asistencias_revision')
    cargo = models.CharField('Cargo', max_length=150, blank=True)
    sigla = models.CharField('Sigla del puesto', max_length=12, blank=True)
    firma = models.JSONField('Firma de asistencia', default=dict, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Asistente de la revisión'
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['revision', 'trabajador'], condition=models.Q(is_active=True),
                                               name='asistente_revision_unico')]


class AcuerdoRevision(AuditableModel):
    """Acuerdo de la revisión = fila del Plan de Acción."""
    revision = models.ForeignKey(Revision, on_delete=models.PROTECT, related_name='acuerdos')
    numero = models.PositiveIntegerField('N°')
    descripcion = models.TextField('Acuerdo / acción')
    elemento = models.CharField('Elemento de la revisión que lo origina', max_length=4, choices=ELEMENTOS, blank=True)
    responsable = models.ForeignKey('organizacion.Trabajador', verbose_name='Responsable', on_delete=models.PROTECT,
                                    null=True, blank=True, related_name='acuerdos_revision')
    fecha_compromiso = models.DateField('Fecha de cumplimiento', null=True, blank=True)
    costo_estimado = models.DecimalField('Costo estimado (S/)', max_digits=12, decimal_places=2, null=True, blank=True)
    evidencia = models.TextField('Evidencia de ejecución', blank=True)
    archivo_evidencia = models.FileField('Archivo de evidencia', upload_to='revision/evidencias/%Y/', null=True,
                                         blank=True)
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS_ACUERDO, default='abierto')
    seguimiento_1 = models.TextField('Seguimiento 1.er semestre', blank=True)
    seguimiento_2 = models.TextField('Seguimiento 2.º semestre', blank=True)
    fecha_cierre = models.DateField('Fecha de cierre', null=True, blank=True)
    firma_cierre = models.JSONField('V°B° de cumplimiento', default=dict, blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    # Lo que se acuerda en la reunión; tras cerrar la revisión solo cambian el seguimiento, la evidencia y el estado.
    CAMPOS_ACUERDO = ('descripcion', 'elemento', 'responsable', 'fecha_compromiso', 'costo_estimado')
    CAMPOS_SEGUIMIENTO = ('evidencia', 'archivo_evidencia', 'seguimiento_1', 'seguimiento_2')

    class Meta:
        verbose_name = 'Acuerdo de la revisión'
        verbose_name_plural = 'Plan de acción'
        ordering = ['revision', 'numero']

    @property
    def vencido(self):
        return bool(self.estado != 'cerrado' and self.fecha_compromiso and self.fecha_compromiso < timezone.localdate())
