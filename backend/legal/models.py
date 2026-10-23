"""
M2 — Requisitos legales y otros requisitos, según el procedimiento de
identificación, acceso y evaluación de requisitos legales: lista de requisitos
por ámbito, obligaciones (artículos a cumplir) y evaluación periódica del
cumplimiento; los incumplimientos se tratan como hallazgos.
"""
from django.db import models
from django.utils import timezone

from core.models import AuditableModel

AMBITOS = [
    ('sst', 'Seguridad y Salud en el Trabajo'),
    ('ma', 'Medio Ambiente'),
    ('sociolaboral', 'Obligaciones Sociolaborales'),
    ('acreditacion', 'Acreditación'),
    ('otros', 'Otros requisitos'),
]
ESTADOS_REQUISITO = [('vigente', 'Vigente'), ('derogada', 'Derogada')]
RESULTADOS = [('pendiente', 'Pendiente'), ('cumple', 'Cumple'), ('no_cumple', 'No cumple'), ('no_aplica', 'No aplica')]
ESTADOS_EVALUACION = [('en_curso', 'En curso'), ('cerrada', 'Cerrada')]
MEDIOS = [('correo', 'Correo formal'), ('reunion', 'Reunión'), ('publicacion', 'Publicación en el SIG'), ('otro', 'Otro')]

# Escala del resumen de cumplimiento (hoja de gráficos del formato).
def calificacion(porcentaje):
    if porcentaje is None:
        return ''
    if porcentaje > 80:
        return 'bueno'
    if porcentaje >= 70:
        return 'regular'
    return 'malo'


class Requisito(AuditableModel):
    """Norma o documento de la lista de requisitos legales y otros requisitos."""
    ambito = models.CharField('Ámbito', max_length=14, choices=AMBITOS)
    tema = models.CharField('Tema', max_length=150, blank=True)
    orden = models.PositiveIntegerField('Ítem', default=0)
    tipo = models.CharField('Tipo', max_length=120, blank=True, help_text='Ley, Decreto Supremo, Resolución…')
    codigo = models.CharField('Código / número', max_length=120, blank=True)
    nombre = models.TextField('Nombre del documento')
    fecha_aprobacion = models.CharField('Fecha de aprobación', max_length=20, blank=True)
    modificatorias = models.TextField('Revisión / modificatorias', blank=True)
    observaciones = models.CharField('Observaciones', max_length=255, blank=True)
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS_REQUISITO, default='vigente')
    procesos = models.ManyToManyField('procesos.Proceso', verbose_name='Procesos involucrados', blank=True,
                                      related_name='requisitos_legales')
    aplicabilidad = models.TextField('Aplicabilidad y consecuencias del incumplimiento', blank=True)
    fecha_identificacion = models.DateField('Fecha de identificación', default=timezone.localdate)
    fecha_derogacion = models.DateField('Fecha de derogación', null=True, blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Requisito legal'
        verbose_name_plural = 'Requisitos legales'
        ordering = ['ambito', 'orden', 'id']

    def __str__(self):
        return f'{self.tipo} {self.codigo} — {self.nombre[:60]}'.strip()

    @property
    def denominacion(self):
        return ' '.join(x for x in (self.tipo, self.codigo) if x).strip()


class Obligacion(AuditableModel):
    """Artículo a cumplir (fila de la matriz de evaluación de cumplimiento legal)."""
    ambito = models.CharField('Ámbito', max_length=14, choices=AMBITOS)
    tema = models.CharField('Tema', max_length=150, blank=True)
    orden = models.PositiveIntegerField('Orden', default=0)
    requisito = models.ForeignKey(Requisito, verbose_name='Requisito', on_delete=models.PROTECT, null=True,
                                  blank=True, related_name='obligaciones')
    documento_legal = models.TextField('Documento legal asociado', blank=True)
    articulo = models.CharField('N° de artículo', max_length=120, blank=True)
    extracto = models.TextField('Extracto del artículo a cumplir')
    evidencia_documento = models.TextField('Documento / registro que evidencia el cumplimiento', blank=True)
    proceso_sede = models.CharField('Proceso / sede', max_length=150, blank=True)
    procesos = models.ManyToManyField('procesos.Proceso', verbose_name='Procesos', blank=True,
                                      related_name='obligaciones_legales')
    responsable = models.CharField('Responsable', max_length=150, blank=True)
    periodicidad = models.CharField('Periodicidad del monitoreo', max_length=80, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS_REQUISITO, default='vigente')
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Obligación legal'
        verbose_name_plural = 'Obligaciones legales'
        ordering = ['ambito', 'orden', 'id']

    @property
    def documento(self):
        return self.requisito.denominacion if self.requisito_id else self.documento_legal


class ComunicacionRequisito(AuditableModel):
    """Comunicación de un requisito a las áreas involucradas."""
    requisito = models.ForeignKey(Requisito, on_delete=models.PROTECT, related_name='comunicaciones')
    fecha = models.DateField('Fecha', default=timezone.localdate)
    medio = models.CharField('Medio', max_length=12, choices=MEDIOS)
    destinatarios = models.CharField('Destinatarios', max_length=255)
    resumen = models.TextField('Obligaciones, impactos y acciones comunicadas')
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        ordering = ['-fecha', '-id']


class Evaluacion(AuditableModel):
    """Evaluación periódica del cumplimiento de un ámbito (semestral)."""
    ambito = models.CharField('Ámbito', max_length=14, choices=AMBITOS)
    anio = models.PositiveIntegerField('Año')
    periodo = models.CharField('Periodo', max_length=40, help_text='Semestre 1, Semestre 2…')
    orden = models.PositiveSmallIntegerField('Orden en el año', default=1)
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS_EVALUACION, default='en_curso')
    fecha_inicio = models.DateField('Inicio', default=timezone.localdate)
    fecha_cierre = models.DateTimeField('Cierre', null=True, blank=True)
    cerrada_por = models.ForeignKey('core.Usuario', verbose_name='Cerrada por', on_delete=models.PROTECT,
                                    null=True, blank=True, related_name='evaluaciones_legales_cerradas')
    firma = models.JSONField('Firma del cierre', default=dict, blank=True)
    historica = models.BooleanField('Cargada de la matriz anterior', default=False)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Evaluación de cumplimiento legal'
        verbose_name_plural = 'Evaluaciones de cumplimiento legal'
        ordering = ['-anio', '-orden', 'ambito']

    def __str__(self):
        return f'{self.get_ambito_display()} · {self.anio} · {self.periodo}'

    def resumen(self):
        """Cumplen / no cumplen / no aplica / pendientes y % de cumplimiento (como el formato)."""
        cuenta = {k: 0 for k, _ in RESULTADOS}
        for r in self.resultados.all():
            cuenta[r.resultado] += 1
        evaluadas = cuenta['cumple'] + cuenta['no_cumple']
        pct = round(100 * cuenta['cumple'] / evaluadas, 1) if evaluadas else None
        return {**cuenta, 'evaluadas': evaluadas, 'porcentaje': pct, 'calificacion': calificacion(pct)}


class ResultadoEvaluacion(AuditableModel):
    """Resultado de una obligación en una evaluación."""
    evaluacion = models.ForeignKey(Evaluacion, on_delete=models.PROTECT, related_name='resultados')
    obligacion = models.ForeignKey(Obligacion, on_delete=models.PROTECT, related_name='resultados')
    resultado = models.CharField('Resultado', max_length=10, choices=RESULTADOS, default='pendiente')
    observaciones = models.TextField('Evidencia / observaciones', blank=True)
    evidencia = models.FileField('Archivo de evidencia', upload_to='legal/evidencias/%Y/', null=True, blank=True)
    evaluado_por = models.ForeignKey('core.Usuario', verbose_name='Evaluado por', on_delete=models.PROTECT,
                                     null=True, blank=True, related_name='resultados_legales')
    fecha = models.DateField('Fecha', null=True, blank=True)
    hallazgo = models.ForeignKey('esynapse_sig.Hallazgo', verbose_name='Hallazgo por incumplimiento',
                                 on_delete=models.PROTECT, null=True, blank=True, related_name='incumplimientos_legales')

    class Meta:
        unique_together = [('evaluacion', 'obligacion')]
        ordering = ['obligacion__orden', 'obligacion__id']


class ActualizacionAmbito(models.Model):
    """Fechas de actualización de la lista y de la matriz de cada ámbito (cabecera de los formatos)."""
    ambito = models.CharField('Ámbito', max_length=14, choices=AMBITOS, unique=True)
    fecha_lista = models.DateField('Actualización de la lista', null=True, blank=True)
    fecha_matriz = models.DateField('Actualización de la matriz', null=True, blank=True)

    @classmethod
    def tocar(cls, ambito, lista=False, matriz=False):
        a, _ = cls.objects.get_or_create(ambito=ambito)
        hoy = timezone.localdate()
        if lista:
            a.fecha_lista = hoy
        if matriz:
            a.fecha_matriz = hoy
        a.save()
