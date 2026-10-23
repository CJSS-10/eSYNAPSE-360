"""
M7 — Procesos: catálogo oficial de procesos del SIG, su mapa y la ficha de
caracterización de cada proceso con control de versiones y firmas
(elabora, revisa, aprueba). El resto de módulos usa este catálogo.
"""
import hashlib
import json

from django.db import models

from core.models import AuditableModel

TIPOS_PROCESO = [
    ('estrategico', 'Estratégico'),
    ('operativo', 'Operativo'),
    ('soporte', 'Soporte'),
]

ESTADOS_FICHA = [
    ('borrador', 'En elaboración'),
    ('en_revision', 'En revisión'),
    ('en_aprobacion', 'En aprobación'),
    ('vigente', 'Vigente'),
    ('obsoleta', 'Obsoleta'),
]
EN_CURSO = ('borrador', 'en_revision', 'en_aprobacion')

FRECUENCIAS = [
    ('mensual', 'Mensual'),
    ('trimestral', 'Trimestral'),
    ('semestral', 'Semestral'),
    ('anual', 'Anual'),
]

ESTADOS_RESULTADO = [
    ('cumple', 'Cumple'),
    ('en_riesgo', 'En riesgo'),
    ('no_cumple', 'No cumple'),
]

ORIGENES_AVISO = [
    ('documento', 'Documento aprobado'),
    ('cambio', 'Cambio aprobado'),
    ('manual', 'Registrado a mano'),
]


class Proceso(AuditableModel):
    """Proceso del catálogo. Los subprocesos cuelgan de su proceso padre."""
    nombre = models.CharField('Nombre', max_length=120, unique=True)
    tipo = models.CharField('Tipo de proceso', max_length=12, choices=TIPOS_PROCESO)
    padre = models.ForeignKey('self', verbose_name='Proceso padre', on_delete=models.PROTECT,
                              null=True, blank=True, related_name='subprocesos')
    responsable_cargo = models.CharField('Cargo responsable', max_length=120, blank=True)
    responsable = models.ForeignKey('core.Usuario', verbose_name='Usuario responsable', on_delete=models.PROTECT,
                                    null=True, blank=True, related_name='procesos_a_cargo',
                                    help_text='Recibe los avisos de ficha por revisar')
    detalle_mapa = models.CharField('Detalle en el mapa', max_length=200, blank=True)
    orden = models.PositiveIntegerField('Orden', default=0)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Proceso'
        verbose_name_plural = 'Procesos'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre

    @property
    def ficha_vigente(self):
        return self.fichas.filter(estado='vigente').first()

    @property
    def ficha_en_curso(self):
        return self.fichas.filter(estado__in=EN_CURSO).first()

    def ids_con_subprocesos(self):
        return [self.pk] + list(self.subprocesos.filter(is_active=True).values_list('pk', flat=True))

    @classmethod
    def buscar_por_texto(cls, texto):
        """Proceso del catálogo cuyo nombre coincide con un texto escrito a mano."""
        t = (texto or '').strip().lower()
        if not t:
            return None
        alias = {'sig': 'Sistema Integrado de Gestión', 'alta dirección': 'Gestión Estratégica',
                 'alta direccion': 'Gestión Estratégica'}
        t = alias.get(t, t).lower()
        for p in cls.objects.filter(is_active=True):
            if p.nombre.lower() == t:
                return p
        return None


class Ficha(AuditableModel):
    """Versión de la ficha de caracterización de un proceso."""
    proceso = models.ForeignKey(Proceso, on_delete=models.PROTECT, related_name='fichas')
    version = models.CharField('Versión', max_length=4)
    estado = models.CharField('Estado', max_length=15, choices=ESTADOS_FICHA, default='borrador')
    motivo_cambio = models.TextField('Motivo de la versión', blank=True)

    objetivo = models.TextField('Objetivo del proceso', blank=True)
    responsable = models.CharField('Responsable', max_length=120, blank=True)
    alcance = models.TextField('Alcance', blank=True)
    recurso_humano = models.TextField('Recursos humanos', blank=True)
    recurso_economico = models.TextField('Recursos económicos', blank=True)
    recurso_tecnologico = models.TextField('Recursos tecnológicos', blank=True)

    # Firmas: [quién, cuándo, desde qué IP] y huella del contenido firmado
    elaborado_por = models.ForeignKey('core.Usuario', verbose_name='Elaborado por', on_delete=models.PROTECT,
                                      null=True, blank=True, related_name='fichas_elaboradas')
    fecha_elaboracion = models.DateTimeField('Fecha de elaboración', null=True, blank=True)
    revisado_por = models.ForeignKey('core.Usuario', verbose_name='Revisado por', on_delete=models.PROTECT,
                                     null=True, blank=True, related_name='fichas_revisadas')
    fecha_revision = models.DateTimeField('Fecha de revisión', null=True, blank=True)
    aprobado_por = models.ForeignKey('core.Usuario', verbose_name='Aprobado por', on_delete=models.PROTECT,
                                     null=True, blank=True, related_name='fichas_aprobadas')
    fecha_aprobacion = models.DateTimeField('Fecha de aprobación', null=True, blank=True)
    firmas = models.JSONField('Registro de firmas', default=list, blank=True)
    hash_contenido = models.CharField('Huella del contenido aprobado', max_length=64, blank=True)
    # Devoluciones: [{fecha, usuario, etapa, comentarios}]
    devoluciones = models.JSONField('Devoluciones', default=list, blank=True)

    # Etapa cerrada = solo lectura: el contenido solo se edita en elaboración.
    CAMPOS_CONTENIDO = ('objetivo', 'responsable', 'alcance', 'recurso_humano', 'recurso_economico',
                        'recurso_tecnologico', 'motivo_cambio')
    ETAPAS = (
        ('elaboracion', ('borrador',), CAMPOS_CONTENIDO),
    )
    NOMBRES_ETAPA = {'elaboracion': 'elaboración'}

    class Meta:
        verbose_name = 'Ficha de caracterización'
        verbose_name_plural = 'Fichas de caracterización'
        ordering = ['proceso__orden', '-id']
        constraints = [models.UniqueConstraint(fields=['proceso', 'version'], name='unique_ficha_proceso_version')]

    def __str__(self):
        return f'{self.proceso} v{self.version} ({self.get_estado_display()})'

    def etapas_abiertas(self):
        return [nombre for nombre, estados, _ in self.ETAPAS if self.estado in estados]

    @property
    def editable(self):
        return self.estado == 'borrador'

    def contenido(self):
        """Contenido de la ficha en forma estable (para la huella de lo firmado)."""
        return {
            'proceso': self.proceso.nombre, 'version': self.version, 'tipo': self.proceso.tipo,
            **{c: getattr(self, c) for c in self.CAMPOS_CONTENIDO},
            'actividades': [[a.seccion, sorted(a.proveedores.values_list('nombre', flat=True)), a.proveedor_otro,
                             a.entrada, a.actividad, a.control, sorted(a.clientes.values_list('nombre', flat=True)),
                             a.cliente_otro, a.salida] for a in self.actividades.all()],
            'documentos': [[d.documento_id, d.descripcion] for d in self.documentos.all()],
            'registros': [r.descripcion for r in self.registros.all()],
            'indicadores': [[i.nombre, i.calculo, i.meta, i.frecuencia, i.responsable] for i in self.indicadores.all()],
        }

    def calcular_hash(self):
        return hashlib.sha256(json.dumps(self.contenido(), ensure_ascii=False, sort_keys=True,
                                         default=str).encode()).hexdigest()

    @staticmethod
    def siguiente_version(proceso):
        nums = [int(v) for v in proceso.fichas.values_list('version', flat=True) if str(v).isdigit()]
        return f'{(max(nums) + 1 if nums else 1):02d}'


class _Activos(models.Manager):
    """Las filas quitadas de una ficha en elaboración se dan de baja (nunca se borran)."""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class _FilaFicha(AuditableModel):
    orden = models.PositiveIntegerField('Orden', default=0)
    is_active = models.BooleanField('Activo', default=True)

    objects = _Activos()
    todos = models.Manager()

    class Meta:
        abstract = True
        ordering = ['orden', 'id']


class Actividad(_FilaFicha):
    """Fila de la descripción del proceso: proveedor → entrada → actividad → control → cliente → salida."""
    ficha = models.ForeignKey(Ficha, on_delete=models.PROTECT, related_name='actividades')
    seccion = models.CharField('Subtítulo de sección', max_length=150, blank=True,
                               help_text='Se imprime como franja antes de esta actividad')
    proveedores = models.ManyToManyField(Proceso, verbose_name='Procesos proveedores', blank=True,
                                         related_name='actividades_como_proveedor')
    proveedor_otro = models.CharField('Otro proveedor', max_length=150, blank=True,
                                      help_text='Cliente, proveedor externo, todos los procesos…')
    entrada = models.TextField('Entrada', blank=True)
    actividad = models.TextField('Actividad')
    control = models.TextField('Medida de control', blank=True)
    clientes = models.ManyToManyField(Proceso, verbose_name='Procesos clientes', blank=True,
                                      related_name='actividades_como_cliente')
    cliente_otro = models.CharField('Otro cliente', max_length=150, blank=True)
    salida = models.TextField('Salida', blank=True)

    class Meta(_FilaFicha.Meta):
        verbose_name = 'Actividad del proceso'
        verbose_name_plural = 'Actividades del proceso'

    def texto_proveedor(self):
        return '\n'.join([p.nombre for p in self.proveedores.all()] + ([self.proveedor_otro] if self.proveedor_otro else []))

    def texto_cliente(self):
        return '\n'.join([p.nombre for p in self.clientes.all()] + ([self.cliente_otro] if self.cliente_otro else []))


class DocumentoFicha(_FilaFicha):
    """Documento asociado: de la lista maestra o descrito mientras no esté en ella."""
    ficha = models.ForeignKey(Ficha, on_delete=models.PROTECT, related_name='documentos')
    documento = models.ForeignKey('esynapse_sig.Documento', verbose_name='Documento de la lista maestra',
                                  on_delete=models.PROTECT, null=True, blank=True, related_name='fichas_proceso')
    descripcion = models.CharField('Descripción', max_length=255, blank=True)

    class Meta(_FilaFicha.Meta):
        verbose_name = 'Documento asociado'
        verbose_name_plural = 'Documentos asociados'

    def texto(self):
        return self.documento.titulo if self.documento_id else self.descripcion


class RegistroFicha(_FilaFicha):
    """Registro que genera el proceso."""
    ficha = models.ForeignKey(Ficha, on_delete=models.PROTECT, related_name='registros')
    descripcion = models.CharField('Registro', max_length=255)

    class Meta(_FilaFicha.Meta):
        verbose_name = 'Registro del proceso'
        verbose_name_plural = 'Registros del proceso'


class Indicador(_FilaFicha):
    """Indicador de seguimiento y medición del proceso."""
    ficha = models.ForeignKey(Ficha, on_delete=models.PROTECT, related_name='indicadores')
    nombre = models.CharField('Nombre del indicador', max_length=200)
    calculo = models.TextField('Forma de cálculo', blank=True)
    meta = models.CharField('Meta', max_length=60, blank=True)
    frecuencia = models.CharField('Frecuencia', max_length=12, choices=FRECUENCIAS, default='mensual')
    responsable = models.CharField('Responsable', max_length=120, blank=True)

    class Meta(_FilaFicha.Meta):
        verbose_name = 'Indicador del proceso'
        verbose_name_plural = 'Indicadores del proceso'


class ResultadoIndicador(AuditableModel):
    """Resultado de un indicador en un periodo (se registra a mano hasta que exista M4)."""
    proceso = models.ForeignKey(Proceso, on_delete=models.PROTECT, related_name='resultados')
    indicador = models.CharField('Indicador', max_length=200)
    periodo = models.DateField('Periodo (primer día del mes)')
    valor = models.CharField('Resultado', max_length=60)
    estado = models.CharField('Estado', max_length=10, choices=ESTADOS_RESULTADO)
    comentario = models.TextField('Comentario', blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Resultado de indicador'
        verbose_name_plural = 'Resultados de indicadores'
        ordering = ['-periodo', 'indicador']


class Aviso(AuditableModel):
    """Aviso «ficha por revisar»: algo cambió en el proceso y su ficha puede estar desactualizada."""
    proceso = models.ForeignKey(Proceso, on_delete=models.PROTECT, related_name='avisos')
    origen = models.CharField('Origen', max_length=12, choices=ORIGENES_AVISO, default='manual')
    motivo = models.TextField('Motivo')
    atendido = models.BooleanField('Atendido', default=False)
    ficha_atencion = models.ForeignKey(Ficha, verbose_name='Atendido con la versión', on_delete=models.PROTECT,
                                       null=True, blank=True, related_name='avisos_atendidos')
    descartado_motivo = models.TextField('Motivo del descarte', blank=True)
    fecha_atencion = models.DateTimeField('Fecha de atención', null=True, blank=True)

    class Meta:
        verbose_name = 'Aviso de ficha por revisar'
        verbose_name_plural = 'Avisos de fichas por revisar'
        ordering = ['atendido', '-created_at']


def avisar_ficha_por_revisar(proceso, motivo, origen='manual', usuario=None):
    """Crea el aviso para el responsable del proceso (no modifica la ficha)."""
    if not proceso:
        return None
    return Aviso.objects.create(proceso=proceso, motivo=motivo, origen=origen, created_by=usuario,
                                updated_by=usuario)
