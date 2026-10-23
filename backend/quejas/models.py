"""
M18 — Quejas, según el procedimiento de gestión de quejas: recepción y
registro, validación, evaluación e investigación, decisión, tratamiento y
cierre, con cada comunicación al reclamante registrada y sus plazos.
"""
from datetime import datetime, time, timedelta

from django.db import models
from django.utils import timezone

from core.models import AuditableModel

ESTADOS_QUEJA = [
    ('recibida', 'Recibida'),
    ('en_evaluacion', 'En evaluación'),
    ('en_tratamiento', 'En tratamiento'),
    ('en_cierre', 'En cierre'),
    ('cerrada', 'Cerrada'),
]

RESULTADOS_QUEJA = [
    ('no_relacionada', 'No relacionada con las actividades'),
    ('no_procedente', 'No procedente'),
    ('procedente', 'Procedente'),
]

TIPOS_RECLAMANTE = [
    ('cliente', 'Cliente'),
    ('estado', 'Entidad del Estado'),
    ('regulador', 'Organismo regulador'),
    ('empresa', 'Empresa privada'),
    ('persona', 'Persona natural'),
    ('otro', 'Otra parte interesada'),
]

MEDIOS_RECEPCION = [
    ('telefono', 'Teléfono'),
    ('email', 'Correo electrónico'),
    ('presencial', 'Presencial'),
    ('otros', 'Otros'),
]

ORIGENES_QUEJA = [
    ('comercial', 'Gestión comercial'),
    ('tecnica', 'Gestión técnica'),
    ('logistica', 'Gestión logística'),
]

# Motivos de cada origen, como los enumera el procedimiento.
MOTIVOS_QUEJA = {
    'comercial': [
        'Incumplimiento de las fechas de entrega',
        'Pedido incompleto',
        'Transporte, recepción o entrega de equipos o certificados de calibración',
        'Mala atención al cliente',
        'Falta de respuesta o demora en la resolución de quejas',
        'Otros aspectos de la gestión comercial',
    ],
    'tecnica': [
        'Errores en los certificados de calibración',
        'Errores de digitación en el nombre de la empresa',
        'Errores en marca, modelo, serie o alcance del equipo',
        'Errores en el código de identificación del equipo',
        'Errores en la fecha del certificado',
        'Errores de cálculo',
        'Incumplimiento de especificaciones del servicio de calibración',
        'Otros aspectos de la gestión técnica',
    ],
    'logistica': [
        'Demora en la programación o ejecución del recojo o entrega de equipos',
        'Daños o deterioro de equipos durante el transporte o la manipulación',
        'Pérdida o extravío de equipos, accesorios o documentación del servicio',
        'Entrega incompleta de equipos o accesorios remitidos por el cliente',
        'Problemas de embalaje, almacenamiento o conservación de los equipos en el laboratorio',
        'Falta de comunicación sobre el estado del equipo durante el proceso logístico',
        'Otros aspectos de la gestión logística',
    ],
}

TIPOS_COMUNICACION = [
    ('acuse', 'Acuse de recibo y código'),
    ('validacion', 'Resultado de la validación'),
    ('ampliacion', 'Ampliación del plazo'),
    ('avance', 'Avance del tratamiento'),
    ('informe', 'Informe de resultados de la investigación'),
    ('no_procede', 'Motivos de no procedencia'),
    ('resultado', 'Resultado final del tratamiento'),
]

MEDIOS_COMUNICACION = [
    ('email', 'Correo electrónico'),
    ('whatsapp', 'WhatsApp'),
    ('mensaje', 'Mensaje de texto'),
    ('llamada', 'Llamada telefónica'),
    ('presencial', 'Presencial'),
    ('otro', 'Otro'),
]

CONFORMIDAD_CLIENTE = [
    ('conforme', 'Conforme'),
    ('no_conforme', 'No conforme'),
    ('sin_respuesta', 'Sin respuesta del cliente'),
]


def sumar_dias_habiles(fecha, dias):
    """Fecha luego de `dias` días hábiles (lunes a viernes)."""
    f = fecha
    while dias > 0:
        f += timedelta(days=1)
        if f.weekday() < 5:
            dias -= 1
    return f


class Queja(AuditableModel):
    """Queja de un cliente u otra parte interesada (código RQ-NNN-AAAA)."""
    codigo = models.CharField('N° de queja', max_length=20, unique=True, editable=False)
    estado = models.CharField('Estado', max_length=20, choices=ESTADOS_QUEJA, default='recibida')
    resultado = models.CharField('Resultado', max_length=20, choices=RESULTADOS_QUEJA, blank=True)

    # 1. Recepción y registro
    fecha_recepcion = models.DateTimeField('Fecha de recepción', default=timezone.now)
    recibido_por = models.ForeignKey('core.Usuario', verbose_name='Recibido por', on_delete=models.PROTECT,
                                     related_name='quejas_recibidas', null=True, blank=True)
    tipo_reclamante = models.CharField('Tipo de reclamante', max_length=15, choices=TIPOS_RECLAMANTE,
                                       default='cliente')
    empresa = models.CharField('Nombre de la empresa', max_length=200)
    contacto = models.CharField('Representante o persona de contacto', max_length=150, blank=True)
    contacto_email = models.EmailField('Correo del contacto', blank=True)
    contacto_telefono = models.CharField('Teléfono del contacto', max_length=40, blank=True)
    orden_trabajo = models.CharField('N° de orden de trabajo', max_length=60, blank=True)
    medio_recepcion = models.CharField('Medio de recepción', max_length=15, choices=MEDIOS_RECEPCION)
    medio_otro = models.CharField('Otro medio', max_length=100, blank=True)
    origen = models.CharField('Origen', max_length=15, choices=ORIGENES_QUEJA)
    motivo = models.CharField('Motivo de la queja', max_length=200)
    desde_encuesta = models.BooleanField('Originada en una encuesta de satisfacción', default=False)
    descripcion = models.TextField('Descripción de la queja')

    # 2. Validación
    relacionada = models.BooleanField('¿Relacionada con las actividades?', null=True, blank=True)
    motivo_validacion = models.TextField('Sustento de la validación', blank=True)
    fecha_validacion = models.DateTimeField('Fecha de validación', null=True, blank=True)
    validado_por = models.ForeignKey('core.Usuario', verbose_name='Validado por', on_delete=models.PROTECT,
                                     related_name='quejas_validadas', null=True, blank=True)

    # 3. Evaluación e investigación
    responsables = models.ManyToManyField('core.Usuario', verbose_name='Responsables de la evaluación',
                                          related_name='quejas_evaluadas', blank=True)
    involucrados = models.ManyToManyField('core.Usuario', verbose_name='Personal involucrado en el origen',
                                          related_name='quejas_involucrado', blank=True)
    fecha_evaluacion = models.DateField('Fecha de evaluación', null=True, blank=True)
    evaluacion = models.TextField('Evaluación de la queja', blank=True)
    investigacion = models.TextField('Investigación / análisis de causas', blank=True)
    dentro_alcance = models.BooleanField('¿Dentro del alcance acreditado?', null=True, blank=True)
    plazo_ampliado = models.BooleanField('Plazo ampliado', default=False)
    motivo_ampliacion = models.TextField('Motivo de la ampliación', blank=True)
    fecha_compromiso = models.DateField('Nueva fecha comprometida', null=True, blank=True)
    cliente_solicita_informe = models.BooleanField('El cliente solicita informe de resultados', default=False)

    # 4. Decisión
    fundamento_decision = models.TextField('Fundamento de la decisión', blank=True)
    fecha_decision = models.DateTimeField('Fecha de decisión', null=True, blank=True)
    decidido_por = models.ForeignKey('core.Usuario', verbose_name='Decidido por', on_delete=models.PROTECT,
                                     related_name='quejas_decididas', null=True, blank=True)

    # 5. Tratamiento
    acciones = models.TextField('Acciones a realizar', blank=True)
    responsable_acciones = models.ForeignKey('core.Usuario', verbose_name='Responsable de las acciones',
                                             on_delete=models.PROTECT, related_name='quejas_a_cargo',
                                             null=True, blank=True)
    hallazgo = models.ForeignKey('esynapse_sig.Hallazgo', verbose_name='No conformidad registrada',
                                 on_delete=models.PROTECT, related_name='quejas', null=True, blank=True)
    requiere_tnc = models.BooleanField('Se trata como trabajo no conforme', default=False)
    certificado_original = models.CharField('Certificado reemplazado', max_length=60, blank=True)
    certificado_nuevo = models.CharField('Nuevo certificado', max_length=60, blank=True)
    seguimiento = models.TextField('Seguimiento de las acciones', blank=True)
    fecha_seguimiento = models.DateField('Fecha del seguimiento', null=True, blank=True)

    # 6. Cierre (conformidad del cliente)
    comunicacion_cliente = models.TextField('Comunicación al cliente', blank=True)
    medio_cierre = models.CharField('Medio de la comunicación', max_length=15, choices=MEDIOS_COMUNICACION,
                                    blank=True)
    conformidad_cliente = models.CharField('Conformidad del cliente', max_length=15, choices=CONFORMIDAD_CLIENTE,
                                           blank=True)
    fecha_cierre = models.DateTimeField('Fecha de cierre', null=True, blank=True)
    notificado_por = models.ForeignKey('core.Usuario', verbose_name='Notificado por', on_delete=models.PROTECT,
                                       related_name='quejas_notificadas', null=True, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    # Reaperturas: [{fecha, usuario, motivo, estado_anterior}]
    reaperturas = models.JSONField('Reaperturas', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    # Etapa cerrada = solo lectura: cada etapa declara en qué estados sigue
    # abierta y qué campos captura (los de etapas futuras no se adelantan).
    ETAPAS = (
        ('registro', ('recibida',),
         ('fecha_recepcion', 'recibido_por', 'tipo_reclamante', 'empresa', 'contacto', 'contacto_email',
          'contacto_telefono', 'orden_trabajo', 'medio_recepcion', 'medio_otro', 'origen', 'motivo',
          'desde_encuesta', 'descripcion')),
        ('evaluacion', ('en_evaluacion',),
         ('responsables', 'involucrados', 'fecha_evaluacion', 'evaluacion', 'investigacion', 'dentro_alcance',
          'plazo_ampliado', 'motivo_ampliacion', 'fecha_compromiso', 'cliente_solicita_informe')),
        ('tratamiento', ('en_tratamiento',),
         ('acciones', 'responsable_acciones', 'requiere_tnc', 'certificado_original', 'certificado_nuevo',
          'seguimiento', 'fecha_seguimiento')),
        ('cierre', ('en_cierre',), ('comunicacion_cliente', 'medio_cierre', 'conformidad_cliente', 'observaciones')),
    )
    NOMBRES_ETAPA = {'registro': 'recepción y registro', 'evaluacion': 'evaluación e investigación',
                     'tratamiento': 'tratamiento', 'cierre': 'cierre'}

    class Meta:
        verbose_name = 'Queja'
        verbose_name_plural = 'Quejas'
        ordering = ['-fecha_recepcion', '-id']

    def __str__(self):
        return f'{self.codigo} — {self.empresa}'

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
        for cod in Queja.objects.filter(codigo__startswith='RQ-', codigo__endswith=f'-{anio}').values_list(
                'codigo', flat=True):
            partes = cod.split('-')
            if len(partes) == 3 and partes[1].isdigit():
                nums.append(int(partes[1]))
        return f'RQ-{(max(nums) + 1 if nums else 1):03d}-{anio}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo(timezone.localtime(self.fecha_recepcion).year)
        super().save(*args, **kwargs)

    @property
    def abierta(self):
        return self.estado != 'cerrada'

    def plazos(self):
        """Plazos del procedimiento: acuse (24 h), resultado de la validación
        (2 días hábiles, o la fecha comprometida si se amplió) e informe de
        resultados (7 días hábiles desde la validación, si el cliente lo pide)."""
        ahora = timezone.now()
        coms = list(self.comunicaciones.filter(is_active=True))

        def primera(*tipos):
            fechas = [c.fecha for c in coms if c.tipo in tipos]
            return min(fechas) if fechas else None

        def estado(limite_dt, cumplido):
            if cumplido:
                return 'cumplido' if cumplido <= limite_dt else 'cumplido_tarde'
            if self.estado == 'cerrada':
                return 'no_registrado'
            if ahora > limite_dt:
                return 'vencido'
            if limite_dt - ahora <= timedelta(hours=24):
                return 'por_vencer'
            return 'a_tiempo'

        def fin_de_dia(fecha):
            return timezone.make_aware(datetime.combine(fecha, time(23, 59, 59)))

        salida = []
        lim = self.fecha_recepcion + timedelta(hours=24)
        hecho = primera('acuse')
        salida.append({'clave': 'acuse', 'nombre': 'Acuse de recibo (24 h)', 'limite': lim, 'cumplido': hecho,
                       'estado': estado(lim, hecho)})
        base = timezone.localtime(self.fecha_recepcion).date()
        lim_v = fin_de_dia(self.fecha_compromiso if (self.plazo_ampliado and self.fecha_compromiso)
                           else sumar_dias_habiles(base, 2))
        hecho = primera('validacion', 'no_procede', 'resultado')
        salida.append({'clave': 'validacion', 'nombre': 'Resultado de la validación (2 días hábiles)',
                       'limite': lim_v, 'cumplido': hecho, 'estado': estado(lim_v, hecho)})
        if self.cliente_solicita_informe and self.fecha_validacion:
            lim_i = fin_de_dia(sumar_dias_habiles(timezone.localtime(self.fecha_validacion).date(), 7))
            hecho = primera('informe')
            salida.append({'clave': 'informe', 'nombre': 'Informe de resultados (7 días hábiles)',
                           'limite': lim_i, 'cumplido': hecho, 'estado': estado(lim_i, hecho)})
        return salida


class ComunicacionQueja(AuditableModel):
    """Comunicación al reclamante (acuse, validación, avances, informe, cierre)."""
    queja = models.ForeignKey(Queja, on_delete=models.PROTECT, related_name='comunicaciones')
    tipo = models.CharField('Tipo', max_length=15, choices=TIPOS_COMUNICACION)
    fecha = models.DateTimeField('Fecha', default=timezone.now)
    medio = models.CharField('Medio', max_length=15, choices=MEDIOS_COMUNICACION)
    resumen = models.TextField('Resumen de lo comunicado')
    evidencia = models.FileField('Evidencia', upload_to='quejas/comunicaciones/%Y/', null=True, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Comunicación de queja'
        verbose_name_plural = 'Comunicaciones de quejas'
        ordering = ['fecha', 'id']


class AdjuntoQueja(AuditableModel):
    """Documento que sustenta la queja o su investigación."""
    queja = models.ForeignKey(Queja, on_delete=models.PROTECT, related_name='adjuntos')
    archivo = models.FileField('Archivo', upload_to='quejas/adjuntos/%Y/')
    descripcion = models.CharField('Descripción', max_length=200, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Adjunto de queja'
        verbose_name_plural = 'Adjuntos de quejas'
        ordering = ['id']
