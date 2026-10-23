"""
Organización y personal — datos maestros del núcleo, comunes a todo el sistema:
áreas (organigrama, incluidos los laboratorios), puestos (con su perfil) y
trabajadores. Siempre habilitado; cada módulo solo los consulta y guarda lo suyo
(SST: peligros y EPP del puesto; Competencia: autorizaciones; etc.).
El futuro módulo de RRHH extiende estos datos, no los reemplaza.
"""
from django.db import models
from django.utils import timezone

from core.models import AuditableModel

TIPOS_AREA = [('gerencia', 'Gerencia'), ('area', 'Área'), ('laboratorio', 'Laboratorio')]
TIPOS_PUESTO = [('propio', 'Personal de la empresa'), ('tercero', 'Tercero / contratista')]
CAMPOS_PERFIL = ('educacion', 'formacion', 'experiencia', 'habilidades', 'responsabilidades')


def _hist(obj, usuario, accion, **datos):
    obj.historial = list(obj.historial or []) + [{
        'fecha': timezone.localtime().isoformat(timespec='minutes'),
        'usuario': (usuario.get_full_name() or usuario.username) if usuario else 'Sistema',
        'accion': accion, **datos}]


class Area(AuditableModel):
    """Unidad del organigrama: gerencia, área o laboratorio."""
    nombre = models.CharField('Nombre', max_length=120, unique=True)
    tipo = models.CharField('Tipo', max_length=12, choices=TIPOS_AREA, default='area')
    padre = models.ForeignKey('self', verbose_name='Depende de', on_delete=models.PROTECT, null=True, blank=True,
                              related_name='subareas')
    proceso = models.ForeignKey('procesos.Proceso', verbose_name='Proceso principal', on_delete=models.PROTECT,
                                null=True, blank=True, related_name='areas_organizacion')
    sede = models.CharField('Sede', max_length=80, blank=True)
    piso = models.CharField('Piso', max_length=20, blank=True)
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
