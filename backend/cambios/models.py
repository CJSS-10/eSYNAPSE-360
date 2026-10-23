"""
M17 — Cambios, según el procedimiento de control de cambios: solicitud,
evaluación de la viabilidad e impactos, resolución del Gerente General,
planificación, implementación con comunicación, verificación de la eficacia
(con reversión si no fue eficaz) y cierre. Un cambio temporal eficaz queda «en
vigor» hasta que se registra su fin (con prórrogas firmadas por el Gerente General).
"""
from django.db import models
from django.utils import timezone

from core.models import AuditableModel

ESTADOS_CAMBIO = [
    ('solicitado', 'Solicitado'),
    ('en_evaluacion', 'En evaluación'),
    ('en_aprobacion', 'En aprobación'),
    ('rechazado', 'Rechazado'),
    ('archivado', 'Archivado'),
    ('en_planificacion', 'En planificación'),
    ('en_implementacion', 'En implementación'),
    ('en_verificacion', 'En verificación de eficacia'),
    ('temporal_vigente', 'Temporal en vigor'),
    ('cerrado', 'Cerrado'),
]

PRIORIDADES = [('alta', 'Alta'), ('media', 'Media'), ('baja', 'Baja')]
CLASIFICACIONES = [('mayor', 'Cambio mayor'), ('menor', 'Cambio menor')]
ORIGENES = [('interno', 'Cambio interno'), ('externo', 'Cambio externo')]

# Origen del cambio, como los enumera el procedimiento.
MOTIVOS_ORIGEN = {
    'interno': ['Nuevos procesos', 'Modificación de procedimientos', 'Cambios organizacionales',
                'Acciones correctivas', 'Riesgos identificados', 'Cambios de infraestructura',
                'Incorporación de equipos', 'Cambios tecnológicos', 'Modificaciones de software',
                'Cambios metodológicos', 'Otros'],
    'externo': ['Requisitos legales', 'Requisitos normativos', 'Cambios regulatorios', 'Requisitos de INACAL',
                'Requisitos del cliente', 'Avances tecnológicos', 'Cambios del mercado', 'Otros'],
}

# Impactos que se evalúan (procedimiento: análisis de la viabilidad del cambio).
IMPACTOS = [
    ('calidad', 'Calidad: procesos, requisitos del cliente, conformidad del servicio, riesgos y oportunidades'),
    ('ambiental', 'Ambiental: aspectos e impactos, residuos, consumo de recursos, emisiones, cumplimiento legal'),
    ('sst', 'SST: peligros, riesgos, controles operacionales, ergonomía, contratistas, sustancias (actualizar IPERC)'),
    ('tecnico', 'Técnico 17025: competencia, procedimientos de calibración, métodos, equipos y patrones, software, '
                'trazabilidad, incertidumbre, condiciones ambientales, validez de resultados'),
    ('imparcialidad', 'Riesgos a la imparcialidad'),
    ('acreditacion', 'Alcance acreditado y requisitos de acreditación'),
    ('legal', 'Requisitos legales y normativos'),
]

PREVISION = [('previsto', 'Previsto'), ('no_previsto', 'No previsto')]
TEMPORALIDAD = [('temporal', 'Temporal'), ('permanente', 'Permanente')]

# Fuente u origen del cambio (formato de planificación).
FUENTES_PLANIFICACION = [
    ('nuevos_procesos', 'Introducción de nuevos procesos'),
    ('metodos_trabajo', 'Cambios en los métodos de trabajo'),
    ('nuevos_proyectos', 'Ejecución de nuevos proyectos'),
    ('nueva_legislacion', 'Identificación de nueva legislación'),
    ('personal_clave', 'Personal clave'),
    ('tecnologia', 'Cambios de tecnología'),
    ('accidente', 'Accidente laboral grave o mortal'),
    ('evento_catastrofico', 'Evento catastrófico, recuperación post-contingencias'),
    ('infraestructura', 'Cambios de infraestructura, instalaciones o equipos'),
    ('requisitos_cliente', 'Requisitos del cliente, especificaciones'),
]

# Lo que se verifica de la eficacia (procedimiento: validar la eficacia del cambio).
CRITERIOS_EFICACIA = [
    ('resultado', 'El cambio logró el resultado esperado'),
    ('calidad', 'No se afectó la calidad del servicio'),
    ('validez', 'No se afectó la validez de los resultados'),
    ('riesgos', 'No se generaron riesgos no previstos'),
    ('legal', 'Se mantiene la conformidad legal y normativa'),
    ('acreditacion', 'Se mantiene la conformidad con los requisitos de acreditación'),
]

# Reversión por ineficacia (no el fin previsto de un cambio temporal, que se registra aparte).
REVERSIONES = [('ninguna', 'Sin reversión'), ('parcial', 'Reversión parcial'), ('total', 'Reversión total')]

DESTINATARIOS = [
    ('personal', 'Personal involucrado'),
    ('clientes', 'Clientes'),
    ('proveedores', 'Proveedores'),
    ('contratistas', 'Contratistas'),
    ('otras', 'Otras partes interesadas'),
]
MEDIOS = [('email', 'Correo electrónico'), ('reunion', 'Reunión'), ('comunicado', 'Comunicado interno'),
          ('whatsapp', 'WhatsApp'), ('llamada', 'Llamada telefónica'), ('otro', 'Otro')]
MOMENTOS_FOTO = [('antes', 'Antes del cambio'), ('durante', 'Durante el cambio'), ('despues', 'Después del cambio')]


class Cambio(AuditableModel):
    """Solicitud de cambio y su ciclo completo (código SC-NNN-AAAA)."""
    codigo = models.CharField('N° de solicitud', max_length=20, unique=True, editable=False)
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS_CAMBIO, default='solicitado')

    # 1. Solicitud
    solicitante = models.ForeignKey('core.Usuario', verbose_name='Solicitante', on_delete=models.PROTECT,
                                    related_name='cambios_solicitados', null=True, blank=True)
    proceso_solicitante = models.ForeignKey('procesos.Proceso', verbose_name='Proceso solicitante',
                                            on_delete=models.PROTECT, related_name='cambios_solicitados',
                                            null=True, blank=True)
    fecha_solicitud = models.DateField('Fecha de solicitud', default=timezone.localdate)
    prioridad = models.CharField('Prioridad', max_length=6, choices=PRIORIDADES, default='media')
    origen = models.CharField('Origen', max_length=8, choices=ORIGENES, default='interno')
    motivo_origen = models.CharField('Motivo del origen', max_length=80, blank=True)
    descripcion = models.TextField('Descripción del cambio')
    justificacion = models.TextField('Justificación del cambio', blank=True)
    sac_origen = models.ForeignKey('esynapse_sig.SolicitudAC', verbose_name='Acción correctiva que lo origina',
                                   on_delete=models.PROTECT, related_name='cambios_originados', null=True, blank=True)

    # 2. Evaluación (Área SIG)
    factibilidad_tecnica = models.TextField('Factibilidad técnica', blank=True)
    aspectos_operativos = models.TextField('Aspectos operativos', blank=True)
    aspectos_financieros = models.TextField('Aspectos financieros', blank=True)
    procesos_afectados = models.ManyToManyField('procesos.Proceso', verbose_name='Procesos afectados', blank=True,
                                                related_name='cambios_que_lo_afectan')
    alcance = models.TextField('Alcance del cambio (detalle)', blank=True)
    beneficios = models.TextField('Beneficios del cambio', blank=True)
    impactos = models.JSONField('Impactos evaluados', default=list, blank=True,
                                help_text='Claves de IMPACTOS que aplican')
    riesgos = models.TextField('Riesgos e impactos identificados', blank=True)
    controles = models.TextField('Controles establecidos', blank=True)
    consecuencias = models.TextField('Consecuencias de no realizarlo', blank=True)
    clasificacion = models.CharField('Clasificación', max_length=6, choices=CLASIFICACIONES, blank=True)
    es_tecnico = models.BooleanField('Cambio técnico (afecta la parte técnica del laboratorio)', default=False)
    afecta_clientes = models.BooleanField('Afecta requisitos acordados con clientes o actividades acreditadas',
                                          default=False)
    responsable_evaluador = models.ForeignKey('core.Usuario', verbose_name='Responsable del equipo evaluador',
                                              on_delete=models.PROTECT, related_name='cambios_evaluados',
                                              null=True, blank=True)
    equipo_evaluador = models.ManyToManyField('core.Usuario', verbose_name='Equipo evaluador', blank=True,
                                              related_name='cambios_equipo_evaluador')

    # 3. Resolución (Gerente General)
    resultado = models.CharField('Resolución', max_length=10, blank=True,
                                 choices=[('aprobado', 'Aprobado'), ('rechazado', 'Rechazado')])
    resuelto_por = models.ForeignKey('core.Usuario', verbose_name='Aprobado / rechazado por',
                                     on_delete=models.PROTECT, related_name='cambios_resueltos', null=True, blank=True)
    fecha_resolucion = models.DateTimeField('Fecha de resolución', null=True, blank=True)
    motivo_resolucion = models.TextField('Comentarios de la resolución', blank=True)
    firma_resolucion = models.JSONField('Firma de la resolución', default=dict, blank=True)
    # Rechazos y reevaluaciones: [{fecha, usuario, accion, motivo}]
    historial = models.JSONField('Historial de resoluciones', default=list, blank=True)

    # 4. Planificación
    fecha_planificacion = models.DateField('Fecha de planificación', null=True, blank=True)
    prevision = models.CharField('Previsto / no previsto', max_length=12, choices=PREVISION, blank=True)
    temporalidad = models.CharField('Temporal / permanente', max_length=10, choices=TEMPORALIDAD, blank=True)
    fecha_reversion = models.DateField('Fecha prevista de reversión (temporal)', null=True, blank=True)
    fuentes = models.JSONField('Fuente u origen del cambio', default=list, blank=True)
    fuente_otro = models.CharField('Otra fuente', max_length=150, blank=True)
    responsable_implementacion = models.ForeignKey('core.Usuario', verbose_name='Responsable del equipo de implementación',
                                                   on_delete=models.PROTECT, related_name='cambios_implementados',
                                                   null=True, blank=True)
    plazo_implementacion = models.DateField('Plazo de implementación', null=True, blank=True)
    equipo_implementacion = models.ManyToManyField('core.Usuario', verbose_name='Equipo de implementación',
                                                   blank=True, related_name='cambios_equipo_implementacion')

    # 5. Implementación
    fecha_inicio_implementacion = models.DateTimeField('Inicio de la implementación', null=True, blank=True)
    documentos_actualizados = models.ManyToManyField('esynapse_sig.Documento', verbose_name='Documentos actualizados',
                                                     blank=True, related_name='cambios')

    # 7. Eficacia y reversión por ineficacia
    se_implemento = models.BooleanField('¿Se implementó?', null=True, blank=True)
    fue_eficaz = models.BooleanField('¿Fue eficaz?', null=True, blank=True)
    criterios_eficacia = models.JSONField('Criterios verificados', default=list, blank=True)
    verificacion = models.TextField('Verificación de la eficacia', blank=True)
    reversion = models.CharField('Reversión', max_length=8, choices=REVERSIONES, default='ninguna')
    detalle_reversion = models.TextField('Detalle de la reversión', blank=True)
    fecha_reversion_real = models.DateField('Fecha de la reversión', null=True, blank=True)
    sac_derivada = models.ForeignKey('esynapse_sig.SolicitudAC', verbose_name='Acción correctiva derivada',
                                     on_delete=models.PROTECT, related_name='cambios_derivados', null=True, blank=True)
    fecha_verificacion = models.DateTimeField('Fecha de verificación', null=True, blank=True)
    verificado_por = models.ForeignKey('core.Usuario', verbose_name='Verificado por', on_delete=models.PROTECT,
                                       related_name='cambios_verificados', null=True, blank=True)

    # 7b. Cambio temporal en vigor: prórrogas y fin del cambio temporal
    # Prórrogas: [{fecha, usuario, sigla, ip, fecha_anterior, fecha_nueva, motivo}]
    prorrogas = models.JSONField('Prórrogas del cambio temporal', default=list, blank=True)
    fin_temporal_fecha = models.DateField('Fecha de fin del cambio temporal', null=True, blank=True)
    fin_temporal_detalle = models.TextField('Qué se restituyó al terminar el cambio temporal', blank=True)
    fin_temporal_evidencia = models.FileField('Evidencia del fin del cambio temporal',
                                              upload_to='cambios/fin_temporal/%Y/', null=True, blank=True)
    fin_temporal_por = models.ForeignKey('core.Usuario', verbose_name='Fin del cambio temporal registrado por',
                                         on_delete=models.PROTECT, related_name='cambios_temporales_terminados',
                                         null=True, blank=True)
    cambio_origen = models.ForeignKey('self', verbose_name='Cambio temporal que se vuelve permanente',
                                      on_delete=models.PROTECT, related_name='cambios_permanentes',
                                      null=True, blank=True)

    # 8. Cierre
    cerrado_por = models.ForeignKey('core.Usuario', verbose_name='Cerrado por', on_delete=models.PROTECT,
                                    related_name='cambios_cerrados', null=True, blank=True)
    fecha_cierre = models.DateTimeField('Fecha de cierre', null=True, blank=True)
    reaperturas = models.JSONField('Reaperturas', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    # Etapa cerrada = solo lectura: cada etapa declara en qué estados sigue
    # abierta y qué campos captura.
    ETAPAS = (
        ('solicitud', ('solicitado',),
         ('solicitante', 'proceso_solicitante', 'fecha_solicitud', 'prioridad', 'origen', 'motivo_origen',
          'descripcion', 'justificacion', 'sac_origen')),
        ('evaluacion', ('en_evaluacion',),
         ('factibilidad_tecnica', 'aspectos_operativos', 'aspectos_financieros', 'procesos_afectados', 'alcance',
          'beneficios', 'impactos', 'riesgos', 'controles', 'consecuencias', 'clasificacion', 'es_tecnico',
          'afecta_clientes', 'responsable_evaluador', 'equipo_evaluador')),
        ('planificacion', ('en_planificacion',),
         ('fecha_planificacion', 'prevision', 'temporalidad', 'fecha_reversion', 'fuentes', 'fuente_otro',
          'responsable_implementacion', 'plazo_implementacion', 'equipo_implementacion')),
        ('implementacion', ('en_implementacion',), ('documentos_actualizados',)),
        ('verificacion', ('en_verificacion',),
         ('se_implemento', 'fue_eficaz', 'criterios_eficacia', 'verificacion', 'reversion', 'detalle_reversion',
          'fecha_reversion_real', 'sac_derivada')),
        ('fin_temporal', ('temporal_vigente',), ('fin_temporal_fecha', 'fin_temporal_detalle')),
    )
    NOMBRES_ETAPA = {'solicitud': 'solicitud', 'evaluacion': 'evaluación', 'planificacion': 'planificación',
                     'implementacion': 'implementación', 'verificacion': 'verificación de la eficacia',
                     'fin_temporal': 'fin del cambio temporal'}

    class Meta:
        verbose_name = 'Cambio'
        verbose_name_plural = 'Cambios'
        ordering = ['-fecha_solicitud', '-id']

    def __str__(self):
        return f'{self.codigo} — {self.descripcion[:60]}'

    def etapas_abiertas(self):
        return [nombre for nombre, estados, _ in self.ETAPAS if self.estado in estados]

    @classmethod
    def etapa_de_campo(cls, campo):
        for nombre, _, campos in cls.ETAPAS:
            if campo in campos:
                return nombre
        return None

    @staticmethod
    def generar_codigo(anio):
        nums = []
        for cod in Cambio.objects.filter(codigo__startswith='SC-', codigo__endswith=f'-{anio}').values_list(
                'codigo', flat=True):
            partes = cod.split('-')
            if len(partes) == 3 and partes[1].isdigit():
                nums.append(int(partes[1]))
        return f'SC-{(max(nums) + 1 if nums else 1):03d}-{anio}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo(self.fecha_solicitud.year)
        super().save(*args, **kwargs)

    @property
    def requiere_planificacion(self):
        """Cambio mayor o técnico: la planificación detallada es obligatoria."""
        return self.clasificacion == 'mayor' or self.es_tecnico

    @property
    def queda_en_vigor(self):
        """Al confirmar la eficacia, un cambio temporal que no se revirtió por completo sigue en vigor."""
        return self.temporalidad == 'temporal' and self.reversion != 'total'

    @property
    def reversion_vencida(self):
        """Cambio temporal cuya fecha prevista de fin pasó sin registrarse."""
        return bool(self.temporalidad == 'temporal' and self.fecha_reversion and not self.fin_temporal_fecha
                    and self.estado in ('en_implementacion', 'en_verificacion', 'temporal_vigente')
                    and self.reversion != 'total' and self.fecha_reversion < timezone.localdate())


class _Fila(AuditableModel):
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        abstract = True


class ActividadCambio(_Fila):
    """Actividad del plan de ejecución / planificación del cambio."""
    cambio = models.ForeignKey(Cambio, on_delete=models.PROTECT, related_name='actividades')
    orden = models.PositiveIntegerField('Orden', default=0)
    actividad = models.TextField('Actividad')
    responsable = models.ForeignKey('core.Usuario', verbose_name='Responsable', on_delete=models.PROTECT,
                                    related_name='actividades_cambio', null=True, blank=True)
    recursos = models.CharField('Recursos', max_length=255, blank=True)
    plazo = models.DateField('Plazo', null=True, blank=True)
    seguimiento = models.TextField('Seguimiento', blank=True)
    completada = models.BooleanField('Completada', default=False)
    fecha_completada = models.DateTimeField('Fecha de cumplimiento', null=True, blank=True)
    evidencia = models.FileField('Evidencia', upload_to='cambios/evidencias/%Y/', null=True, blank=True)

    class Meta:
        ordering = ['orden', 'id']


class ComunicacionCambio(_Fila):
    """Comunicación del cambio a una parte interesada."""
    cambio = models.ForeignKey(Cambio, on_delete=models.PROTECT, related_name='comunicaciones')
    destinatario = models.CharField('Destinatario', max_length=15, choices=DESTINATARIOS)
    fecha = models.DateField('Fecha', default=timezone.localdate)
    medio = models.CharField('Medio', max_length=12, choices=MEDIOS)
    resumen = models.TextField('Qué se comunicó')
    evidencia = models.FileField('Evidencia', upload_to='cambios/comunicaciones/%Y/', null=True, blank=True)

    class Meta:
        ordering = ['fecha', 'id']


class FotoCambio(_Fila):
    """Registro fotográfico antes, durante y después del cambio."""
    cambio = models.ForeignKey(Cambio, on_delete=models.PROTECT, related_name='fotos')
    momento = models.CharField('Momento', max_length=8, choices=MOMENTOS_FOTO)
    archivo = models.FileField('Foto', upload_to='cambios/fotos/%Y/')
    descripcion = models.CharField('Descripción', max_length=200, blank=True)

    class Meta:
        ordering = ['momento', 'id']
