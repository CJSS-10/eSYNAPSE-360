"""
Inspecciones de SST y monitoreos de agentes ocupacionales, según el procedimiento de
seguimiento y medición.

Inspecciones: motor de plantillas. Cada formato del procedimiento es una plantilla de una
de cuatro familias:
    - elementos:    una fila por elemento (extintores, luces, detectores, escaleras, herramientas)
                    y una columna por criterio.
    - contenido:    un elemento con su lista de productos (botiquín, kit antiderrame).
    - preguntas:    secciones con preguntas de respuesta única (SSTMA, movilidad, moto lineal).
    - trabajadores: una fila por trabajador y columnas agrupadas por EPP.
Cada inspección guarda una copia de la estructura de su plantilla: si luego la plantilla
cambia, la inspección conserva lo que se inspeccionó.

Flujo de la inspección:  en registro → (firma) → con acciones (ítems «no conforme» con su
acción inmediata) → cerrada.   Anulada: registrada por error, antes de firmar.

Monitoreos: programa anual por agente, registro de cada monitoreo con sus resultados frente
a los límites máximos permisibles y programa de seguimiento de sus recomendaciones.
"""
from datetime import timedelta

from django.db import models
from django.utils import timezone

from core.models import AuditableModel

TIPOS_ELEMENTO = [('extintor', 'Extintor'), ('luz_emergencia', 'Luz de emergencia'),
                  ('detector_humo', 'Detector de humo'), ('escalera', 'Escalera'), ('botiquin', 'Botiquín'),
                  ('kit_antiderrame', 'Kit antiderrame'), ('vehiculo', 'Vehículo'), ('moto', 'Moto lineal')]
FAMILIAS = [('elementos', 'Por elemento'), ('contenido', 'Contenido de un elemento'),
            ('preguntas', 'Por preguntas'), ('trabajadores', 'Por trabajador')]
FRECUENCIAS = [('mensual', 'Mensual'), ('bimestral', 'Bimestral'), ('trimestral', 'Trimestral'),
               ('semestral', 'Semestral'), ('anual', 'Anual'), ('eventual', 'Eventual')]
MESES_FRECUENCIA = {'mensual': 1, 'bimestral': 2, 'trimestral': 3, 'semestral': 6, 'anual': 12}

# Escalas de respuesta: valores posibles (clave, etiqueta) y cuál es «no conforme».
ESCALAS = {
    'c_nc_na': {'nombre': 'Conforme / No conforme / No aplica',
                'valores': [('C', 'C'), ('NC', 'NC'), ('NA', 'NA')], 'malo': 'NC'},
    'si_no_na': {'nombre': 'Sí / No / No aplica', 'valores': [('SI', 'Sí'), ('NO', 'No'), ('NA', 'NA')], 'malo': 'NO'},
    'optimo_mal_na': {'nombre': 'Óptimo / Mal estado / No aplica',
                      'valores': [('OPT', 'Óptimo'), ('MAL', 'Mal estado'), ('NA', 'No aplica')], 'malo': 'MAL'},
    'bueno_mal': {'nombre': 'Bueno / Mal', 'valores': [('B', '✔'), ('M', 'X')], 'malo': 'M'},
}
ESCALAS_CHOICES = [(k, v['nombre']) for k, v in ESCALAS.items()]
TIPOS_INSPECCION = [('planeada', 'Planeada'), ('no_planeada', 'No planeada'), ('otro', 'Otro')]
ESTADOS_INSPECCION = [('en_registro', 'En registro'), ('con_acciones', 'Con acciones pendientes'),
                      ('cerrada', 'Cerrada'), ('anulada', 'Anulada')]

AGENTES_MONITOREO = [('fisico', 'Físico'), ('quimico', 'Químico'), ('biologico', 'Biológico'),
                     ('ergonomico', 'Ergonómico'), ('psicosocial', 'Psicosocial')]
ESTADOS_MONITOREO = [('en_registro', 'En registro'), ('registrado', 'Registrado'), ('anulado', 'Anulado')]
ESTADOS_RECOMENDACION = [('pendiente', 'Pendiente'), ('en_proceso', 'En proceso'), ('ejecutada', 'Ejecutada'),
                         ('no_aplica', 'No aplica')]

DIAS_AVISO = 30


def _siguiente_codigo(modelo, prefijo, anio):
    nums = [int(c.split('-')[1]) for c in modelo.objects.filter(codigo__startswith=f'{prefijo}-',
                                                                codigo__endswith=f'-{anio}')
            .values_list('codigo', flat=True) if c.split('-')[1].isdigit()]
    return f'{prefijo}-{(max(nums) + 1) if nums else 1:03d}-{anio}'


def estado_fecha(fecha, hoy=None):
    """'vencido', 'por_vencer' (dentro de 30 días) o 'vigente'."""
    if not fecha:
        return None
    hoy = hoy or timezone.localdate()
    if fecha < hoy:
        return 'vencido'
    if fecha <= hoy + timedelta(days=DIAS_AVISO):
        return 'por_vencer'
    return 'vigente'


# ============================================================================ inventario
class ElementoSeguridad(AuditableModel):
    """Elemento de seguridad o vehículo que se inspecciona periódicamente."""
    tipo = models.CharField('Tipo', max_length=20, choices=TIPOS_ELEMENTO)
    codigo = models.CharField('Código / N°', max_length=40)
    ubicacion = models.CharField('Ubicación', max_length=150, blank=True)
    piso = models.CharField('Piso', max_length=20, blank=True)
    area = models.ForeignKey('organizacion.Area', verbose_name='Área', on_delete=models.PROTECT, null=True,
                             blank=True, related_name='elementos_seguridad')
    subtipo = models.CharField('Tipo (agente del extintor, tipo de escalera…)', max_length=80, blank=True)
    marca = models.CharField('Marca / modelo', max_length=100, blank=True)
    capacidad = models.CharField('Capacidad', max_length=40, blank=True)
    fecha_fabricacion = models.DateField('Fecha de fabricación', null=True, blank=True)
    fecha_vencimiento = models.DateField('Vencimiento (recarga, SOAT o producto)', null=True, blank=True)
    fecha_prueba_hidrostatica = models.DateField('Próxima prueba hidrostática', null=True, blank=True)
    fecha_revision_tecnica = models.DateField('Revisión técnica vehicular (vence)', null=True, blank=True)
    placa = models.CharField('Placa', max_length=12, blank=True)
    combustible = models.CharField('Tipo de combustible', max_length=30, blank=True)
    # Botiquín y kit: [{producto, cantidad, unidad, vencimiento}]
    contenido = models.JSONField('Contenido mínimo', default=list, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    motivo_baja = models.TextField('Motivo de la baja', blank=True)
    fecha_baja = models.DateField('Fecha de baja', null=True, blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Elemento de seguridad'
        verbose_name_plural = 'Elementos de seguridad'
        ordering = ['tipo', 'codigo']
        constraints = [models.UniqueConstraint(fields=['tipo', 'codigo'], name='elemento_seguridad_unico')]

    def __str__(self):
        return f'{self.get_tipo_display()} {self.codigo}'

    def vencimientos(self, hoy=None):
        """Fechas que vigilar: [{concepto, fecha, estado}]."""
        if not self.is_active:
            return []
        fechas = [('Vencimiento' if self.tipo not in ('vehiculo', 'moto') else 'SOAT', self.fecha_vencimiento),
                  ('Prueba hidrostática', self.fecha_prueba_hidrostatica),
                  ('Revisión técnica', self.fecha_revision_tecnica)]
        for c in self.contenido or []:
            if c.get('vencimiento'):
                from django.utils.dateparse import parse_date
                fechas.append((c.get('producto') or 'Producto', parse_date(str(c['vencimiento'])[:10])))
        return [{'concepto': n, 'fecha': f.isoformat(), 'estado': estado_fecha(f, hoy)} for n, f in fechas if f]


# ============================================================================ plantillas
class PlantillaInspeccion(AuditableModel):
    """Formato de inspección (estructura que se copia a cada inspección)."""
    nombre = models.CharField('Nombre de la inspección', max_length=150, unique=True)
    codigo_formato = models.CharField('Código del formato impreso', max_length=30, blank=True)
    familia = models.CharField('Familia', max_length=14, choices=FAMILIAS)
    tipo_elemento = models.CharField('Elementos que inspecciona', max_length=20, choices=TIPOS_ELEMENTO, blank=True)
    escala = models.CharField('Escala de respuesta', max_length=14, choices=ESCALAS_CHOICES, default='c_nc_na')
    # elementos / trabajadores: [{grupo, nombre, invertido}]; «invertido»: la respuesta buena es la «mala»
    # (p. ej. «Requiere cambio»).
    criterios = models.JSONField('Criterios (columnas)', default=list, blank=True)
    # Filas libres (sin inventario): columnas descriptivas, p. ej. ['Cantidad', 'Tipo / clase de herramienta'].
    columnas_datos = models.JSONField('Columnas descriptivas de las filas libres', default=list, blank=True)
    # preguntas: [{titulo, preguntas: [texto]}]
    secciones = models.JSONField('Secciones y preguntas', default=list, blank=True)
    # contenido por defecto (botiquín / kit) cuando el elemento no tiene el suyo.
    contenido_base = models.JSONField('Contenido mínimo por defecto', default=list, blank=True)
    frecuencia = models.CharField('Frecuencia', max_length=12, choices=FRECUENCIAS, default='mensual')
    objetivo = models.CharField('Objetivo de la inspección', max_length=250, blank=True)
    nota = models.TextField('Nota al pie del formato', blank=True)
    # Caja de control de respaldo (si el formato no está vinculado a la lista maestra).
    version_formato = models.CharField('Versión del formato', max_length=6, default='00')
    fecha_formato = models.DateField('Fecha del formato', null=True, blank=True)
    elaborado = models.CharField('Elaborado (sigla)', max_length=20, default='ASIG')
    revisado = models.CharField('Revisado (sigla)', max_length=20, default='GSIG')
    aprobado = models.CharField('Aprobado (sigla)', max_length=20, default='GG')
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name = 'Plantilla de inspección'
        verbose_name_plural = 'Plantillas de inspección'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def estructura(self):
        """Copia que se guarda en cada inspección."""
        return {'nombre': self.nombre, 'familia': self.familia, 'tipo_elemento': self.tipo_elemento,
                'escala': self.escala, 'criterios': self.criterios, 'columnas_datos': self.columnas_datos,
                'secciones': self.secciones, 'codigo_formato': self.codigo_formato, 'nota': self.nota}


# ============================================================================ inspecciones
class Inspeccion(AuditableModel):
    codigo = models.CharField('Código', max_length=16, unique=True, editable=False)
    plantilla = models.ForeignKey(PlantillaInspeccion, verbose_name='Plantilla', on_delete=models.PROTECT,
                                  related_name='inspecciones')
    estructura = models.JSONField('Estructura inspeccionada', default=dict, blank=True)
    estado = models.CharField('Estado', max_length=14, choices=ESTADOS_INSPECCION, default='en_registro')
    fecha = models.DateField('Fecha de inspección', default=timezone.localdate)
    hora = models.TimeField('Hora de inspección', null=True, blank=True)
    tipo_inspeccion = models.CharField('Tipo de inspección', max_length=12, choices=TIPOS_INSPECCION,
                                       default='planeada')
    tipo_detalle = models.CharField('Otro tipo (detalle)', max_length=120, blank=True)
    area = models.ForeignKey('organizacion.Area', verbose_name='Área inspeccionada', on_delete=models.PROTECT,
                             null=True, blank=True, related_name='inspecciones_sst')
    lugar = models.CharField('Lugar / sede', max_length=150, blank=True)
    responsable_area = models.ForeignKey('organizacion.Trabajador', verbose_name='Responsable del área',
                                         on_delete=models.PROTECT, null=True, blank=True,
                                         related_name='inspecciones_responsable')
    objetivo = models.CharField('Objetivo de la inspección', max_length=250, blank=True)
    n_trabajadores = models.PositiveIntegerField('N° de trabajadores en el centro', null=True, blank=True)
    elemento = models.ForeignKey(ElementoSeguridad, verbose_name='Elemento inspeccionado', on_delete=models.PROTECT,
                                 null=True, blank=True, related_name='inspecciones_propias')
    conductor = models.ForeignKey('organizacion.Trabajador', verbose_name='Conductor', on_delete=models.PROTECT,
                                  null=True, blank=True, related_name='inspecciones_conductor')
    km = models.PositiveIntegerField('Kilometraje', null=True, blank=True)
    inspector = models.ForeignKey('core.Usuario', verbose_name='Responsable de la inspección',
                                  on_delete=models.PROTECT, null=True, blank=True,
                                  related_name='inspecciones_sst')
    conclusiones = models.TextField('Conclusiones / observaciones / recomendaciones', blank=True)
    firma_registro = models.JSONField('Firma del responsable del registro', default=dict, blank=True)
    fecha_cierre = models.DateTimeField('Fecha de cierre', null=True, blank=True)
    motivo_anulacion = models.TextField('Motivo de anulación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    CAMPOS_REGISTRO = ('fecha', 'hora', 'tipo_inspeccion', 'tipo_detalle', 'area', 'lugar', 'responsable_area',
                       'objetivo', 'n_trabajadores', 'conductor', 'km', 'inspector', 'conclusiones')
    ETAPAS = [('registro', ('en_registro',), CAMPOS_REGISTRO)]

    class Meta:
        verbose_name = 'Inspección de SST'
        verbose_name_plural = 'Inspecciones de SST'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = _siguiente_codigo(Inspeccion, 'INS', self.fecha.year)
        super().save(*args, **kwargs)

    def etapas_abiertas(self):
        return [n for n, estados, _ in self.ETAPAS if self.estado in estados]

    @property
    def malo(self):
        return ESCALAS.get(self.estructura.get('escala') or 'c_nc_na', ESCALAS['c_nc_na'])['malo']


class ItemInspeccion(AuditableModel):
    """Fila de la inspección: un elemento, un producto, una pregunta o un trabajador."""
    inspeccion = models.ForeignKey(Inspeccion, on_delete=models.PROTECT, related_name='items')
    orden = models.PositiveIntegerField('N°', default=1)
    seccion = models.CharField('Sección', max_length=200, blank=True)
    texto = models.TextField('Pregunta / descripción', blank=True)
    elemento = models.ForeignKey(ElementoSeguridad, verbose_name='Elemento', on_delete=models.PROTECT, null=True,
                                 blank=True, related_name='items_inspeccion')
    trabajador = models.ForeignKey('organizacion.Trabajador', verbose_name='Trabajador', on_delete=models.PROTECT,
                                   null=True, blank=True, related_name='items_inspeccion_sst')
    datos = models.JSONField('Datos de la fila', default=dict, blank=True)
    # Respuesta por criterio (elementos, trabajadores): {"0": "C", "1": "NC"…} (índice del criterio);
    # respuesta única (preguntas, contenido): {"r": "SI"}.
    resultados = models.JSONField('Resultados', default=dict, blank=True)
    observacion = models.TextField('Observaciones', blank=True)
    no_conforme = models.BooleanField('No conforme', default=False)
    accion = models.TextField('Acción inmediata', blank=True)
    responsable_accion = models.ForeignKey('core.Usuario', verbose_name='Responsable de la acción',
                                           on_delete=models.PROTECT, null=True, blank=True,
                                           related_name='acciones_inspeccion_sst')
    plazo_accion = models.DateField('Plazo de la acción', null=True, blank=True)
    accion_completada = models.BooleanField('Acción completada', default=False)
    fecha_accion_completada = models.DateField('Fecha en que se completó', null=True, blank=True)
    seguimiento_accion = models.TextField('Seguimiento de la acción', blank=True)
    evidencia_accion = models.FileField('Evidencia de la acción', upload_to='sst/inspecciones/%Y/', null=True,
                                        blank=True)
    hallazgo = models.ForeignKey('esynapse_sig.Hallazgo', verbose_name='Hallazgo registrado',
                                 on_delete=models.PROTECT, null=True, blank=True, related_name='items_inspeccion_sst')
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Ítem de inspección'
        verbose_name_plural = 'Ítems de inspección'
        ordering = ['orden', 'id']

    def calcular_no_conforme(self):
        """Algún criterio con la respuesta «mala» de la escala (o la buena, si el criterio es invertido)."""
        est = self.inspeccion.estructura or {}
        escala = ESCALAS.get(est.get('escala') or 'c_nc_na', ESCALAS['c_nc_na'])
        malo = escala['malo']
        bueno = escala['valores'][0][0]
        criterios = est.get('criterios') or []
        for k, v in (self.resultados or {}).items():
            if not v:
                continue
            invertido = False
            if k.isdigit() and int(k) < len(criterios):
                invertido = bool(criterios[int(k)].get('invertido'))
            if (v == bueno) if invertido else (v == malo):
                return True
        return False

    def save(self, *args, **kwargs):
        self.no_conforme = self.calcular_no_conforme()
        super().save(*args, **kwargs)


# ============================================================================ monitoreos
class ProgramaMonitoreo(AuditableModel):
    """Programa anual de monitoreos de agentes ocupacionales."""
    anio = models.PositiveIntegerField('Año', unique=True)
    fecha_actualizacion = models.DateField('Fecha de actualización', null=True, blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Programa anual de monitoreos'
        verbose_name_plural = 'Programas anuales de monitoreos'
        ordering = ['-anio']

    def __str__(self):
        return f'Programa de monitoreos {self.anio}'


class MonitoreoProgramado(AuditableModel):
    programa = models.ForeignKey(ProgramaMonitoreo, on_delete=models.PROTECT, related_name='items')
    orden = models.PositiveIntegerField('Ítem', default=1)
    agente = models.CharField('Agente', max_length=14, choices=AGENTES_MONITOREO)
    detalle = models.CharField('Detalle del agente (p. ej. iluminación)', max_length=120, blank=True)
    fecha_programada = models.DateField('Fecha programada', null=True, blank=True)
    frecuencia = models.CharField('Frecuencia', max_length=12, choices=FRECUENCIAS, default='anual')
    meses = models.JSONField('Meses programados', default=list, blank=True)
    filas_iperc = models.ManyToManyField('sst.FilaIPERC', verbose_name='Filas IPERC que lo originan', blank=True,
                                         related_name='monitoreos_programados')
    comentarios = models.TextField('Comentarios / observaciones', blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Monitoreo programado'
        verbose_name_plural = 'Monitoreos programados'
        ordering = ['orden', 'id']

    @property
    def nombre(self):
        return f'{self.get_agente_display()}' + (f' - {self.detalle}' if self.detalle else '')

    def meses_ejecutados(self):
        return sorted({m.fecha.month for m in self.monitoreos.all() if m.estado == 'registrado'
                       and m.fecha.year == self.programa.anio})


class Monitoreo(AuditableModel):
    """Registro de un monitoreo de agentes (resultados frente a los límites máximos permisibles)."""
    codigo = models.CharField('N° de registro', max_length=16, unique=True, editable=False)
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS_MONITOREO, default='en_registro')
    programados = models.ManyToManyField(MonitoreoProgramado, verbose_name='Monitoreos del programa', blank=True,
                                         related_name='monitoreos')
    area_monitoreada = models.CharField('Área monitoreada', max_length=200)
    fecha = models.DateField('Fecha del monitoreo')
    frecuencia = models.CharField('Frecuencia de monitoreo', max_length=12, choices=FRECUENCIAS, default='anual')
    tipo_riesgo = models.TextField('Tipo de riesgo monitoreado', blank=True)
    n_expuestos = models.PositiveIntegerField('N° de trabajadores expuestos', null=True, blank=True)
    organizacion = models.CharField('Organización que realiza el monitoreo', max_length=200, blank=True)
    # [{agente, resultado, valor, lmp, dentro_lmp (true/false/null)}]
    resultados = models.JSONField('Resultados del monitoreo', default=list, blank=True)
    causas_desviacion = models.TextField('Causas ante desviaciones', blank=True)
    conclusiones = models.TextField('Conclusiones y recomendaciones', blank=True)
    informe = models.FileField('Informe con resultados', upload_to='sst/monitoreos/%Y/', null=True, blank=True)
    firma_registro = models.JSONField('Firma del responsable del registro', default=dict, blank=True)
    motivo_anulacion = models.TextField('Motivo de anulación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Monitoreo de agentes ocupacionales'
        verbose_name_plural = 'Monitoreos de agentes ocupacionales'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = _siguiente_codigo(Monitoreo, 'MON', self.fecha.year)
        super().save(*args, **kwargs)

    @property
    def con_desviaciones(self):
        return any(r.get('dentro_lmp') is False for r in self.resultados or [])


class RecomendacionMonitoreo(AuditableModel):
    """Actividad del programa de seguimiento de recomendaciones de monitoreos."""
    anio = models.PositiveIntegerField('Año del programa')
    monitoreo = models.ForeignKey(Monitoreo, verbose_name='Monitoreo que la origina', on_delete=models.PROTECT,
                                  null=True, blank=True, related_name='recomendaciones')
    orden = models.PositiveIntegerField('Ítem', default=1)
    agente = models.CharField('Agente', max_length=150)
    actividad = models.TextField('Actividad')
    fecha_programada = models.DateField('Fecha programada', null=True, blank=True)
    programacion = models.CharField('Frecuencia / programación (si no hay fecha)', max_length=120, blank=True)
    meses = models.JSONField('Meses programados', default=list, blank=True)
    meses_ejecutados = models.JSONField('Meses ejecutados', default=list, blank=True)
    responsable = models.ForeignKey('core.Usuario', verbose_name='Responsable', on_delete=models.PROTECT, null=True,
                                    blank=True, related_name='recomendaciones_monitoreo')
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS_RECOMENDACION, default='pendiente')
    fecha_ejecucion = models.DateField('Fecha de ejecución', null=True, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Recomendación de monitoreo'
        verbose_name_plural = 'Recomendaciones de monitoreos'
        ordering = ['anio', 'id']

    @property
    def vencida(self):
        return bool(self.fecha_programada and self.estado in ('pendiente', 'en_proceso')
                    and self.fecha_programada < timezone.localdate())
