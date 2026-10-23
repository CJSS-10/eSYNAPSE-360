"""
M3 — Riesgos y oportunidades, según el procedimiento de gestión de riesgos y
oportunidades: contexto (FODA y partes interesadas), matriz de riesgos y
oportunidades (identificación, valoración, tratamiento, seguimiento y eficacia
por valoración residual) y matriz de oportunidades de mejora.
"""
from django.db import models
from django.utils import timezone

from core.models import AuditableModel

TIPOS = [('riesgo', 'Riesgo'), ('oportunidad', 'Oportunidad')]

CATEGORIAS = [
    ('tecnico_metrologico', 'Técnico-metrológico'),
    ('operativo', 'Operativo'),
    ('imparcialidad', 'Imparcialidad'),
    ('confidencialidad', 'Confidencialidad'),
    ('cumplimiento', 'Cumplimiento'),
    ('estrategico', 'Estratégico'),
    ('comercial', 'Comercial'),
    ('financiero', 'Financiero'),
    ('proveedores', 'Proveedores'),
    ('personal', 'Personal'),
    ('tecnologias_de_la_informacion', 'Tecnologías de la información'),
    ('ambiental', 'Ambiental'),
    ('seguridad_y_salud_en_el_trabajo', 'Seguridad y salud en el trabajo'),
]

FUENTES = [
    ('analisis_del_contexto_foda', 'Análisis del contexto - FODA'),
    ('partes_interesadas', 'Partes interesadas'),
    ('actividad_del_proceso', 'Actividad del proceso'),
    ('requisitos_legales_y_otros_requisitos', 'Requisitos legales y otros requisitos'),
    ('auditoria_interna', 'Auditoría interna'),
    ('evaluacion_de_organismo_externo', 'Evaluación de organismo externo'),
    ('queja_o_reclamo_del_cliente', 'Queja o reclamo del cliente'),
    ('ensayo_de_aptitud_o_comparacion_interlaboratorios', 'Ensayo de aptitud o comparación interlaboratorios'),
    ('revision_por_la_direccion', 'Revisión por la dirección'),
    ('trabajo_no_conforme_o_accion_correctiva', 'Trabajo no conforme o acción correctiva'),
    ('analisis_de_datos_e_indicadores', 'Análisis de datos e indicadores'),
]

FUENTES_MEJORA = [
    ('analisis_del_contexto_foda', 'Análisis del contexto - FODA'),
    ('partes_interesadas', 'Partes interesadas'),
    ('actividad_del_proceso', 'Actividad del proceso'),
    ('requisitos_legales_y_otros_requisitos', 'Requisitos legales y otros requisitos'),
    ('auditoria_interna', 'Auditoría interna'),
    ('evaluacion_de_organismo_externo', 'Evaluación de organismo externo'),
    ('queja', 'Queja'),
    ('sugerencia_del_personal', 'Sugerencia del personal'),
    ('ensayo_de_aptitud_o_comparacion_interlaboratorios', 'Ensayo de aptitud o comparación interlaboratorios'),
    ('revision_por_la_direccion', 'Revisión por la dirección'),
    ('accion_correctiva_o_trabajo_no_conforme', 'Acción correctiva o trabajo no conforme'),
    ('analisis_de_datos', 'Análisis de datos'),
    ('retroalimentacion_del_cliente', 'Retroalimentación del cliente'),
    ('revision_de_documentos_del_sig', 'Revisión de documentos del SIG'),
    ('evaluacion_de_riesgos', 'Evaluación de riesgos'),
]

ESTRATEGIAS = [
    ('reducir', 'Reducir'), ('aceptar', 'Aceptar'), ('evitar', 'Evitar'), ('compartir', 'Compartir'),
    ('remover', 'Remover'), ('incrementar', 'Incrementar'),
]
ESTRATEGIAS_RIESGO = ('reducir', 'aceptar', 'evitar', 'compartir', 'remover')
ESTRATEGIAS_OPORTUNIDAD = ('incrementar',)

ESTADOS_ACCION = [('pendiente', 'Pendiente de implementar'), ('en_proceso', 'En proceso'),
                  ('ejecutado', 'Ejecutado'), ('no_aplica', 'No aplica')]

ESTADOS_RYO = [('borrador', 'En registro'), ('vigente', 'En la matriz'), ('retirado', 'Retirado')]

TIPOS_CONTEXTO = [('fortaleza', 'Fortaleza'), ('debilidad', 'Debilidad'), ('oportunidad', 'Oportunidad'),
                  ('amenaza', 'Amenaza'), ('parte_interesada', 'Parte interesada')]
PREFIJO_CONTEXTO = {'fortaleza': 'F', 'debilidad': 'D', 'oportunidad': 'O', 'amenaza': 'A', 'parte_interesada': 'PI'}

DECISIONES_MEJORA = [('se_implementa', 'Se implementa'), ('en_evaluacion', 'En evaluación'),
                     ('no_se_implementa', 'No se implementa')]
EFICACIAS_MEJORA = [('pendiente', 'Pendiente'), ('lograda', 'Lograda'), ('parcial', 'Parcial'),
                    ('no_lograda', 'No lograda')]
DECISIONES_CARTERA = [('abordar', 'Se aborda'), ('descartar', 'Se descarta')]

# Escala común de cinco niveles (anexo de criterios de valoración).
NIVELES = [('no_significativo', 'No significativo'), ('tolerado', 'Tolerado'), ('moderado', 'Moderado'),
           ('importante', 'Importante'), ('critico', 'Crítico')]


def nivel_de(valor):
    """Nivel según la tabla de nivel resultante: 1–3, 4–7, 8–14, 15–19, 20–25."""
    if not valor:
        return ''
    if valor >= 20:
        return 'critico'
    if valor >= 15:
        return 'importante'
    if valor >= 8:
        return 'moderado'
    if valor >= 4:
        return 'tolerado'
    return 'no_significativo'


class ElementoContexto(AuditableModel):
    """Elemento del análisis de contexto: fortaleza, debilidad, oportunidad, amenaza o parte interesada."""
    tipo = models.CharField('Tipo', max_length=16, choices=TIPOS_CONTEXTO)
    codigo = models.CharField('Código', max_length=8, unique=True)
    descripcion = models.TextField('Descripción')
    requisitos = models.TextField('Necesidades y expectativas (partes interesadas)', blank=True)
    is_active = models.BooleanField('Vigente', default=True)

    class Meta:
        verbose_name = 'Elemento de contexto'
        verbose_name_plural = 'Contexto'
        ordering = ['tipo', 'id']

    def __str__(self):
        return f'{self.codigo}: {self.descripcion[:60]}'

    @staticmethod
    def siguiente_codigo(tipo):
        pref = PREFIJO_CONTEXTO[tipo]
        nums = [int(c[len(pref):]) for c in ElementoContexto.objects.filter(tipo=tipo).values_list('codigo', flat=True)
                if c[len(pref):].isdigit()]
        return f'{pref}{(max(nums) + 1) if nums else 1}'


class RiesgoOportunidad(AuditableModel):
    """Registro de la matriz de riesgos y oportunidades (código R-000 / O-000)."""
    codigo = models.CharField('Código', max_length=10, unique=True, editable=False)
    tipo = models.CharField('Tipo', max_length=12, choices=TIPOS)
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS_RYO, default='borrador')

    # Identificación y análisis
    proceso = models.ForeignKey('procesos.Proceso', verbose_name='Proceso', on_delete=models.PROTECT,
                                related_name='riesgos', null=True, blank=True)
    contexto = models.ManyToManyField(ElementoContexto, verbose_name='Contexto y partes interesadas', blank=True,
                                      related_name='riesgos')
    categoria = models.CharField('Categoría', max_length=40, choices=CATEGORIAS, blank=True)
    fuente = models.CharField('Fuente / origen de la identificación', max_length=60, choices=FUENTES, blank=True)
    fecha_identificacion = models.DateField('Fecha de identificación', default=timezone.localdate)
    actividad = models.TextField('Actividad / etapa', blank=True)
    descripcion = models.TextField('Descripción del riesgo u oportunidad')
    causa = models.TextField('Causa', blank=True)
    efecto = models.TextField('Efecto / consecuencia', blank=True)
    controles_existentes = models.TextField('Controles existentes', blank=True)
    hallazgo = models.ForeignKey('esynapse_sig.Hallazgo', verbose_name='Hallazgo que lo origina',
                                 on_delete=models.PROTECT, null=True, blank=True, related_name='riesgos_derivados')

    # Valoración inicial: riesgos P×I; oportunidades V×B.
    probabilidad = models.PositiveSmallIntegerField('Probabilidad / viabilidad', null=True, blank=True)
    impacto = models.PositiveSmallIntegerField('Impacto / beneficio', null=True, blank=True)

    # Tratamiento
    estrategia = models.CharField('Estrategia', max_length=12, choices=ESTRATEGIAS, blank=True)
    justificacion_aceptacion = models.TextField('Decisión documentada de aceptar el riesgo', blank=True)
    firma_aceptacion = models.JSONField('Aceptación del Gerente General', default=dict, blank=True)
    decision_cartera = models.CharField('Decisión sobre la oportunidad en cartera', max_length=10,
                                        choices=DECISIONES_CARTERA, blank=True)
    motivo_cartera = models.TextField('Motivo de la decisión de cartera', blank=True)

    # Verificación de la eficacia (valoración residual)
    residual_probabilidad = models.PositiveSmallIntegerField('Probabilidad / viabilidad residual', null=True, blank=True)
    residual_impacto = models.PositiveSmallIntegerField('Impacto / beneficio residual', null=True, blank=True)
    fecha_verificacion = models.DateField('Fecha de verificación', null=True, blank=True)
    evidencia_verificacion = models.TextField('Evidencia / observaciones de la verificación', blank=True)
    verificado_por = models.ForeignKey('core.Usuario', verbose_name='Verificado por', on_delete=models.PROTECT,
                                       null=True, blank=True, related_name='riesgos_verificados')

    # Revaloraciones, ciclos de tratamiento anteriores, materializaciones, retiro.
    historial = models.JSONField('Historial', default=list, blank=True)
    motivo_retiro = models.TextField('Motivo del retiro', blank=True)
    is_active = models.BooleanField('Activo', default=True)

    CAMPOS_IDENTIFICACION = ('tipo', 'proceso', 'contexto', 'categoria', 'fuente', 'fecha_identificacion', 'actividad',
                             'descripcion', 'causa', 'efecto', 'controles_existentes', 'probabilidad', 'impacto',
                             'hallazgo')
    CAMPOS_TRATAMIENTO = ('estrategia', 'justificacion_aceptacion')
    NOMBRES_ETAPA = {'identificacion': 'identificación y valoración inicial', 'tratamiento': 'tratamiento'}

    class Meta:
        verbose_name = 'Riesgo u oportunidad'
        verbose_name_plural = 'Riesgos y oportunidades'
        ordering = ['tipo', 'codigo']

    def __str__(self):
        return f'{self.codigo} — {self.descripcion[:60]}'

    @staticmethod
    def siguiente_codigo(tipo):
        pref = 'R-' if tipo == 'riesgo' else 'O-'
        nums = [int(c[2:]) for c in RiesgoOportunidad.objects.filter(codigo__startswith=pref)
                .values_list('codigo', flat=True) if c[2:].isdigit()]
        return f'{pref}{(max(nums) + 1) if nums else 1:03d}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.siguiente_codigo(self.tipo)
        super().save(*args, **kwargs)

    # --- Valoración ---
    @property
    def valor(self):
        return self.probabilidad * self.impacto if self.probabilidad and self.impacto else None

    @property
    def nivel(self):
        return nivel_de(self.valor)

    @property
    def requiere_accion(self):
        """'si', 'no' o 'en_cartera' (oportunidades de nivel moderado)."""
        v = self.valor
        if v is None:
            return ''
        if self.tipo == 'riesgo':
            return 'si' if v >= 8 else 'no'
        return 'si' if v >= 15 else 'en_cartera' if v >= 8 else 'no'

    @property
    def debe_tratarse(self):
        """Tratamiento obligatorio, u oportunidad en cartera que la Alta Dirección decidió abordar."""
        r = self.requiere_accion
        return r == 'si' or (r == 'en_cartera' and self.decision_cartera == 'abordar')

    @property
    def valor_residual(self):
        return (self.residual_probabilidad * self.residual_impacto
                if self.residual_probabilidad and self.residual_impacto else None)

    @property
    def nivel_residual(self):
        return nivel_de(self.valor_residual)

    def acciones_activas(self):
        return [a for a in self.acciones.all() if a.is_active]

    @property
    def eficacia(self):
        """Igual que el formato: no aplica / pendiente / eficaz / sin cambio / no eficaz."""
        r = self.requiere_accion
        if not r:
            return ''
        acciones = self.acciones_activas()
        if r in ('no', 'en_cartera') and not acciones:
            return 'no_aplica'
        if self.estrategia == 'aceptar' and not acciones:
            return 'no_aplica'
        vr, v = self.valor_residual, self.valor
        if vr is None:
            return 'pendiente'
        if vr == v:
            return 'sin_cambio'
        mejora = vr < v if self.tipo == 'riesgo' else vr > v
        return 'eficaz' if mejora else 'no_eficaz'

    @property
    def acciones_vencidas(self):
        hoy = timezone.localdate()
        return [a for a in self.acciones_activas() if a.estado in ('pendiente', 'en_proceso')
                and a.fecha_maxima and a.fecha_maxima < hoy]

    @property
    def situacion(self):
        """Resumen para la pantalla."""
        if self.estado != 'vigente':
            return self.estado
        e = self.eficacia
        if e == 'no_aplica':
            if self.requiere_accion == 'en_cartera' and not self.decision_cartera:
                return 'en_cartera'
            return 'aceptado' if self.estrategia == 'aceptar' else ('descartado' if self.decision_cartera == 'descartar'
                                                                   else 'asumido')
        if e == 'pendiente':
            acciones = self.acciones_activas()
            if not acciones:
                return 'sin_tratamiento'
            if acciones and all(a.estado in ('ejecutado', 'no_aplica') for a in acciones):
                return 'por_verificar'
            return 'en_tratamiento'
        return e

    def etapas_abiertas(self):
        if self.estado == 'borrador':
            return ['identificacion', 'tratamiento']
        if self.estado == 'vigente' and self.valor_residual is None:
            return ['tratamiento']
        return []

    @classmethod
    def etapa_de_campo(cls, campo):
        if campo in cls.CAMPOS_IDENTIFICACION:
            return 'identificacion'
        if campo in cls.CAMPOS_TRATAMIENTO:
            return 'tratamiento'
        return None


class AccionRiesgo(AuditableModel):
    """Acción de tratamiento de un riesgo u oportunidad."""
    riesgo = models.ForeignKey(RiesgoOportunidad, on_delete=models.PROTECT, related_name='acciones')
    orden = models.PositiveIntegerField('Orden', default=0)
    actividad = models.TextField('Acción o actividad')
    implementacion_documental = models.TextField('Implementación documental propuesta', blank=True)
    responsable = models.ForeignKey('core.Usuario', verbose_name='Responsable', on_delete=models.PROTECT,
                                    null=True, blank=True, related_name='acciones_riesgo')
    responsable_texto = models.CharField('Responsable (texto)', max_length=150, blank=True)
    fecha_inicio = models.DateField('Fecha de inicio', null=True, blank=True)
    fecha_maxima = models.DateField('Fecha máxima de implementación', null=True, blank=True)
    recursos = models.TextField('Recursos', blank=True)
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS_ACCION, default='pendiente')
    fecha_ejecucion = models.DateField('Fecha de ejecución', null=True, blank=True)
    evidencia = models.FileField('Evidencia', upload_to='riesgos/acciones/%Y/', null=True, blank=True)
    observaciones = models.TextField('Evidencia / observaciones', blank=True)
    hallazgo_incumplimiento = models.ForeignKey('esynapse_sig.Hallazgo', verbose_name='Hallazgo por incumplimiento',
                                                on_delete=models.PROTECT, null=True, blank=True,
                                                related_name='acciones_riesgo_incumplidas')
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        ordering = ['orden', 'id']

    @property
    def responsable_nombre(self):
        if self.responsable_id:
            return self.responsable.get_full_name() or self.responsable.username
        return self.responsable_texto

    @property
    def vencida(self):
        return bool(self.estado in ('pendiente', 'en_proceso') and self.fecha_maxima
                    and self.fecha_maxima < timezone.localdate())


class OportunidadMejora(AuditableModel):
    """Registro de la matriz de oportunidades de mejora (código OM-000)."""
    codigo = models.CharField('Código', max_length=10, unique=True, editable=False)
    proceso = models.ForeignKey('procesos.Proceso', verbose_name='Proceso', on_delete=models.PROTECT,
                                related_name='oportunidades_mejora', null=True, blank=True)
    fuente = models.CharField('Fuente / origen de la identificación', max_length=60, choices=FUENTES_MEJORA)
    detectado_por = models.CharField('Detectado por', max_length=150, blank=True)
    fecha_identificacion = models.DateField('Fecha de identificación', default=timezone.localdate)
    descripcion = models.TextField('Descripción de la oportunidad de mejora')
    situacion = models.TextField('Situación que la motiva', blank=True)
    hallazgo = models.ForeignKey('esynapse_sig.Hallazgo', verbose_name='Hallazgo que la origina',
                                 on_delete=models.PROTECT, null=True, blank=True, related_name='mejoras_derivadas')

    # Selección
    decision = models.CharField('Decisión', max_length=16, choices=DECISIONES_MEJORA, default='en_evaluacion')
    justificacion = models.TextField('Justificación de la decisión', blank=True)
    fecha_decision = models.DateField('Fecha de la decisión', null=True, blank=True)

    # Implementación y seguimiento
    accion = models.TextField('Acción o actividad', blank=True)
    responsable = models.ForeignKey('core.Usuario', verbose_name='Responsable', on_delete=models.PROTECT,
                                    null=True, blank=True, related_name='mejoras_a_cargo')
    responsable_texto = models.CharField('Responsable (texto)', max_length=150, blank=True)
    fecha_maxima = models.DateField('Fecha máxima de implementación', null=True, blank=True)
    estado_accion = models.CharField('Estado', max_length=10, choices=ESTADOS_ACCION, default='pendiente')
    fecha_ejecucion = models.DateField('Fecha de ejecución', null=True, blank=True)
    fecha_verificacion = models.DateField('Fecha de verificación', null=True, blank=True)
    evidencia = models.TextField('Evidencia / observaciones', blank=True)
    evidencia_archivo = models.FileField('Archivo de evidencia', upload_to='riesgos/mejoras/%Y/', null=True, blank=True)
    eficacia = models.CharField('Eficacia de la mejora', max_length=10, choices=EFICACIAS_MEJORA, default='pendiente')
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Oportunidad de mejora'
        verbose_name_plural = 'Oportunidades de mejora'
        ordering = ['codigo']

    def __str__(self):
        return f'{self.codigo} — {self.descripcion[:60]}'

    @staticmethod
    def siguiente_codigo():
        nums = [int(c[3:]) for c in OportunidadMejora.objects.values_list('codigo', flat=True) if c[3:].isdigit()]
        return f'OM-{(max(nums) + 1) if nums else 1:03d}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.siguiente_codigo()
        super().save(*args, **kwargs)

    @property
    def responsable_nombre(self):
        if self.responsable_id:
            return self.responsable.get_full_name() or self.responsable.username
        return self.responsable_texto

    @property
    def cerrada(self):
        return self.decision == 'no_se_implementa' or (self.decision == 'se_implementa'
                                                       and self.eficacia != 'pendiente')

    @property
    def evaluacion_vencida(self):
        """En evaluación más de un ciclo anual."""
        return (self.decision == 'en_evaluacion'
                and (timezone.localdate() - self.fecha_identificacion).days > 365)

    @property
    def accion_vencida(self):
        return bool(self.decision == 'se_implementa' and self.estado_accion in ('pendiente', 'en_proceso')
                    and self.fecha_maxima and self.fecha_maxima < timezone.localdate())

    def etapas_abiertas(self):
        if self.decision == 'en_evaluacion':
            return ['identificacion']
        return []

    CAMPOS_IDENTIFICACION = ('proceso', 'fuente', 'detectado_por', 'fecha_identificacion', 'descripcion', 'situacion',
                             'hallazgo')

    @classmethod
    def etapa_de_campo(cls, campo):
        return 'identificacion' if campo in cls.CAMPOS_IDENTIFICACION else None


class RevisionMatriz(AuditableModel):
    """Actualización (Área SIG) o supervisión del correcto llenado (Gerente Técnico) de una matriz."""
    MATRICES = [('ryo', 'Matriz de riesgos y oportunidades'), ('om', 'Matriz de oportunidades de mejora')]
    TIPOS_REVISION = [('actualizacion', 'Actualización'), ('supervision', 'Supervisión')]
    matriz = models.CharField('Matriz', max_length=4, choices=MATRICES)
    tipo = models.CharField('Tipo', max_length=14, choices=TIPOS_REVISION)
    fecha = models.DateField('Fecha', default=timezone.localdate)
    usuario = models.ForeignKey('core.Usuario', verbose_name='Responsable', on_delete=models.PROTECT,
                                null=True, blank=True, related_name='revisiones_matriz_riesgos')
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
