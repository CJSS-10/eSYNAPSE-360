"""
Equipos de protección personal (procedimiento de gestión de EPP) y vigilancia médica ocupacional.

EPP:
    - Catálogo con tipo de protección, clasificación (básico / específico) y vida útil referencial.
    - Matriz de EPP por puesto de trabajo: cada perfil (puesto, laboratorio o servicio en campo) con sus
      EPP obligatorios o según la tarea.
    - Entrega (dotación inicial, reposición…): el responsable de la entrega firma con su contraseña y el
      trabajador con su PIN personal (o el cargo firmado en papel adjunto). Firmada no se modifica.
    - Devolución por cese, rotación o cambio de puesto.
    El stock lo lleva Logística (se integra con Inventarios).

Vigilancia médica: evaluaciones (exámenes médicos ocupacionales) con la aptitud de cada trabajador,
sus restricciones o recomendaciones sin diagnóstico y la fecha del próximo examen.
"""
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from core.models import AuditableModel

from .inspecciones import _siguiente_codigo, estado_fecha

TIPOS_PROTECCION = [('cabeza', 'Protección de cabeza'), ('visual', 'Protección visual'),
                    ('auditiva', 'Protección auditiva'), ('manos', 'Protección de manos'),
                    ('pies', 'Protección de pies'), ('respiratoria', 'Protección respiratoria'),
                    ('caidas', 'Protección contra caídas'), ('ropa', 'Ropa de trabajo'), ('uniforme', 'Uniforme'),
                    ('otros', 'Otros')]
CLASIFICACION_EPP = [('basico', 'Básico'), ('especifico', 'Específico')]
NIVELES_REQUISITO = [('obligatorio', 'Obligatorio'), ('segun_tarea', 'Según la tarea')]
TIPOS_ENTREGA = [('dotacion', 'Dotación inicial'), ('reposicion', 'Reposición'), ('cambio_puesto', 'Cambio de puesto'),
                 ('campo', 'Servicio en campo'), ('otro', 'Otro')]
MOTIVOS_REPOSICION = [('desgaste', 'Desgaste normal'), ('dano', 'Daño'), ('vencimiento', 'Vencimiento'),
                      ('perdida', 'Pérdida'), ('contaminacion', 'Contaminación'), ('cambio_puesto', 'Cambio de puesto'),
                      ('actualizacion', 'Actualización técnica')]
ESTADOS_ENTREGA = [('en_registro', 'En registro'), ('firmada', 'Firmada'), ('anulada', 'Anulada')]
ESTADOS_DEVOLUCION = [('reutilizable', 'Reutilizable'), ('descartado', 'Descartado (disposición final)')]
INTENTOS_PIN = 5

TIPOS_EMO = [('preocupacional', 'Preocupacional'), ('periodico', 'Periódico'), ('retiro', 'De retiro'),
             ('reincorporacion', 'Por reincorporación / cambio de puesto'), ('otro', 'Otro')]
APTITUDES = [('apto', 'Apto'), ('apto_restricciones', 'Apto con restricciones'), ('no_apto', 'No apto'),
             ('observado', 'Observado (pendiente)')]
ESTADOS_EMO = [('en_registro', 'En registro'), ('registrado', 'Registrado'), ('anulado', 'Anulado')]
# Procedimiento de seguimiento y medición: personal operativo anual, administrativo cada dos años.
MESES_EMO = {'operativo': 12, 'administrativo': 24}
AREAS_OPERATIVAS = ('Gerencia Técnica', 'Logística', 'Mantenimiento')


def sumar_meses(fecha, meses):
    import calendar
    m = fecha.month - 1 + meses
    anio, mes = fecha.year + m // 12, m % 12 + 1
    return fecha.replace(year=anio, month=mes, day=min(fecha.day, calendar.monthrange(anio, mes)[1]))


def es_operativo(trabajador):
    """Personal operativo: laboratorios, logística y mantenimiento (y sus gerencias)."""
    a = trabajador.area_efectiva
    while a is not None:
        if a.tipo == 'laboratorio' or a.nombre in AREAS_OPERATIVAS:
            return True
        a = a.padre
    return False


# ================================================================================== EPP
class CatalogoEPP(AuditableModel):
    nombre = models.CharField('EPP', max_length=150, unique=True)
    tipo = models.CharField('Tipo de protección', max_length=14, choices=TIPOS_PROTECCION)
    clasificacion = models.CharField('Clasificación', max_length=10, choices=CLASIFICACION_EPP, default='especifico')
    marca_modelo = models.CharField('Marca / modelo', max_length=150, blank=True)
    certificacion = models.CharField('Certificación (ANSI, EN, NIOSH…)', max_length=100, blank=True)
    vida_util_meses = models.PositiveIntegerField('Vida útil referencial (meses)', null=True, blank=True)
    descartable = models.BooleanField('Descartable (no se devuelve)', default=False)
    orden = models.PositiveIntegerField('Orden', default=0)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'EPP del catálogo'
        verbose_name_plural = 'Catálogo de EPP'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class PerfilEPP(AuditableModel):
    """Fila de la matriz de EPP por puesto de trabajo."""
    nombre = models.CharField('Puesto / perfil (como figura en la matriz)', max_length=250)
    grupo = models.CharField('Área de la matriz', max_length=120, blank=True)
    puestos = models.ManyToManyField('organizacion.Puesto', verbose_name='Puestos del organigrama', blank=True,
                                     related_name='perfiles_epp')
    area = models.ForeignKey('organizacion.Area', verbose_name='Área o laboratorio (si aplica solo ahí)',
                             on_delete=models.PROTECT, null=True, blank=True, related_name='perfiles_epp')
    en_campo = models.BooleanField('Servicio en campo (se aplica al entregar para campo)', default=False)
    orden = models.PositiveIntegerField('Orden', default=0)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Perfil de la matriz de EPP'
        verbose_name_plural = 'Matriz de EPP por puesto'
        ordering = ['orden', 'id']

    def __str__(self):
        return self.nombre

    def aplica_a(self, trabajador):
        if self.en_campo:
            return False
        if self.puestos.exists() and not self.puestos.filter(pk=trabajador.puesto_id).exists():
            return False
        if self.area_id and (not trabajador.area_efectiva or trabajador.area_efectiva.pk != self.area_id):
            return False
        return self.puestos.exists() or bool(self.area_id)


class RequisitoEPP(models.Model):
    perfil = models.ForeignKey(PerfilEPP, on_delete=models.CASCADE, related_name='requisitos')
    epp = models.ForeignKey(CatalogoEPP, on_delete=models.PROTECT, related_name='requisitos')
    nivel = models.CharField('Nivel', max_length=12, choices=NIVELES_REQUISITO, default='obligatorio')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['perfil', 'epp'], name='requisito_epp_unico')]


class PinTrabajador(models.Model):
    """PIN con el que el trabajador firma la recepción de sus EPP (cifrado, como una contraseña)."""
    trabajador = models.OneToOneField('organizacion.Trabajador', on_delete=models.CASCADE, related_name='pin_epp')
    pin = models.CharField('PIN cifrado', max_length=128)
    creado = models.DateTimeField('Creado', default=timezone.now)
    intentos_fallidos = models.PositiveSmallIntegerField('Intentos fallidos', default=0)
    bloqueado = models.BooleanField('Bloqueado', default=False)
    historial = models.JSONField('Historial', default=list, blank=True)

    def fijar(self, pin):
        self.pin = make_password(pin)
        self.intentos_fallidos, self.bloqueado, self.creado = 0, False, timezone.now()

    def verificar(self, pin):
        """True si el PIN es correcto; cuenta los intentos fallidos y bloquea al quinto. Lee y escribe el registro
        bloqueado en la base, para que intentos simultáneos no esquiven el contador."""
        from django.db import transaction
        with transaction.atomic():
            reg = PinTrabajador.objects.select_for_update().get(pk=self.pk)
            if reg.bloqueado:
                self.bloqueado, self.intentos_fallidos = True, reg.intentos_fallidos
                return False
            if check_password(pin, reg.pin):
                reg.intentos_fallidos = 0
                reg.save(update_fields=['intentos_fallidos'])
                self.intentos_fallidos, self.bloqueado = 0, False
                return True
            reg.intentos_fallidos += 1
            reg.bloqueado = reg.intentos_fallidos >= INTENTOS_PIN
            reg.save(update_fields=['intentos_fallidos', 'bloqueado'])
            self.intentos_fallidos, self.bloqueado = reg.intentos_fallidos, reg.bloqueado
        return False


class EntregaEPP(AuditableModel):
    codigo = models.CharField('N° de registro', max_length=16, unique=True, editable=False)
    trabajador = models.ForeignKey('organizacion.Trabajador', verbose_name='Trabajador', on_delete=models.PROTECT,
                                   related_name='entregas_epp')
    fecha = models.DateField('Fecha de entrega', default=timezone.localdate)
    tipo = models.CharField('Tipo de entrega', max_length=14, choices=TIPOS_ENTREGA, default='dotacion')
    motivo = models.CharField('Motivo de la reposición', max_length=14, choices=MOTIVOS_REPOSICION, blank=True)
    # Datos del trabajador al momento de la entrega (se conservan aunque luego cambie).
    puesto = models.CharField('Puesto de trabajo', max_length=150, blank=True)
    area = models.CharField('Área', max_length=150, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS_ENTREGA, default='en_registro')
    firma_trabajador = models.JSONField('Firma del trabajador', default=dict, blank=True)
    firma_responsable = models.JSONField('Firma del responsable de la entrega', default=dict, blank=True)
    cargo_papel = models.FileField('Cargo firmado en papel', upload_to='sst/epp/%Y/', null=True, blank=True)
    motivo_anulacion = models.TextField('Motivo de anulación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Entrega de EPP'
        verbose_name_plural = 'Entregas de EPP'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = _siguiente_codigo(EntregaEPP, 'EPP', self.fecha.year)
        super().save(*args, **kwargs)


class ItemEntregaEPP(AuditableModel):
    entrega = models.ForeignKey(EntregaEPP, on_delete=models.PROTECT, related_name='items')
    epp = models.ForeignKey(CatalogoEPP, verbose_name='EPP', on_delete=models.PROTECT, related_name='entregados')
    cantidad = models.PositiveIntegerField('Cantidad', default=1)
    talla = models.CharField('Talla', max_length=20, blank=True)
    observaciones = models.CharField('Observaciones', max_length=250, blank=True)
    renovar_el = models.DateField('Renovar el (según vida útil)', null=True, blank=True)
    devuelto = models.BooleanField('Devuelto', default=False)
    fecha_devolucion = models.DateField('Fecha de devolución', null=True, blank=True)
    estado_devolucion = models.CharField('Estado al devolver', max_length=14, choices=ESTADOS_DEVOLUCION, blank=True)
    reemplazado_por = models.ForeignKey('self', verbose_name='Reemplazado por', on_delete=models.PROTECT, null=True,
                                        blank=True, related_name='reemplaza')
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'EPP entregado'
        verbose_name_plural = 'EPP entregados'
        ordering = ['epp__orden', 'id']

    @property
    def vigente(self):
        """En poder del trabajador: entrega firmada, no devuelto ni reemplazado."""
        return (self.is_active and self.entrega.estado == 'firmada' and not self.devuelto
                and self.reemplazado_por_id is None)

    @property
    def estado_renovacion(self):
        return estado_fecha(self.renovar_el) if self.vigente else None


# ====================================================================== vigilancia médica
class EvaluacionMedica(AuditableModel):
    """Evaluación médica ocupacional (campaña o examen individual) con la aptitud de cada trabajador."""
    codigo = models.CharField('N° de registro', max_length=16, unique=True, editable=False)
    tipo = models.CharField('Tipo de examen', max_length=16, choices=TIPOS_EMO, default='periodico')
    fecha = models.DateField('Fecha de la evaluación')
    centro_medico = models.CharField('Centro médico / IPRESS', max_length=200, blank=True)
    medico = models.CharField('Médico ocupacional responsable', max_length=150, blank=True)
    cmp = models.CharField('CMP', max_length=20, blank=True)
    # [{descripcion, responsable, fecha, estado}]
    medidas = models.JSONField('Medidas correctivas', default=list, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS_EMO, default='en_registro')
    firma_registro = models.JSONField('Firma del responsable del registro', default=dict, blank=True)
    motivo_anulacion = models.TextField('Motivo de anulación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Evaluación médica ocupacional'
        verbose_name_plural = 'Evaluaciones médicas ocupacionales'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = _siguiente_codigo(EvaluacionMedica, 'EMO', self.fecha.year)
        super().save(*args, **kwargs)


class ResultadoEMO(AuditableModel):
    evaluacion = models.ForeignKey(EvaluacionMedica, on_delete=models.PROTECT, related_name='resultados')
    trabajador = models.ForeignKey('organizacion.Trabajador', verbose_name='Trabajador', on_delete=models.PROTECT,
                                   related_name='resultados_emo')
    puesto = models.CharField('Puesto de trabajo', max_length=150, blank=True)
    area = models.CharField('Área', max_length=150, blank=True)
    aptitud = models.CharField('Resultado de aptitud', max_length=20, choices=APTITUDES, blank=True)
    restricciones = models.TextField('Restricciones / recomendaciones (sin diagnóstico)', blank=True)
    fecha_proximo = models.DateField('Fecha del próximo examen', null=True, blank=True)
    certificado = models.FileField('Certificado de aptitud', upload_to='sst/emo/%Y/', null=True, blank=True)
    # Cargo de entrega de resultados: el médico ocupacional lee los resultados al trabajador, que firma.
    entrega_resultados = models.JSONField('Cargo de entrega de resultados', default=dict, blank=True)
    cargo_resultados = models.FileField('Cargo de entrega firmado en papel', upload_to='sst/emo/%Y/', null=True,
                                        blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Resultado de examen médico'
        verbose_name_plural = 'Resultados de exámenes médicos'
        ordering = ['trabajador__apellidos', 'trabajador__nombres']
        constraints = [models.UniqueConstraint(fields=['evaluacion', 'trabajador'], name='resultado_emo_unico')]

    def proximo_sugerido(self):
        meses = MESES_EMO['operativo' if es_operativo(self.trabajador) else 'administrativo']
        return sumar_meses(self.evaluacion.fecha, meses)


class InformeAnexo4(AuditableModel):
    """Informe técnico de vigilancia de la salud de los trabajadores (Anexo 4), anual, hasta marzo del año
    siguiente; lo elabora el médico ocupacional a pedido de Recursos Humanos."""
    anio = models.PositiveIntegerField('Año que informa', unique=True)
    fecha_presentacion = models.DateField('Fecha de presentación')
    archivo = models.FileField('Informe', upload_to='sst/emo/anexo4/', null=True, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        verbose_name = 'Informe anual de vigilancia (Anexo 4)'
        verbose_name_plural = 'Informes anuales de vigilancia (Anexo 4)'
        ordering = ['-anio']


def renovacion(item):
    """Fecha de renovación según la vida útil del EPP."""
    v = item.epp.vida_util_meses
    return sumar_meses(item.entrega.fecha, v) if v else None

