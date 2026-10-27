"""
Capacitación e inducción del personal, según el procedimiento de gestión del personal.

- Programa anual de capacitación: lo realiza y aprueba el Comité de SST (pie del formato). Cada capacitación tiene
  fecha programada, reprogramaciones con motivo (RP) y fecha realizada (R). Si el programa cambia después de su
  aprobación, queda pendiente de una nueva aprobación.
- Sesión (lista de asistencia): toda inducción, capacitación, entrenamiento o simulacro se registra con sus
  asistentes, que firman con su usuario o con su PIN (o se adjunta la lista firmada en papel). Con evaluación, la nota
  aprobatoria es 14: certificado de aprobación; si no, de participación. La eficacia se evalúa dentro de los 6 meses.
- Inducción: tres partes (organizacional, del sistema integrado de gestión, específica del cargo); cada una se
  aprueba con 14 y, si se desaprueba, se repite solo esa parte. El trabajador inicia actividades con las tres
  aprobadas.
"""
from decimal import Decimal

from django.db import models
from django.utils import timezone

from core.models import AuditableModel

NOTA_APROBATORIA = Decimal('14')
MESES_EFICACIA = 6

TIPOS_CAPACITACION = [('metrologia', 'Metrología'), ('sst', 'SST'), ('sig', 'SIG'), ('calidad', 'Calidad'),
                      ('ambiental', 'Ambiental'), ('rrhh', 'RR. HH.'), ('otros', 'Otros')]
ALCANCES = [('todos', 'Todo el personal'), ('areas', 'Áreas'), ('puestos', 'Puestos'), ('otros', 'Otro grupo')]
TIPOS_ACTIVIDAD = [('induccion', 'Inducción'), ('difusion', 'Difusión'), ('reunion_inicio', 'Reunión inicio de jornada'),
                   ('simulacro', 'Simulacro'), ('curso', 'Curso'), ('capacitacion', 'Capacitación'),
                   ('reunion', 'Reunión'), ('entrenamiento', 'Entrenamiento'), ('sensibilizacion', 'Sensibilización'),
                   ('otros', 'Otros')]
TEMAS_ASISTENCIA = [('seguridad', 'Seguridad'), ('ambiental', 'Ambiental'), ('calidad', 'Calidad'),
                    ('metrologia', 'Metrología'), ('otros', 'Otros')]
ESTADOS_SESION = [('en_registro', 'En registro'), ('cerrada', 'Cerrada'), ('anulada', 'Anulada')]
RESULTADOS_EFICACIA = [('eficaz', 'Eficaz'), ('no_eficaz', 'No eficaz')]
PARTES_INDUCCION = [('organizacional', 'Inducción organizacional'),
                    ('sig', 'Inducción al Sistema Integrado de Gestión'),
                    ('especifica', 'Inducción específica del cargo')]
TIPOS_INDUCCION = [('induccion', 'Inducción'), ('reinduccion', 'Re-inducción')]
ESTADOS_PARTE = [('en_registro', 'En registro'), ('aprobada', 'Aprobada'), ('desaprobada', 'Desaprobada')]


def sumar_meses(f, meses):
    m = f.month - 1 + meses
    anio, mes = f.year + m // 12, m % 12 + 1
    import calendar
    return f.replace(year=anio, month=mes, day=min(f.day, calendar.monthrange(anio, mes)[1]))


def duracion_entre(desde, hasta):
    """Horas entre dos horas del mismo día (redondeo a centésimas); None si falta alguna o no es positiva.
    Acepta objetos time o textos 'HH:MM'."""
    def minutos(h):
        if isinstance(h, str):
            p = h.split(':')
            return int(p[0]) * 60 + int(p[1])
        return h.hour * 60 + h.minute
    if not desde or not hasta:
        return None
    total = minutos(hasta) - minutos(desde)
    return (Decimal(total) / Decimal(60)).quantize(Decimal('0.01')) if total > 0 else None


def siguiente_codigo(modelo, prefijo, anio):
    nums = [int(c.split('-')[1]) for c in modelo.objects.filter(codigo__startswith=f'{prefijo}-',
                                                                codigo__endswith=f'-{anio}')
            .values_list('codigo', flat=True) if c.split('-')[1].isdigit()]
    return f'{prefijo}-{(max(nums) + 1) if nums else 1:03d}-{anio}'


# ---------------------------------------------------------------------------- programa anual
class ProgramaCapacitacion(AuditableModel):
    anio = models.PositiveIntegerField('Año', unique=True)
    historico = models.BooleanField('Histórico (solo consulta)', default=False)
    elaborado = models.JSONField('Elaborado por', default=dict, blank=True)
    # Última aprobación del Comité de SST: {fecha, firmas[], registro, reunion, observaciones, origen?}
    aprobacion = models.JSONField('Aprobación del Comité', default=dict, blank=True)
    aprobado_en = models.DateTimeField('Registrada la aprobación', null=True, blank=True)
    archivo_aprobacion = models.FileField('Acta de aprobación en papel', upload_to='capacitacion/programas/',
                                          null=True, blank=True)
    aprobaciones_anteriores = models.JSONField('Aprobaciones anteriores', default=list, blank=True)
    # Último cambio de lo planificado (agregar, corregir o retirar capacitaciones). La reprogramación de fechas y la
    # ejecución no lo tocan: se siguen dentro del programa aprobado (RP / R).
    modificado_en = models.DateTimeField('Último cambio de lo planificado', null=True, blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Programa anual de capacitación'
        ordering = ['-anio']

    def __str__(self):
        return f'Programa de capacitación {self.anio}'

    @property
    def estado_aprobacion(self):
        """'aprobado', 'pendiente' (cambió después de aprobarse) o 'sin_aprobar'."""
        if self.historico:
            return 'historico'
        if not self.aprobado_en:
            return 'sin_aprobar'
        return 'pendiente' if self.modificado_en and self.modificado_en > self.aprobado_en else 'aprobado'


class ItemPrograma(AuditableModel):
    programa = models.ForeignKey(ProgramaCapacitacion, on_delete=models.PROTECT, related_name='items')
    orden = models.PositiveIntegerField('Orden', default=0)
    tema = models.CharField('Capacitación', max_length=250)
    tipo = models.CharField('Tipo', max_length=12, choices=TIPOS_CAPACITACION)
    responsable = models.CharField('Responsable de la capacitación', max_length=150, blank=True)
    responsable_trabajador = models.ForeignKey('organizacion.Trabajador', verbose_name='Responsable (trabajador)',
                                               on_delete=models.PROTECT, null=True, blank=True,
                                               related_name='capacitaciones_a_cargo')
    externo = models.BooleanField('Capacitación externa', default=False)
    alcance = models.CharField('Personal a capacitar', max_length=8, choices=ALCANCES, default='todos')
    areas = models.ManyToManyField('organizacion.Area', blank=True, related_name='capacitaciones_programadas')
    puestos = models.ManyToManyField('organizacion.Puesto', blank=True, related_name='capacitaciones_programadas')
    dirigido_texto = models.CharField('Personal a capacitar (texto)', max_length=150, blank=True)
    fecha_programada = models.DateField('Fecha programada')
    horas = models.DecimalField('Horas', max_digits=5, decimal_places=2, default=0)
    fecha_realizada = models.DateField('Fecha realizada', null=True, blank=True)
    # [{fecha, usuario, de, a, motivo}]
    reprogramaciones = models.JSONField('Reprogramaciones', default=list, blank=True)
    cancelado = models.BooleanField('Cancelada', default=False)
    motivo_cancelacion = models.TextField('Motivo de la cancelación', blank=True)
    vb = models.CharField('V°B°', max_length=20, blank=True)
    origen = models.CharField('Origen', max_length=40, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Capacitación programada'
        ordering = ['fecha_programada', 'orden', 'id']

    def __str__(self):
        return self.tema

    @property
    def fecha_vigente(self):
        """Fecha programada vigente: la última reprogramación con fecha, o la original."""
        for r in reversed(self.reprogramaciones or []):
            if r.get('a'):
                return timezone.datetime.fromisoformat(r['a']).date()
        return self.fecha_programada

    @property
    def estado(self):
        if self.cancelado:
            return 'cancelado'
        if self.fecha_realizada:
            return 'realizado'
        if self.reprogramaciones:
            return 'reprogramado'
        if self.fecha_vigente < timezone.localdate():
            return 'atrasado'
        return 'programado'

    def aplica_a(self, trabajador):
        """¿La capacitación está dirigida a este trabajador?"""
        if self.alcance == 'todos':
            return True
        if self.alcance == 'puestos':
            return self.puestos.filter(pk=trabajador.puesto_id).exists()
        if self.alcance == 'areas':
            a = trabajador.area_efectiva
            if not a:
                return False
            ids = set()
            for area in self.areas.all():
                ids.add(area.pk)
                ids.update(x.pk for x in area.descendientes())
            return a.pk in ids
        return False


# ------------------------------------------------------------------- sesiones (lista de asistencia)
class Sesion(AuditableModel):
    codigo = models.CharField('Código', max_length=20, unique=True, editable=False)
    item = models.ForeignKey(ItemPrograma, verbose_name='Capacitación del programa', on_delete=models.PROTECT,
                             null=True, blank=True, related_name='sesiones')
    tipo_actividad = models.CharField('Tipo', max_length=16, choices=TIPOS_ACTIVIDAD, default='capacitacion')
    temas = models.JSONField('Temas', default=list, blank=True)  # claves de TEMAS_ASISTENCIA
    otros_temas = models.CharField('Otros temas', max_length=120, blank=True)
    tema_tratado = models.TextField('Tema tratado')
    capacitador = models.CharField('Capacitador', max_length=150)
    capacitador_trabajador = models.ForeignKey('organizacion.Trabajador', verbose_name='Capacitador (trabajador)',
                                               on_delete=models.PROTECT, null=True, blank=True,
                                               related_name='sesiones_dictadas')
    externo = models.BooleanField('Capacitación externa', default=False)
    entidad = models.CharField('Entidad capacitadora', max_length=150, blank=True)
    fecha = models.DateField('Fecha')
    hora_desde = models.TimeField('Desde', null=True, blank=True)
    hora_hasta = models.TimeField('Hasta', null=True, blank=True)
    duracion_horas = models.DecimalField('Duración (horas)', max_digits=5, decimal_places=2, default=0)
    material_entregado = models.TextField('Material entregado', blank=True)
    con_evaluacion = models.BooleanField('Con evaluación', default=False)
    observaciones = models.TextField('Observaciones / anotaciones', blank=True)
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS_SESION, default='en_registro')
    firma_registro = models.JSONField('Responsable del registro', default=dict, blank=True)
    lista_papel = models.FileField('Lista de asistencia firmada (papel)', upload_to='capacitacion/listas/%Y/',
                                   null=True, blank=True)
    # Evaluación de la eficacia: {resultado, comentario, fecha, firma}
    eficacia = models.JSONField('Evaluación de la eficacia', default=dict, blank=True)
    motivo_anulacion = models.TextField('Motivo de la anulación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    # Etapa cerrada = solo lectura: los datos de la sesión se corrigen mientras está en registro.
    CAMPOS_REGISTRO = ('item', 'tipo_actividad', 'temas', 'otros_temas', 'tema_tratado', 'capacitador',
                       'capacitador_trabajador', 'externo', 'entidad', 'fecha', 'hora_desde', 'hora_hasta',
                       'duracion_horas', 'material_entregado', 'con_evaluacion', 'observaciones')

    class Meta:
        verbose_name = 'Sesión de capacitación (lista de asistencia)'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = siguiente_codigo(Sesion, 'CAP', (self.fecha or timezone.localdate()).year)
        calculada = duracion_entre(self.hora_desde, self.hora_hasta)
        if calculada is not None:
            self.duracion_horas = calculada
        super().save(*args, **kwargs)

    @property
    def eficacia_vence(self):
        return sumar_meses(self.fecha, MESES_EFICACIA) if self.fecha else None

    @property
    def estado_eficacia(self):
        """'evaluada', 'vencida', 'por_vencer' (30 días), 'pendiente' o None (no aplica)."""
        if self.estado != 'cerrada':
            return None
        if self.eficacia.get('resultado'):
            return 'evaluada'
        vence = self.eficacia_vence
        hoy = timezone.localdate()
        if vence < hoy:
            return 'vencida'
        return 'por_vencer' if (vence - hoy).days <= 30 else 'pendiente'


class Asistente(AuditableModel):
    sesion = models.ForeignKey(Sesion, on_delete=models.PROTECT, related_name='asistentes')
    trabajador = models.ForeignKey('organizacion.Trabajador', on_delete=models.PROTECT,
                                   related_name='asistencias')
    firma = models.JSONField('Firma', default=dict, blank=True)
    nota = models.DecimalField('Nota (0 a 20)', max_digits=4, decimal_places=1, null=True, blank=True)
    constancia = models.FileField('Constancia o certificado externo', upload_to='capacitacion/constancias/%Y/',
                                  null=True, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Asistente'
        ordering = ['trabajador__apellidos', 'trabajador__nombres']
        constraints = [models.UniqueConstraint(fields=['sesion', 'trabajador'], condition=models.Q(is_active=True),
                                               name='asistente_unico_por_sesion')]

    @property
    def certificado(self):
        """'aprobacion' (nota ≥ 14), 'participacion' o None mientras la sesión no se cierre."""
        if self.sesion.estado != 'cerrada':
            return None
        if self.sesion.con_evaluacion and self.nota is not None and self.nota >= NOTA_APROBATORIA:
            return 'aprobacion'
        return 'participacion'


class ArchivoSesion(AuditableModel):
    sesion = models.ForeignKey(Sesion, on_delete=models.PROTECT, related_name='archivos')
    tipo = models.CharField('Tipo', max_length=12, choices=[('material', 'Material de formación'),
                                                            ('evaluacion', 'Evaluación'),
                                                            ('constancia', 'Constancia / certificado'),
                                                            ('otro', 'Otro')], default='material')
    descripcion = models.CharField('Descripción', max_length=200, blank=True)
    archivo = models.FileField('Archivo', upload_to='capacitacion/material/%Y/')
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        ordering = ['id']


# ---------------------------------------------------------------------------------- inducción
class PlantillaInduccion(AuditableModel):
    """Contenido de cada parte de la inducción según el formato (editable por el Área SIG)."""
    parte = models.CharField('Parte', max_length=16, choices=PARTES_INDUCCION, unique=True)
    # Lista de verificación: [{grupo, tema, descripcion, codigo, enlace}]
    temas = models.JSONField('Temas', default=list, blank=True)
    # [{documento, codigo, enlace, documento_id}] — documento_id enlaza con la lista maestra de Documentos
    documentos = models.JSONField('Documentos que se entregan', default=list, blank=True)
    # [{pregunta, puntos}]
    preguntas = models.JSONField('Preguntas de la evaluación', default=list, blank=True)
    evaluacion_url = models.URLField('Evaluación en línea', blank=True)
    version = models.PositiveSmallIntegerField('Versión del contenido', default=1)
    # [{version, fecha, usuario, motivo, cambios}]
    historial = models.JSONField('Historial de cambios', default=list, blank=True)

    class Meta:
        verbose_name = 'Plantilla de inducción'
        ordering = ['id']


class Induccion(AuditableModel):
    codigo = models.CharField('Código', max_length=20, unique=True, editable=False)
    trabajador = models.ForeignKey('organizacion.Trabajador', on_delete=models.PROTECT, related_name='inducciones')
    tipo = models.CharField('Tipo', max_length=12, choices=TIPOS_INDUCCION, default='induccion')
    fecha_inicio = models.DateField('Inicio', default=timezone.localdate)
    motivo = models.CharField('Motivo de la re-inducción', max_length=200, blank=True)
    motivo_anulacion = models.TextField('Motivo de la anulación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Inducción'
        ordering = ['-fecha_inicio', '-id']

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = siguiente_codigo(Induccion, 'IND', (self.fecha_inicio or timezone.localdate()).year)
        super().save(*args, **kwargs)

    def ultima(self, parte):
        return self.partes.filter(parte=parte, is_active=True).order_by('-intento').first()

    @property
    def estado(self):
        """'completa' (las tres partes aprobadas) o 'en_proceso'."""
        if not self.is_active:
            return 'anulada'
        ok = all((p := self.ultima(k)) and p.estado == 'aprobada' for k, _ in PARTES_INDUCCION)
        return 'completa' if ok else 'en_proceso'


class ParteInduccion(AuditableModel):
    induccion = models.ForeignKey(Induccion, on_delete=models.PROTECT, related_name='partes')
    parte = models.CharField('Parte', max_length=16, choices=PARTES_INDUCCION)
    intento = models.PositiveSmallIntegerField('Intento', default=1)
    responsable = models.CharField('Responsable de la inducción', max_length=150, blank=True)
    fecha = models.DateField('Fecha', null=True, blank=True)
    hora_inicio = models.TimeField('Inicio', null=True, blank=True)
    hora_fin = models.TimeField('Fin', null=True, blank=True)
    # Copias de la plantilla con lo marcado: temas [{grupo, tema, descripcion, codigo, incluido}],
    # documentos [{documento, codigo, entregado}], preguntas [{pregunta, puntos, calificacion}]
    temas = models.JSONField('Temas', default=list, blank=True)
    documentos = models.JSONField('Documentos entregados', default=list, blank=True)
    preguntas = models.JSONField('Evaluación', default=list, blank=True)
    evaluacion_url = models.URLField('Evaluación en línea', blank=True)
    nota_directa = models.DecimalField('Nota de la evaluación en línea', max_digits=4, decimal_places=1, null=True,
                                       blank=True)
    evaluador = models.CharField('Evaluador', max_length=150, blank=True)
    fecha_evaluacion = models.DateField('Fecha de evaluación', null=True, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS_PARTE, default='en_registro')
    firma_responsable = models.JSONField('Firma del responsable', default=dict, blank=True)
    firma_colaborador = models.JSONField('Firma del colaborador', default=dict, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Parte de la inducción'
        ordering = ['induccion', 'parte', 'intento']

    @property
    def nota(self):
        """Nota de 0 a 20: la de la evaluación en línea o la suma de calificaciones llevada a 20."""
        if self.nota_directa is not None:
            return self.nota_directa
        total = sum(Decimal(str(p.get('puntos') or 0)) for p in self.preguntas or [])
        if not total or any(p.get('calificacion') in (None, '') for p in self.preguntas or []):
            return None
        obtenido = sum(Decimal(str(p.get('calificacion') or 0)) for p in self.preguntas)
        return (obtenido * 20 / total).quantize(Decimal('0.1'))
