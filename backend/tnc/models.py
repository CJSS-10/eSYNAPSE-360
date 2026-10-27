"""
Trabajos y salidas no conformes (NTP-ISO/IEC 17025 7.10 · ISO 9001 8.7).

Etapas: registro → tratamiento (acciones, corrección, análisis de impacto retroactivo) → autorización de la
reanudación → evaluación de la importancia (Área SIG) → cierre. Lo de una etapa cerrada no se modifica (ADR-0005).
"""
from datetime import timedelta

from django.db import models
from django.utils import timezone

from core.models import AuditableModel

TIPOS = [('tnc', 'Trabajo no conforme'), ('snc', 'Salida no conforme')]
NATURALEZAS = [('tecnica', 'Técnica'), ('administrativa', 'Administrativa')]
CATEGORIAS = [('equipo', 'Equipo o patrón'), ('personal', 'Competencia del personal'),
              ('ambiente', 'Condiciones ambientales'), ('metodo', 'Método o procedimiento'),
              ('resultado', 'Certificado o resultados'), ('administrativo', 'Administrativo'), ('otro', 'Otro')]
FUENTES = [('queja', 'Queja del cliente'), ('calibracion', 'Problemas con la calibración'),
           ('verificacion', 'Verificación de certificados'), ('control_calidad', 'Control de calidad interno'),
           ('consumibles', 'Control de materiales consumibles'), ('equipos', 'Estado de los equipos'),
           ('competencia', 'Competencia del personal'), ('supervision', 'Observación o supervisión'),
           ('no_conformidad', 'No conformidad'), ('otros', 'Otros')]
NIVELES = [('alto', 'Alto'), ('medio', 'Medio'), ('bajo', 'Bajo')]
ACCIONES = [('detencion', 'Detención del trabajo'), ('repeticion', 'Repetición del trabajo'),
            ('retencion', 'Retención de documentos'), ('notificacion', 'Notificación al cliente'),
            ('retroactivo', 'Análisis de impacto retroactivo'), ('fuera_servicio', 'Equipo fuera de servicio')]
ACCIONES_AFECTACION = [('retener', 'Retener'), ('anular_reemitir', 'Anular y reemitir'), ('ninguna', 'Ninguna')]
ESTADOS = [('registrado', 'Registrado'), ('tratamiento', 'En tratamiento'), ('autorizacion', 'Por autorizar'),
           ('evaluacion', 'En evaluación'), ('cierre', 'Por cerrar'), ('cerrado', 'Cerrado'), ('anulado', 'Anulado')]
EVENTOS_PARA_SAC = 3
MESES_SIMILARES = 12


def acciones_vacias():
    return {c: {'aplica': None, 'ejecutada': None} for c, _ in ACCIONES}


class TrabajoNoConforme(AuditableModel):
    codigo = models.CharField('N° de registro', max_length=16, unique=True, editable=False)
    # Registro
    tipo = models.CharField('Tipo', max_length=3, choices=TIPOS, default='tnc')
    naturaleza = models.CharField('Naturaleza', max_length=14, choices=NATURALEZAS, default='tecnica')
    categoria = models.CharField('Categoría del incidente', max_length=14, choices=CATEGORIAS)
    area = models.ForeignKey('organizacion.Area', verbose_name='Área o laboratorio', on_delete=models.PROTECT,
                             related_name='trabajos_no_conformes')
    reportado_por = models.ForeignKey('organizacion.Trabajador', verbose_name='Reportado por',
                                      on_delete=models.PROTECT, related_name='tnc_reportados')
    fecha_deteccion = models.DateField('Fecha de detección')
    fecha_reporte = models.DateField('Fecha de reporte al Gerente SIG y Gerente Técnico', null=True, blank=True)
    fuente = models.CharField('Fuente de detección', max_length=16, choices=FUENTES)
    queja = models.ForeignKey('quejas.Queja', verbose_name='Queja de origen', on_delete=models.PROTECT,
                              null=True, blank=True, related_name='trabajos_no_conformes')
    hallazgo = models.ForeignKey('esynapse_sig.Hallazgo', verbose_name='No conformidad de origen',
                                 on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='trabajos_no_conformes')
    referencias = models.CharField('OT / certificado / equipo', max_length=300, blank=True)
    equipos = models.ManyToManyField('esynapse_sig.Equipo', verbose_name='Equipos involucrados', blank=True,
                                     related_name='trabajos_no_conformes')
    descripcion = models.TextField('Descripción del TNC o SNC')
    nivel_riesgo = models.CharField('Nivel de riesgo', max_length=5, choices=NIVELES, blank=True)
    firma_nivel = models.JSONField('Nivel asignado por', default=dict, blank=True)
    # Tratamiento
    responsable_tratamiento = models.ForeignKey('organizacion.Trabajador', verbose_name='Responsable del tratamiento',
                                                on_delete=models.PROTECT, null=True, blank=True,
                                                related_name='tnc_a_cargo')
    acciones = models.JSONField('Acciones: ¿aplica? / ¿ejecutada?', default=acciones_vacias, blank=True)
    correccion = models.TextField('Corrección del TNC o SNC', blank=True)
    correccion_por = models.ForeignKey('organizacion.Trabajador', verbose_name='Corrección realizada por',
                                       on_delete=models.PROTECT, null=True, blank=True,
                                       related_name='tnc_corregidos')
    correccion_fecha = models.DateField('Fecha de la corrección', null=True, blank=True)
    nota_cliente = models.TextField('Nota del cliente', blank=True)
    # Análisis de impacto retroactivo y notificación al cliente
    periodo_desde = models.DateField('Periodo revisado desde', null=True, blank=True)
    periodo_hasta = models.DateField('Periodo revisado hasta', null=True, blank=True)
    ultima_condicion = models.CharField('Última condición conforme', max_length=200, blank=True)
    notificacion_cliente = models.TextField('Notificación al cliente', blank=True)
    notificacion_fecha_medio = models.CharField('Notificación: fecha y medio', max_length=150, blank=True)
    certificado_anulado = models.CharField('Certificado anulado N°', max_length=150, blank=True)
    certificado_reemplazo = models.CharField('Certificado de reemplazo N°', max_length=150, blank=True)
    conclusion_retroactivo = models.TextField('Conclusión del análisis de impacto retroactivo', blank=True)
    # Autorización para la reanudación
    acepta = models.BooleanField('¿Acepta el TNC o SNC corregido como conforme?', null=True, blank=True)
    sustento_autorizacion = models.TextField('Sustento de la autorización', blank=True)
    asignado_a = models.ForeignKey('organizacion.Trabajador', verbose_name='Reanudación asignada a',
                                   on_delete=models.PROTECT, null=True, blank=True, related_name='tnc_asignados')
    firma_autorizacion = models.JSONField('Autorizado por', default=dict, blank=True)
    # Evaluación de la importancia (Área SIG)
    afecta_validez = models.BooleanField('¿Afecta la validez de los resultados?', null=True, blank=True)
    incumple_sig = models.BooleanField('¿Incumple requisitos y alcances del SIG?', null=True, blank=True)
    compromete_competencia = models.BooleanField('¿Compromete la competencia técnica del laboratorio?', null=True,
                                                 blank=True)
    nivel_confirmado = models.CharField('Nivel de riesgo confirmado', max_length=5, choices=NIVELES, blank=True)
    evaluacion = models.TextField('Evaluación de la importancia', blank=True)
    eventos_similares = models.PositiveIntegerField('N° de eventos similares (12 meses)', null=True, blank=True)
    registros_similares = models.JSONField('Registros similares', default=list, blank=True)
    amerita_sac = models.BooleanField('¿Amerita la solicitud de una acción correctiva?', null=True, blank=True)
    sac = models.ForeignKey('esynapse_sig.SolicitudAC', verbose_name='Solicitud de acción correctiva',
                            on_delete=models.PROTECT, null=True, blank=True, related_name='trabajos_no_conformes')
    firma_evaluacion = models.JSONField('Evaluación realizada por', default=dict, blank=True)
    # Cierre
    evidencias = models.TextField('Evidencias archivadas', blank=True)
    firma_cierre = models.JSONField('Cerrado por', default=dict, blank=True)
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS, default='registrado')
    motivo_anulacion = models.TextField('Motivo de la anulación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    ETAPAS = (
        ('registro', ('registrado',),
         ('tipo', 'naturaleza', 'categoria', 'area', 'reportado_por', 'fecha_deteccion', 'fecha_reporte', 'fuente',
          'queja', 'hallazgo', 'referencias', 'equipos', 'descripcion')),
        ('tratamiento', ('tratamiento',),
         ('responsable_tratamiento', 'acciones', 'correccion', 'correccion_por', 'correccion_fecha', 'nota_cliente',
          'periodo_desde', 'periodo_hasta', 'ultima_condicion', 'notificacion_cliente', 'notificacion_fecha_medio',
          'certificado_anulado', 'certificado_reemplazo', 'conclusion_retroactivo')),
        ('autorizacion', ('autorizacion',), ('acepta', 'sustento_autorizacion', 'asignado_a')),
        ('evaluacion', ('evaluacion',),
         ('afecta_validez', 'incumple_sig', 'compromete_competencia', 'nivel_confirmado', 'evaluacion',
          'amerita_sac')),
        ('cierre', ('cierre',), ('sac', 'evidencias')),
    )
    NOMBRES_ETAPA = {'registro': 'registro', 'tratamiento': 'tratamiento', 'autorizacion': 'autorización',
                     'evaluacion': 'evaluación de la importancia', 'cierre': 'cierre'}

    class Meta:
        verbose_name = 'Trabajo o salida no conforme'
        verbose_name_plural = 'Trabajos y salidas no conformes'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        if not self.codigo:
            anio = (self.fecha_deteccion or timezone.localdate()).year
            nums = [int(c.split('-')[1]) for c in TrabajoNoConforme.objects.filter(codigo__endswith=f'-{anio}')
                    .values_list('codigo', flat=True) if c.split('-')[1].isdigit()]
            self.codigo = f'TSNC-{(max(nums) + 1) if nums else 1:03d}-{anio}'
        super().save(*args, **kwargs)

    def etapas_abiertas(self):
        return [n for n, estados, _ in self.ETAPAS if self.estado in estados]

    @classmethod
    def etapa_de_campo(cls, campo):
        for n, _, campos in cls.ETAPAS:
            if campo in campos:
                return n
        return None

    def similares(self):
        """TNC/SNC de la misma área y categoría en los últimos 12 meses hasta la detección (incluye este)."""
        desde = self.fecha_deteccion - timedelta(days=365)
        return TrabajoNoConforme.objects.filter(is_active=True, area_id=self.area_id, categoria=self.categoria,
                                                fecha_deteccion__gt=desde, fecha_deteccion__lte=self.fecha_deteccion) \
            .exclude(estado='anulado').order_by('fecha_deteccion', 'id')

    def sac_obligatoria(self):
        nivel = self.nivel_confirmado or self.nivel_riesgo
        return nivel == 'alto' or (self.eventos_similares or 0) >= EVENTOS_PARA_SAC

    def accion(self, clave):
        return (self.acciones or {}).get(clave) or {}


class AfectacionTNC(AuditableModel):
    """Fila del análisis de impacto retroactivo: una OT y su certificado."""
    tnc = models.ForeignKey(TrabajoNoConforme, on_delete=models.PROTECT, related_name='afectaciones')
    ot = models.CharField('N° OT', max_length=40, blank=True)
    certificado = models.CharField('N° certificado', max_length=60, blank=True)
    entregado = models.BooleanField('¿Entregado?', default=False)
    afectado = models.BooleanField('¿Afectado?', default=False)
    accion = models.CharField('Acción', max_length=16, choices=ACCIONES_AFECTACION, default='ninguna')
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'OT o certificado revisado'
        ordering = ['id']


class AdjuntoTNC(AuditableModel):
    tnc = models.ForeignKey(TrabajoNoConforme, on_delete=models.PROTECT, related_name='adjuntos')
    archivo = models.FileField('Archivo', upload_to='tnc/%Y/')
    descripcion = models.CharField('Descripción', max_length=200, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Evidencia del TNC o SNC'
        ordering = ['id']
