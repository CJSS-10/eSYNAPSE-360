"""
M23 — Seguridad y Salud en el Trabajo: matriz IPERC (identificación de peligros,
evaluación de riesgos y controles) y Análisis de Trabajo Seguro (ATS), según el
procedimiento de identificación de peligros, evaluación de riesgos y controles.
Los puestos y las áreas vienen de Organización y personal (núcleo).
"""
from django.db import models
from django.utils import timezone

from core.models import AuditableModel

SITUACIONES = [('rutinaria', 'Rutinaria'), ('no_rutinaria', 'No rutinaria'), ('emergencia', 'Emergencia')]

# Nivel de riesgo = índice de probabilidad (A+B+C+D) × índice de severidad.
NIVELES_IPERC = [('T', 'Trivial'), ('TO', 'Tolerable'), ('M', 'Moderado'), ('IM', 'Importante'), ('IT', 'Intolerable')]
ACCION_NIVEL = {
    'T': 'No requiere acción.', 'TO': 'No requiere mejoras, salvo las más rentables.',
    'M': 'Requiere reducción o controles periódicos.', 'IM': 'No se inicia el trabajo hasta reducir el riesgo.',
    'IT': 'No se permite realizar el trabajo.',
}


def nivel_iperc(valor):
    if not valor:
        return ''
    if valor <= 4:
        return 'T'
    if valor <= 8:
        return 'TO'
    if valor <= 16:
        return 'M'
    if valor <= 24:
        return 'IM'
    return 'IT'


def es_aceptable(nivel):
    return nivel in ('T', 'TO', 'M') if nivel else None


class PeligroCatalogo(models.Model):
    """Tabla de peligros y riesgos (anexo de la matriz IPERC), para elegir al registrar."""
    clase = models.CharField('Clase', max_length=60, blank=True)
    codigo = models.CharField('Código', max_length=20, blank=True)
    peligro = models.CharField('Peligro', max_length=200)
    riesgo = models.CharField('Riesgo / evento peligroso', max_length=255, blank=True)
    consecuencia = models.TextField('Consecuencias', blank=True)

    class Meta:
        ordering = ['clase', 'codigo', 'peligro']


class FilaIPERC(AuditableModel):
    """Fila de la matriz IPERC: peligro de una actividad, su evaluación y sus controles."""
    codigo = models.CharField('Código', max_length=12, unique=True, editable=False)
    area = models.CharField('Hoja de la matriz', max_length=120)
    unidad = models.ForeignKey('organizacion.Area', verbose_name='Área del organigrama', on_delete=models.PROTECT,
                               null=True, blank=True, related_name='filas_iperc')
    proceso = models.ForeignKey('procesos.Proceso', verbose_name='Proceso', on_delete=models.PROTECT, null=True,
                                blank=True, related_name='filas_iperc')
    subproceso = models.CharField('Subproceso', max_length=200, blank=True)
    puestos = models.ManyToManyField('organizacion.Puesto', verbose_name='Puestos expuestos', blank=True,
                                     related_name='filas_iperc')
    todos_los_puestos = models.BooleanField('Aplica a todos los puestos', default=False)
    puestos_texto = models.CharField('Puestos (como figura en la matriz)', max_length=255, blank=True)
    actividad = models.TextField('Actividad / tarea')
    peligro = models.TextField('Peligro')
    riesgo = models.TextField('Riesgo')
    consecuencia = models.TextField('Consecuencia del riesgo', blank=True)
    situaciones = models.JSONField('Situación', default=list, blank=True,
                                   help_text='rutinaria, no_rutinaria y/o emergencia')
    controles_existentes = models.TextField('Controles existentes', blank=True)
    requisito_legal = models.TextField('Requisito legal asociado', blank=True)

    # Evaluación inicial: índices 1–3.
    personas = models.PositiveSmallIntegerField('Personas expuestas (A)', null=True, blank=True)
    procedimientos = models.PositiveSmallIntegerField('Procedimientos existentes (B)', null=True, blank=True)
    capacitacion = models.PositiveSmallIntegerField('Capacitación (C)', null=True, blank=True)
    exposicion = models.PositiveSmallIntegerField('Exposición al riesgo (D)', null=True, blank=True)
    severidad = models.PositiveSmallIntegerField('Índice de severidad', null=True, blank=True)

    # Controles por jerarquía.
    control_eliminacion = models.TextField('Eliminación', blank=True)
    control_sustitucion = models.TextField('Sustitución', blank=True)
    control_ingenieria = models.TextField('Controles de ingeniería', blank=True)
    control_administrativo = models.TextField('Controles administrativos', blank=True)
    control_epp = models.TextField('Equipo de protección personal', blank=True)
    responsables = models.ManyToManyField('organizacion.Puesto', verbose_name='Responsable(s) de los controles',
                                          blank=True, related_name='filas_iperc_responsable')
    responsable = models.CharField('Responsable (como figura en la matriz)', max_length=200, blank=True)

    # Evaluación residual.
    r_personas = models.PositiveSmallIntegerField('Residual A', null=True, blank=True)
    r_procedimientos = models.PositiveSmallIntegerField('Residual B', null=True, blank=True)
    r_capacitacion = models.PositiveSmallIntegerField('Residual C', null=True, blank=True)
    r_exposicion = models.PositiveSmallIntegerField('Residual D', null=True, blank=True)
    r_severidad = models.PositiveSmallIntegerField('Residual severidad', null=True, blank=True)

    estado = models.CharField('Estado', max_length=10, choices=[('vigente', 'Vigente'), ('retirado', 'Retirado')],
                              default='vigente')
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    CAMPOS_A = ('personas', 'procedimientos', 'capacitacion', 'exposicion')
    CAMPOS_R = ('r_personas', 'r_procedimientos', 'r_capacitacion', 'r_exposicion')

    class Meta:
        verbose_name = 'Fila IPERC'
        verbose_name_plural = 'Matriz IPERC'
        ordering = ['area', 'codigo']

    def __str__(self):
        return f'{self.codigo} — {self.peligro[:50]}'

    @staticmethod
    def siguiente_codigo():
        nums = [int(c[4:]) for c in FilaIPERC.objects.values_list('codigo', flat=True) if c[4:].isdigit()]
        return f'IPR-{(max(nums) + 1) if nums else 1:03d}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.siguiente_codigo()
        super().save(*args, **kwargs)

    def _prob(self, campos):
        vals = [getattr(self, c) for c in campos]
        return sum(vals) if all(vals) else None

    @property
    def probabilidad(self):
        return self._prob(self.CAMPOS_A)

    @property
    def nivel_riesgo(self):
        p = self.probabilidad
        return p * self.severidad if p and self.severidad else None

    @property
    def clasificacion(self):
        return nivel_iperc(self.nivel_riesgo)

    @property
    def aceptable(self):
        return es_aceptable(self.clasificacion)

    @property
    def r_probabilidad(self):
        return self._prob(self.CAMPOS_R)

    @property
    def r_nivel_riesgo(self):
        p = self.r_probabilidad
        return p * self.r_severidad if p and self.r_severidad else None

    @property
    def r_clasificacion(self):
        return nivel_iperc(self.r_nivel_riesgo)

    @property
    def r_aceptable(self):
        return es_aceptable(self.r_clasificacion)

    @property
    def tiene_controles(self):
        return any((self.control_eliminacion, self.control_sustitucion, self.control_ingenieria,
                    self.control_administrativo, self.control_epp))

    @property
    def situacion_control(self):
        """controlado / sin_evaluar / requiere_control / trabajo_detenido."""
        if not self.clasificacion:
            return 'sin_evaluar'
        if self.aceptable:
            return 'controlado'
        if self.r_clasificacion and self.r_aceptable:
            return 'controlado'
        if not self.tiene_controles or not self.r_clasificacion:
            return 'requiere_control'
        return 'trabajo_detenido'


class RevisionIPERC(AuditableModel):
    """Actualización / revisión de la matriz IPERC de un área, con firma."""
    area = models.CharField('Área', max_length=120)
    fecha = models.DateField('Fecha', default=timezone.localdate)
    usuario = models.ForeignKey('core.Usuario', verbose_name='Responsable', on_delete=models.PROTECT, null=True,
                                blank=True, related_name='revisiones_iperc')
    nombre = models.CharField('Responsable (texto)', max_length=150, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    firma = models.JSONField('Firma', default=dict, blank=True)

    class Meta:
        ordering = ['-fecha', '-id']

    @property
    def responsable_nombre(self):
        if self.usuario_id:
            return self.usuario.get_full_name() or self.usuario.username
        return self.nombre


class AprobacionIPERC(AuditableModel):
    """Aprobación de la matriz IPERC por el Comité de SST ("realizado y aprobado por"): una o varias hojas a la vez,
    con la firma de cada miembro titular (contraseña si tiene usuario, PIN si no) o el acta firmada en papel adjunta.
    Si una fila del área cambia después, el área queda pendiente de una nueva aprobación."""
    fecha = models.DateField('Fecha de aprobación', default=timezone.localdate)
    areas = models.JSONField('Hojas aprobadas', default=list)
    reunion = models.ForeignKey('sst.ReunionComite', verbose_name='Reunión del comité', on_delete=models.PROTECT,
                                null=True, blank=True, related_name='aprobaciones_iperc')
    # [{miembro_id, trabajador_id, nombre, cargo, metodo (usuario / pin / papel / carga), fecha}]
    firmas = models.JSONField('Firmas del comité', default=list)
    archivo = models.FileField('Acta firmada en papel', upload_to='sst/iperc/aprobaciones/', null=True, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    registro = models.JSONField('Registrado por', default=dict, blank=True)

    class Meta:
        verbose_name = 'Aprobación de la matriz IPERC'
        verbose_name_plural = 'Aprobaciones de la matriz IPERC'
        ordering = ['-fecha', '-id']


def estado_aprobacion_iperc(area):
    """(estado, aprobación): 'aprobada', 'pendiente' (cambió después de aprobarse) o 'sin_aprobar'."""
    ap = next((a for a in AprobacionIPERC.objects.all() if area in (a.areas or [])), None)
    if not ap:
        return 'sin_aprobar', None
    cambio = FilaIPERC.objects.filter(area=area, updated_at__gt=ap.created_at).exists()
    return ('pendiente' if cambio else 'aprobada'), ap


# --- Análisis de Trabajo Seguro (escala propia del formato: severidad 1–4 × probabilidad 1–4) ---
TIPOS_TRABAJO = [('altura', 'Trabajo en altura'), ('electrico', 'Trabajo eléctrico'), ('caliente', 'Trabajo en caliente'),
                 ('confinado', 'Espacio confinado'), ('quimicos', 'Productos químicos'), ('izaje', 'Izaje'),
                 ('excavaciones', 'Excavaciones y zanjas'), ('otro', 'Otro')]
ESTADOS_ATS = [('borrador', 'En preparación'), ('en_campo', 'En campo'), ('recibido', 'Recibido'),
               ('revisado', 'Revisado'), ('validado', 'Validado'), ('anulado', 'Anulado')]
LUGARES_ATS = [('instalaciones', 'Instalaciones de Metrindust'), ('campo', 'En campo (instalaciones del cliente)')]
FORMATOS_ATS = [('metrindust', 'Formato de Metrindust'), ('cliente', 'Formato del cliente')]
# Datos que se pueden transcribir mientras el ATS está en campo (lo que cambió en el lugar).
CAMPOS_EN_CAMPO = ('ejecutantes', 'comentarios', 'equipos', 'fecha', 'hora_inicio', 'hora_fin', 'responsable_cliente',
                   'ssoma_cliente', 'filas_iperc')


def nivel_ats(valor):
    if not valor:
        return ''
    if valor <= 2:
        return 'tolerable'
    if valor <= 6:
        return 'poco_significativo'
    if valor <= 9:
        return 'significativo'
    return 'intolerable'


NIVELES_ATS = [('tolerable', 'Tolerable'), ('poco_significativo', 'Poco significativo'),
               ('significativo', 'Significativo'), ('intolerable', 'Intolerable')]


class ATSTipo(AuditableModel):
    """ATS base de un servicio (etapas, peligros, medidas y evaluación típicas), para preparar los ATS."""
    nombre = models.CharField('Servicio / nombre', max_length=150, unique=True)
    descripcion = models.TextField('Descripción', blank=True)
    tipos_trabajo = models.JSONField('Tipo de trabajo', default=list, blank=True)
    proceso = models.ForeignKey('procesos.Proceso', verbose_name='Proceso', on_delete=models.PROTECT, null=True,
                                blank=True, related_name='ats_tipo')
    filas_iperc = models.ManyToManyField(FilaIPERC, verbose_name='Filas IPERC relacionadas', blank=True,
                                         related_name='ats_tipo')
    pasos = models.JSONField('Etapas', default=list, blank=True,
                             help_text='[{etapa, peligros, riesgos, severidad, probabilidad, medidas, r_severidad, '
                                       'r_probabilidad}]')
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'ATS tipo'
        verbose_name_plural = 'ATS tipo'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ATS(AuditableModel):
    """Análisis de Trabajo Seguro (código ATS-NNN-AAAA)."""
    codigo = models.CharField('Código', max_length=16, unique=True, editable=False)
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS_ATS, default='borrador')
    lugar_ejecucion = models.CharField('Dónde se realiza', max_length=14, choices=LUGARES_ATS, default='instalaciones')
    formato = models.CharField('Formato', max_length=10, choices=FORMATOS_ATS, default='metrindust')
    cliente = models.CharField('Cliente', max_length=200, blank=True)
    ats_tipo = models.ForeignKey(ATSTipo, verbose_name='ATS tipo', on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='ats')
    evidencia = models.FileField('ATS firmado (archivo)', upload_to='sst/ats/%Y/', null=True, blank=True)
    fecha_ejecucion = models.DateField('Fecha de ejecución', null=True, blank=True)
    observaciones_campo = models.TextField('Observaciones de campo', blank=True)
    recibido_por = models.ForeignKey('core.Usuario', verbose_name='Recibido por', on_delete=models.PROTECT,
                                     null=True, blank=True, related_name='ats_recibidos')
    fecha_recepcion = models.DateTimeField('Fecha de recepción', null=True, blank=True)
    revisor = models.ForeignKey('core.Usuario', verbose_name='Revisado por (SST)', on_delete=models.PROTECT, null=True,
                                blank=True, related_name='ats_revisados')
    firma_revision = models.JSONField('Firma de la revisión', default=dict, blank=True)
    observaciones_revision = models.TextField('Observaciones de la revisión', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    zona = models.CharField('Zona de trabajo', max_length=200)
    fecha = models.DateField('Fecha', default=timezone.localdate)
    hora_inicio = models.TimeField('Hora de inicio', null=True, blank=True)
    hora_fin = models.TimeField('Hora final', null=True, blank=True)
    tarea = models.TextField('Tarea a realizar')
    lugar = models.CharField('Lugar de servicio', max_length=200, blank=True)
    orden_trabajo = models.CharField('Orden de trabajo', max_length=40, blank=True)
    empresa = models.CharField('Empresa que realiza el servicio', max_length=150, default='METRINDUST S.A.C.')
    planificado = models.CharField('Planificado', max_length=12, choices=[('si', 'Sí'), ('no', 'No'),
                                                                        ('emergencia', 'Emergencia')], default='si')
    tipos_trabajo = models.JSONField('Tipo de trabajo', default=list, blank=True)
    tipo_otro = models.CharField('Otro tipo de trabajo', max_length=120, blank=True)
    proceso = models.ForeignKey('procesos.Proceso', verbose_name='Proceso', on_delete=models.PROTECT, null=True,
                                blank=True, related_name='ats')
    filas_iperc = models.ManyToManyField(FilaIPERC, verbose_name='Filas IPERC relacionadas', blank=True,
                                         related_name='ats')
    ejecutantes = models.JSONField('Personal ejecutante', default=list, blank=True, help_text='[{trabajador, nombre, puesto}] (hasta 9; sin trabajador = personal externo)')
    comentarios = models.TextField('Comentarios / observaciones', blank=True)
    equipos = models.JSONField('Equipos, herramientas o insumos', default=list, blank=True)
    supervisor = models.ForeignKey('core.Usuario', verbose_name='Supervisor o prevencionista de SST',
                                   on_delete=models.PROTECT, null=True, blank=True, related_name='ats_supervisados')
    firma_supervisor = models.JSONField('Firma del supervisor', default=dict, blank=True)
    responsable_cliente = models.CharField('Responsable del servicio (cliente)', max_length=150, blank=True)
    ssoma_cliente = models.CharField('Área de SSOMA (cliente)', max_length=150, blank=True)
    motivo_anulacion = models.TextField('Motivo de anulación', blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Análisis de Trabajo Seguro'
        verbose_name_plural = 'Análisis de Trabajo Seguro'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.codigo} — {self.tarea[:50]}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            anio = self.fecha.year
            nums = [int(c.split('-')[1]) for c in ATS.objects.filter(codigo__endswith=f'-{anio}')
                    .values_list('codigo', flat=True) if c.split('-')[1].isdigit()]
            self.codigo = f'ATS-{(max(nums) + 1) if nums else 1:03d}-{anio}'
        super().save(*args, **kwargs)

    @property
    def en_campo(self):
        return self.lugar_ejecucion == 'campo'

    def etapas_abiertas(self):
        """preparación: todo el ATS; campo: transcripción de lo que cambió en el lugar (y las etapas, si el
        formato es el de Metrindust)."""
        if self.estado == 'borrador':
            return ['preparacion', 'campo']
        if self.estado == 'en_campo':
            return ['campo']
        return []

    def pasos_editables(self):
        return self.estado == 'borrador' or (self.estado == 'en_campo' and self.formato == 'metrindust')


class PasoATS(AuditableModel):
    """Etapa del trabajo con sus peligros, riesgos, evaluación y medidas de control."""
    ats = models.ForeignKey(ATS, on_delete=models.PROTECT, related_name='pasos')
    orden = models.PositiveIntegerField('Orden', default=0)
    etapa = models.TextField('Etapa (descripción de la actividad)')
    peligros = models.TextField('Peligros', blank=True)
    riesgos = models.TextField('Riesgos', blank=True)
    severidad = models.PositiveSmallIntegerField('S', null=True, blank=True)
    probabilidad = models.PositiveSmallIntegerField('P', null=True, blank=True)
    medidas = models.TextField('Medidas de control', blank=True)
    r_severidad = models.PositiveSmallIntegerField('S residual', null=True, blank=True)
    r_probabilidad = models.PositiveSmallIntegerField('P residual', null=True, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        ordering = ['orden', 'id']

    @property
    def valor(self):
        return self.severidad * self.probabilidad if self.severidad and self.probabilidad else None

    @property
    def nivel(self):
        return nivel_ats(self.valor)

    @property
    def r_valor(self):
        return self.r_severidad * self.r_probabilidad if self.r_severidad and self.r_probabilidad else None

    @property
    def r_nivel(self):
        return nivel_ats(self.r_valor)


# Incidentes, accidentes, enfermedades ocupacionales y estadísticas (en su propio archivo).
from .eventos import (AfectadoEvento, ArchivoEvento, DatosMesSST, EnfermedadOcupacional, Evento,  # noqa: E402,F401
                      InformeEstadisticasSST)
# Inspecciones y monitoreos de agentes ocupacionales (en su propio archivo).
from .inspecciones import (ElementoSeguridad, Inspeccion, ItemInspeccion, Monitoreo,  # noqa: E402,F401
                           MonitoreoProgramado, PlantillaInspeccion, ProgramaMonitoreo, RecomendacionMonitoreo)
# EPP y vigilancia médica (en su propio archivo).
from .epp import (CatalogoEPP, EntregaEPP, EvaluacionMedica, InformeAnexo4, ItemEntregaEPP,  # noqa: E402,F401
                  PerfilEPP, PinTrabajador, RequisitoEPP, ResultadoEMO)
# Comité de SST y Programa anual SSOMA (en su propio archivo).
from .comite import (AcuerdoComite, ActividadSSOMA, ComiteSST, MiembroComite, ObjetivoSSOMA,  # noqa: E402,F401
                     ProgramaSSOMA, ReunionComite)
