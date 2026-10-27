"""
M11 Cumplimiento: evaluación, requisito por requisito, del cumplimiento de ISO 9001, ISO 14001, ISO 45001 y
NTP ISO/IEC 17025, con evidencia automática de los módulos, correspondencia entre normas y cortes para ver la
evolución. El catálogo de requisitos es el de Auditorías (no se cargan las normas otra vez); los requisitos de otras
fuentes (organismo de acreditación, entidad certificadora, clientes) se registran aquí.
"""
from datetime import timedelta

from django.db import models
from django.utils import timezone

from core.models import AuditableModel
from esynapse_sig.models import NORMAS_APLICABLES

NORMAS = NORMAS_APLICABLES
NORMAS_ISO = ('iso_9001', 'iso_14001', 'iso_45001')

ESTADOS = [
    ('sin_evaluar', 'Sin evaluar'),
    ('cumple', 'Cumple'),
    ('parcial', 'Parcial'),
    ('no_cumple', 'No cumple'),
    ('no_aplica', 'No aplica'),
]
PUNTAJE = {'cumple': 100, 'parcial': 50, 'no_cumple': 0}
MESES_VIGENCIA_EVALUACION = 12

FUENTES_ADICIONAL = [
    ('acreditacion', 'Organismo de acreditación'),
    ('certificacion', 'Entidad certificadora'),
    ('cliente', 'Cliente'),
    ('otro', 'Otro'),
]

# Estructura de alto nivel común a ISO 9001, 14001 y 45001: estas cláusulas se evalúan una vez y se reflejan en las
# otras normas. La 8.2 solo coincide entre 14001 y 45001 (en 9001 es «Requisitos para los productos y servicios»).
CLAUSULAS_COMUNES = {'4.1', '4.2', '4.3', '4.4', '5.1', '5.2', '5.3', '6.1', '6.2', '7.1', '7.2', '7.3', '7.4',
                     '7.5', '8.1', '9.1', '9.2', '9.3', '10.1', '10.2', '10.3'}
COMUNES_8_2 = ('iso_14001', 'iso_45001')


def normas_equivalentes(norma, codigo):
    """Otras normas ISO en las que la misma cláusula es común (para reflejar la evaluación)."""
    if norma not in NORMAS_ISO:
        return []
    if codigo in CLAUSULAS_COMUNES:
        return [n for n in NORMAS_ISO if n != norma]
    if codigo == '8.2' and norma in COMUNES_8_2:
        return [n for n in COMUNES_8_2 if n != norma]
    return []


class RequisitoAdicional(AuditableModel):
    """Requisito que no es de una norma del catálogo: directrices del organismo de acreditación, de la entidad
    certificadora, de clientes u otros que el laboratorio suscribe."""
    fuente = models.CharField('Fuente', max_length=15, choices=FUENTES_ADICIONAL)
    referencia = models.CharField('Documento de referencia', max_length=200,
                                  help_text='p. ej. directriz, política o contrato que lo establece')
    codigo = models.CharField('Código o numeral', max_length=40, blank=True)
    texto = models.TextField('Requisito')
    norma = models.CharField('Norma relacionada', max_length=12, choices=NORMAS, blank=True)
    orden = models.PositiveIntegerField('Orden', default=0)
    is_active = models.BooleanField('Activo', default=True)
    motivo_baja = models.CharField('Motivo de la baja', max_length=300, blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Otro requisito'
        verbose_name_plural = 'Otros requisitos'
        ordering = ['fuente', 'orden', 'id']

    def __str__(self):
        return f'{self.referencia} {self.codigo}'.strip()


class EvaluacionRequisito(AuditableModel):
    """Estado de cumplimiento de un requisito (de norma o adicional). Una por requisito; cada cambio queda en el
    historial."""
    requisito = models.OneToOneField('esynapse_sig.RequisitoNorma', verbose_name='Requisito de norma',
                                     on_delete=models.PROTECT, null=True, blank=True, related_name='cumplimiento')
    adicional = models.OneToOneField(RequisitoAdicional, verbose_name='Otro requisito', on_delete=models.PROTECT,
                                     null=True, blank=True, related_name='evaluacion')
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS, default='sin_evaluar')
    justificacion = models.TextField('Justificación de no aplica', blank=True)
    proceso = models.ForeignKey('procesos.Proceso', verbose_name='Proceso responsable', on_delete=models.PROTECT,
                                null=True, blank=True, related_name='requisitos_cumplimiento')
    como_se_cumple = models.TextField('Cómo se cumple', blank=True)
    documentos = models.ManyToManyField('esynapse_sig.Documento', verbose_name='Documentos que lo sustentan',
                                        blank=True, related_name='requisitos_cumplimiento')
    evidencia = models.TextField('Evidencia', blank=True)
    fecha_evaluacion = models.DateField('Fecha de la última evaluación', null=True, blank=True)
    evaluado_por = models.ForeignKey('core.Usuario', verbose_name='Evaluado por', on_delete=models.PROTECT,
                                     null=True, blank=True, related_name='evaluaciones_cumplimiento')
    hallazgo = models.ForeignKey('esynapse_sig.Hallazgo', verbose_name='Hallazgo de la brecha',
                                 on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='requisitos_cumplimiento')
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Evaluación de cumplimiento'
        verbose_name_plural = 'Evaluaciones de cumplimiento'
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(requisito__isnull=False, adicional__isnull=True)
                           | models.Q(requisito__isnull=True, adicional__isnull=False)),
                name='cumplimiento_un_solo_requisito'),
        ]

    def __str__(self):
        return f'{self.requisito or self.adicional} · {self.get_estado_display()}'

    @property
    def vencida(self):
        """La evaluación tiene más de 12 meses."""
        if not self.fecha_evaluacion:
            return False
        return self.fecha_evaluacion < timezone.localdate() - timedelta(days=round(MESES_VIGENCIA_EVALUACION * 30.44))


class EvaluacionSede(AuditableModel):
    """Evaluación individual de un requisito en una sede, independiente de la del SIG completo y de la otra sede
    (César, 2026-10-27): cada una tiene su propia calificación."""
    evaluacion = models.ForeignKey(EvaluacionRequisito, verbose_name='Evaluación', on_delete=models.PROTECT,
                                   related_name='sedes')
    sede = models.ForeignKey('organizacion.Sede', verbose_name='Sede', on_delete=models.PROTECT,
                             related_name='evaluaciones_cumplimiento')
    estado = models.CharField('Estado en la sede', max_length=12, choices=ESTADOS, default='sin_evaluar')
    observacion = models.TextField('Cómo se cumple / evidencia en la sede', blank=True)
    fecha_evaluacion = models.DateField('Fecha', null=True, blank=True)
    evaluado_por = models.ForeignKey('core.Usuario', verbose_name='Evaluado por', on_delete=models.PROTECT,
                                     null=True, blank=True, related_name='evaluaciones_cumplimiento_sede')

    class Meta:
        verbose_name = 'Evaluación por sede'
        verbose_name_plural = 'Evaluaciones por sede'
        constraints = [models.UniqueConstraint(fields=['evaluacion', 'sede'], name='cumplimiento_una_por_sede')]

    def __str__(self):
        return f'{self.evaluacion} · {self.sede} · {self.get_estado_display()}'

    @property
    def vencida(self):
        if not self.fecha_evaluacion:
            return False
        return self.fecha_evaluacion < timezone.localdate() - timedelta(days=round(MESES_VIGENCIA_EVALUACION * 30.44))


class CorteCumplimiento(AuditableModel):
    """Fotografía del grado de cumplimiento por norma en una fecha, para ver la evolución."""
    fecha = models.DateField('Fecha del corte')
    resultados = models.JSONField('Resultados por norma', default=dict)
    observaciones = models.TextField('Observaciones', blank=True)
    firma = models.JSONField('Registrado por', default=dict, blank=True)

    class Meta:
        verbose_name = 'Corte de cumplimiento'
        verbose_name_plural = 'Cortes de cumplimiento'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'Corte {self.fecha}'
