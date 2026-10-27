"""
Organización y personal — datos maestros del núcleo, comunes a todo el sistema:
sedes (con sus niveles y suministros de servicios), áreas (organigrama, incluidos los laboratorios),
puestos (con su perfil) y trabajadores. Siempre habilitado; cada módulo solo los consulta y guarda lo suyo
(SST: peligros y EPP del puesto; Competencia: autorizaciones; Medio ambiente: consumos por suministro; etc.).
El futuro módulo de RRHH extiende estos datos, no los reemplaza.
"""
from django.db import models
from django.utils import timezone

from core.models import AuditableModel

TIPOS_AREA = [('gerencia', 'Gerencia'), ('area', 'Área'), ('laboratorio', 'Laboratorio')]
TIPOS_PUESTO = [('propio', 'Personal de la empresa'), ('tercero', 'Tercero / contratista')]
CAMPOS_PERFIL = ('educacion', 'formacion', 'experiencia', 'habilidades', 'responsabilidades')
TENENCIAS = [('propia', 'Propia'), ('alquilada', 'Alquilada')]
TIPOS_SUMINISTRO = [('energia', 'Energía eléctrica'), ('agua', 'Agua')]
UNIDAD_SUMINISTRO = {'energia': 'kWh', 'agua': 'm³'}
MODALIDADES_SUMINISTRO = [('lectura', 'Lectura del medidor'), ('recibo', 'Recibo de la empresa prestadora')]


def _hist(obj, usuario, accion, **datos):
    obj.historial = list(obj.historial or []) + [{
        'fecha': timezone.localtime().isoformat(timespec='minutes'),
        'usuario': (usuario.get_full_name() or usuario.username) if usuario else 'Sistema',
        'accion': accion, **datos}]


class Sede(AuditableModel):
    """Local donde opera la organización (instalaciones propias o alquiladas). Todo lo que ocurre en un lugar físico
    —consumos, residuos, inspecciones, requisitos del inmueble— se vincula a su sede."""
    nombre = models.CharField('Nombre', max_length=120, unique=True)
    codigo = models.CharField('Código corto', max_length=12, blank=True,
                              help_text='Abreviatura para listados e impresos (p. ej. SO, SA).')
    direccion = models.CharField('Dirección', max_length=250, blank=True)
    ubigeo = models.ForeignKey('core.Ubigeo', verbose_name='Ubigeo (distrito)', on_delete=models.PROTECT, null=True,
                               blank=True, related_name='sedes')
    # Copia del ubigeo elegido (para listados e impresos sin consultas adicionales).
    distrito = models.CharField('Distrito', max_length=80, blank=True)
    provincia = models.CharField('Provincia', max_length=80, blank=True)
    departamento = models.CharField('Departamento', max_length=80, blank=True)
    tenencia = models.CharField('Instalaciones', max_length=10, choices=TENENCIAS, default='propia')
    principal = models.BooleanField('Sede principal (domicilio fiscal)', default=False)
    responsable = models.ForeignKey('Puesto', verbose_name='Puesto responsable de la sede', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='sedes_a_cargo')
    descripcion = models.TextField('Descripción / observaciones', blank=True)
    orden = models.PositiveIntegerField('Orden', default=0)
    is_active = models.BooleanField('Activo', default=True)
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Sede'
        verbose_name_plural = 'Sedes'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class Nivel(AuditableModel):
    """Piso, nivel o bloque de una sede."""
    sede = models.ForeignKey(Sede, verbose_name='Sede', on_delete=models.PROTECT, related_name='niveles')
    nombre = models.CharField('Nombre', max_length=60, help_text='Piso 1, Sótano, Bloque B…')
    orden = models.IntegerField('Orden', default=0)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Nivel / piso'
        verbose_name_plural = 'Niveles / pisos'
        ordering = ['sede', 'orden', 'nombre']
        constraints = [models.UniqueConstraint(fields=['sede', 'nombre'], name='nivel_unico_por_sede')]

    def __str__(self):
        return f'{self.sede.nombre} · {self.nombre}'


class Suministro(AuditableModel):
    """Suministro de un servicio (energía eléctrica o agua) con su medidor: de toda la sede o de uno de sus niveles. Su
    consumo se registra por lectura del medidor o por el recibo de la empresa prestadora."""
    sede = models.ForeignKey(Sede, verbose_name='Sede', on_delete=models.PROTECT, related_name='suministros')
    nivel = models.ForeignKey(Nivel, verbose_name='Nivel (vacío: toda la sede)', on_delete=models.PROTECT, null=True,
                              blank=True, related_name='suministros')
    tipo = models.CharField('Servicio', max_length=8, choices=TIPOS_SUMINISTRO)
    modalidad = models.CharField('Cómo se obtiene el consumo', max_length=8, choices=MODALIDADES_SUMINISTRO,
                                 default='lectura')
    numero = models.CharField('N° de suministro / medidor', max_length=60, blank=True)
    empresa_prestadora = models.CharField('Empresa prestadora', max_length=120, blank=True)
    ubicacion = models.CharField('Ubicación del medidor', max_length=150, blank=True)
    responsable = models.ForeignKey('Puesto', verbose_name='Responsable del registro (vacío: el de la sede)',
                                    on_delete=models.SET_NULL, null=True, blank=True, related_name='suministros_a_cargo')
    is_active = models.BooleanField('Activo', default=True)
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Suministro'
        verbose_name_plural = 'Suministros'
        ordering = ['sede', 'nivel__orden', 'tipo', 'id']

    def __str__(self):
        return self.nombre

    @property
    def unidad(self):
        return UNIDAD_SUMINISTRO.get(self.tipo, '')

    @property
    def nombre(self):
        lugar = self.nivel.nombre if self.nivel_id else 'toda la sede'
        return f'{self.get_tipo_display()} · {self.sede.nombre} · {lugar}{f" ({self.numero})" if self.numero else ""}'

    @property
    def responsable_efectivo(self):
        return self.responsable or self.sede.responsable


class Area(AuditableModel):
    """Unidad del organigrama: gerencia, área o laboratorio."""
    nombre = models.CharField('Nombre', max_length=120, unique=True)
    tipo = models.CharField('Tipo', max_length=12, choices=TIPOS_AREA, default='area')
    padre = models.ForeignKey('self', verbose_name='Depende de', on_delete=models.PROTECT, null=True, blank=True,
                              related_name='subareas')
    proceso = models.ForeignKey('procesos.Proceso', verbose_name='Proceso principal', on_delete=models.PROTECT,
                                null=True, blank=True, related_name='areas_organizacion')
    sede = models.ForeignKey(Sede, verbose_name='Sede', on_delete=models.PROTECT, null=True, blank=True,
                             related_name='areas')
    nivel = models.ForeignKey(Nivel, verbose_name='Nivel / piso', on_delete=models.PROTECT, null=True, blank=True,
                              related_name='areas')
    responsable = models.ForeignKey('Puesto', verbose_name='Puesto responsable', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='areas_a_cargo')
    descripcion = models.TextField('Descripción', blank=True)
    orden = models.PositiveIntegerField('Orden', default=0)
    is_active = models.BooleanField('Activo', default=True)
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Área'
        verbose_name_plural = 'Áreas'
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre

    def descendientes(self):
        ids, pendientes = [], [self.pk]
        while pendientes:
            hijos = list(Area.objects.filter(padre_id__in=pendientes).values_list('pk', flat=True))
            ids += hijos
            pendientes = hijos
        return ids


class Puesto(AuditableModel):
    """Puesto de trabajo con su perfil (requisitos de competencia del manual de funciones)."""
    nombre = models.CharField('Puesto', max_length=150, unique=True)
    sigla = models.CharField('Sigla (firmas)', max_length=12, blank=True,
                             help_text='Tal como se imprime en las firmas de los formatos (GG, GSIG, ASIG…)')
    area = models.ForeignKey(Area, verbose_name='Área', on_delete=models.PROTECT, null=True, blank=True,
                             related_name='puestos')
    reporta_a = models.ForeignKey('self', verbose_name='Reporta a', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='subordinados')
    tipo = models.CharField('Tipo', max_length=8, choices=TIPOS_PUESTO, default='propio')
    proceso = models.ForeignKey('procesos.Proceso', verbose_name='Proceso', on_delete=models.PROTECT, null=True,
                                blank=True, related_name='puestos_organizacion')
    # Perfil del puesto (versionado: cada cambio sube la versión y queda en el historial).
    educacion = models.TextField('Educación', blank=True)
    formacion = models.TextField('Formación', blank=True)
    experiencia = models.TextField('Experiencia', blank=True)
    habilidades = models.TextField('Habilidades', blank=True)
    responsabilidades = models.TextField('Funciones y responsabilidades', blank=True)
    version_perfil = models.PositiveIntegerField('Versión del perfil', default=0)
    is_active = models.BooleanField('Activo', default=True)
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Puesto'
        verbose_name_plural = 'Puestos'
        ordering = ['tipo', 'nombre']

    def __str__(self):
        return self.nombre

    @property
    def tiene_perfil(self):
        return any(getattr(self, c) for c in CAMPOS_PERFIL)


class Trabajador(AuditableModel):
    """Persona que trabaja en la empresa (o tercero que presta servicios), con usuario del sistema opcional."""
    nombres = models.CharField('Nombres', max_length=120)
    apellidos = models.CharField('Apellidos', max_length=120)
    documento = models.CharField('Documento de identidad', max_length=20, blank=True)
    puesto = models.ForeignKey(Puesto, verbose_name='Puesto', on_delete=models.PROTECT, related_name='trabajadores')
    area = models.ForeignKey(Area, verbose_name='Área', on_delete=models.PROTECT, null=True, blank=True,
                             related_name='trabajadores', help_text='Si se deja vacía, la del puesto.')
    empresa = models.CharField('Empresa (terceros)', max_length=150, blank=True)
    correo = models.EmailField('Correo', blank=True)
    telefono = models.CharField('Teléfono', max_length=20, blank=True)
    fecha_ingreso = models.DateField('Fecha de ingreso', null=True, blank=True)
    fecha_cese = models.DateField('Fecha de cese', null=True, blank=True)
    motivo_cese = models.TextField('Motivo del cese', blank=True)
    estado = models.CharField('Estado', max_length=8, choices=[('activo', 'Activo'), ('cesado', 'Cesado')],
                              default='activo')
    usuario = models.OneToOneField('core.Usuario', verbose_name='Usuario del sistema', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='trabajador')
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Trabajador'
        verbose_name_plural = 'Trabajadores'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return self.nombre_completo

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'.strip()

    @property
    def area_efectiva(self):
        return self.area or self.puesto.area


def q_trabajadores_de_sede(sede_id):
    """Trabajadores cuya área efectiva (la suya o la de su puesto) está en la sede."""
    return models.Q(area__sede_id=sede_id) | models.Q(area__isnull=True, puesto__area__sede_id=sede_id)


def sincronizar_usuario(trabajador):
    """
    Copia en el usuario vinculado el cargo, la sigla, el área y el laboratorio que vienen del
    puesto y el área del trabajador. Son los datos que imprimen las firmas de todo el sistema.
    """
    u = trabajador.usuario
    if not u:
        return
    area = trabajador.area_efectiva
    es_lab = bool(area and area.tipo == 'laboratorio')
    # Para un laboratorio, el área es la unidad de la que depende (p. ej. Gerencia Técnica).
    area_texto = (area.padre.nombre if es_lab and area.padre_id else area.nombre) if area else u.area
    datos = {'cargo': trabajador.puesto.nombre[:100], 'sigla_cargo': trabajador.puesto.sigla[:12],
             'area': area_texto[:100], 'laboratorio': (area.nombre if es_lab else '')[:100]}
    cambios = {k: v for k, v in datos.items() if getattr(u, k) != v}
    if cambios:
        type(u).objects.filter(pk=u.pk).update(**cambios)
        for k, v in cambios.items():
            setattr(u, k, v)
