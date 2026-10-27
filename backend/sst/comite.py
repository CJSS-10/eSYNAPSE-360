"""
Comité de Seguridad y Salud en el Trabajo (procedimiento de elección del Comité de SST) y Programa anual de
seguridad, salud ocupacional y medio ambiente (anexo del Plan anual SSOMA).

Comité: el proceso electoral se lleva en papel; aquí se registra su resultado (comité por periodo, miembros,
actas de elección e instalación, T-Registro), las reuniones con su acta firmada adjunta y los acuerdos con su
seguimiento mensual.

Programa SSOMA: objetivos con indicador y meta, actividades con responsable y meses programados / ejecutados.
Aprobado, lo programado queda de solo lectura; un cambio se hace como reprogramación (nueva versión).
"""
from django.db import models
from django.utils import timezone

from core.models import AuditableModel

REPRESENTACION = [('empleador', 'Empleador'), ('trabajadores', 'Trabajadores')]
CONDICION = [('titular', 'Titular'), ('suplente', 'Suplente')]
CARGOS_COMITE = [('presidente', 'Presidente'), ('secretario', 'Secretario'), ('miembro', 'Miembro')]
TIPOS_REUNION = [('instalacion', 'Instalación'), ('ordinaria', 'Ordinaria'), ('extraordinaria', 'Extraordinaria')]
ESTADOS_REUNION = [('programada', 'Programada'), ('realizada', 'Realizada'), ('cancelada', 'Cancelada')]
ESTADOS_ACUERDO = [('pendiente', 'Pendiente'), ('en_proceso', 'En proceso'), ('cumplido', 'Cumplido'),
                   ('no_cumplido', 'No cumplido')]
ESTADOS_PROGRAMA = [('borrador', 'En elaboración'), ('aprobado', 'Aprobado'), ('reprogramacion', 'En reprogramación')]


class ComiteSST(AuditableModel):
    periodo = models.CharField('Periodo', max_length=40, help_text='p. ej. 2025-2027')
    fecha_eleccion = models.DateField('Fecha de la elección', null=True, blank=True)
    fecha_instalacion = models.DateField('Fecha de instalación')
    fecha_fin = models.DateField('Fin del mandato')
    fecha_t_registro = models.DateField('Registro en el T-Registro', null=True, blank=True)
    acta_eleccion = models.FileField('Acta del proceso de elección', upload_to='sst/comite/', null=True, blank=True)
    acta_instalacion = models.FileField('Acta de instalación', upload_to='sst/comite/', null=True, blank=True)
    constancia_t_registro = models.FileField('Constancia del T-Registro', upload_to='sst/comite/', null=True,
                                             blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Comité de SST'
        verbose_name_plural = 'Comités de SST'
        ordering = ['-fecha_instalacion']

    def __str__(self):
        return f'Comité de SST {self.periodo}'

    @property
    def vigente(self):
        hoy = timezone.localdate()
        return self.is_active and self.fecha_instalacion <= hoy <= self.fecha_fin

    def titulares(self, fecha=None):
        """Titulares en funciones en la fecha (hoy por omisión): sin baja anterior a esa fecha y que no hayan cesado
        en la empresa antes de ella."""
        from django.db.models import Q
        f = fecha or timezone.localdate()
        return (self.miembros.filter(is_active=True, condicion='titular')
                .filter(Q(fecha_baja__isnull=True) | Q(fecha_baja__gt=f))
                .filter(Q(trabajador__estado='activo') | Q(trabajador__fecha_cese__gt=f)))


class MiembroComite(AuditableModel):
    comite = models.ForeignKey(ComiteSST, on_delete=models.PROTECT, related_name='miembros')
    trabajador = models.ForeignKey('organizacion.Trabajador', verbose_name='Trabajador', on_delete=models.PROTECT,
                                   related_name='comites_sst')
    representacion = models.CharField('Representa a', max_length=14, choices=REPRESENTACION)
    condicion = models.CharField('Condición', max_length=10, choices=CONDICION, default='titular')
    cargo = models.CharField('Cargo en el comité', max_length=12, choices=CARGOS_COMITE, default='miembro')
    fecha_alta = models.DateField('Desde', default=timezone.localdate)
    fecha_baja = models.DateField('Hasta (baja)', null=True, blank=True)
    motivo_baja = models.TextField('Motivo de la baja', blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Miembro del Comité de SST'
        verbose_name_plural = 'Miembros del Comité de SST'
        ordering = ['representacion', 'condicion', 'id']


class ReunionComite(AuditableModel):
    comite = models.ForeignKey(ComiteSST, on_delete=models.PROTECT, related_name='reuniones')
    codigo = models.CharField('N° de acta', max_length=20, unique=True, editable=False)
    tipo = models.CharField('Tipo', max_length=14, choices=TIPOS_REUNION, default='ordinaria')
    fecha = models.DateField('Fecha')
    hora = models.TimeField('Hora', null=True, blank=True)
    lugar = models.CharField('Lugar', max_length=150, blank=True)
    asistentes = models.ManyToManyField(MiembroComite, verbose_name='Miembros asistentes', blank=True,
                                        related_name='reuniones')
    invitados = models.CharField('Invitados', max_length=250, blank=True)
    agenda = models.JSONField('Agenda', default=list, blank=True)
    desarrollo = models.TextField('Desarrollo de la reunión', blank=True)
    acta_firmada = models.FileField('Acta firmada', upload_to='sst/comite/actas/%Y/', null=True, blank=True)
    proxima_reunion = models.DateField('Próxima reunión', null=True, blank=True)
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS_REUNION, default='programada')
    motivo_cancelacion = models.TextField('Motivo de la cancelación', blank=True)
    historial = models.JSONField('Historial', default=list, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Reunión del Comité de SST'
        verbose_name_plural = 'Reuniones del Comité de SST'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        if not self.codigo:
            anio = self.fecha.year
            nums = [int(c.split('-')[0]) for c in ReunionComite.objects.filter(codigo__endswith=f'-{anio}-CSST')
                    .values_list('codigo', flat=True) if c.split('-')[0].isdigit()]
            self.codigo = f'{(max(nums) + 1) if nums else 1:03d}-{anio}-CSST'
        super().save(*args, **kwargs)

    def quorum(self):
        """Mitad más uno de los miembros titulares (art. 69 del reglamento de la ley de SST)."""
        en_funciones = self.comite.titulares(self.fecha)
        titulares = en_funciones.count()
        presentes = self.asistentes.filter(pk__in=en_funciones.values('pk')).count()
        requerido = titulares // 2 + 1 if titulares else 0
        return {'titulares': titulares, 'presentes': presentes, 'requerido': requerido,
                'hay_quorum': bool(titulares) and presentes >= requerido}


class AcuerdoComite(AuditableModel):
    reunion = models.ForeignKey(ReunionComite, on_delete=models.PROTECT, related_name='acuerdos')
    orden = models.PositiveIntegerField('N°', default=1)
    descripcion = models.TextField('Acuerdo')
    responsable = models.ForeignKey('organizacion.Trabajador', verbose_name='Responsable', on_delete=models.PROTECT,
                                    null=True, blank=True, related_name='acuerdos_comite')
    plazo = models.DateField('Plazo', null=True, blank=True)
    estado = models.CharField('Estado', max_length=12, choices=ESTADOS_ACUERDO, default='pendiente')
    seguimiento = models.JSONField('Seguimiento', default=list, blank=True,
                                   help_text='[{fecha, usuario, estado, comentario}]')
    fecha_cumplimiento = models.DateField('Fecha de cumplimiento', null=True, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Acuerdo del Comité de SST'
        verbose_name_plural = 'Acuerdos del Comité de SST'
        ordering = ['reunion__fecha', 'orden', 'id']

    @property
    def vencido(self):
        return bool(self.plazo and self.estado in ('pendiente', 'en_proceso') and self.plazo < timezone.localdate())


# ============================================================================ Programa SSOMA
class ProgramaSSOMA(AuditableModel):
    anio = models.PositiveIntegerField('Año', unique=True)
    version = models.PositiveIntegerField('Versión', default=1)
    estado = models.CharField('Estado', max_length=16, choices=ESTADOS_PROGRAMA, default='borrador')
    objetivo_general = models.TextField('Objetivo general', blank=True)
    recursos = models.TextField('Recursos', blank=True)
    fecha = models.DateField('Fecha', null=True, blank=True)
    fecha_actualizacion = models.DateField('Fecha de actualización', null=True, blank=True)
    # [{nombre, cargo, fecha, origen?}]
    elaborado = models.JSONField('Elaborado por', default=dict, blank=True)
    revisado = models.JSONField('Revisado por', default=dict, blank=True)
    aprobado = models.JSONField('Aprobado por', default=list, blank=True)
    acta_aprobacion = models.FileField('Acta de aprobación firmada (papel)', upload_to='sst/comite/programa/%Y/',
                                       null=True, blank=True)
    reunion_aprobacion = models.ForeignKey(ReunionComite, verbose_name='Reunión del Comité que lo aprobó',
                                           on_delete=models.PROTECT, null=True, blank=True,
                                           related_name='programas_aprobados')
    historial = models.JSONField('Historial', default=list, blank=True)

    class Meta:
        verbose_name = 'Programa anual SSOMA'
        verbose_name_plural = 'Programas anuales SSOMA'
        ordering = ['-anio']

    def __str__(self):
        return f'Programa anual SSOMA {self.anio}'


class ObjetivoSSOMA(AuditableModel):
    programa = models.ForeignKey(ProgramaSSOMA, on_delete=models.PROTECT, related_name='objetivos')
    codigo = models.CharField('Código', max_length=12)
    descripcion = models.TextField('Objetivo')
    orden = models.PositiveIntegerField('Orden', default=1)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Objetivo del programa SSOMA'
        verbose_name_plural = 'Objetivos del programa SSOMA'
        ordering = ['orden', 'id']


class ActividadSSOMA(AuditableModel):
    programa = models.ForeignKey(ProgramaSSOMA, on_delete=models.PROTECT, related_name='actividades')
    objetivo = models.ForeignKey(ObjetivoSSOMA, verbose_name='Objetivo', on_delete=models.PROTECT,
                                 related_name='actividades')
    orden = models.PositiveIntegerField('Ítem', default=1)
    descripcion = models.TextField('Actividad / objetivo específico')
    indicador = models.CharField('Indicador', max_length=250, blank=True)
    meta = models.CharField('Meta', max_length=60, blank=True)
    responsable = models.ForeignKey('organizacion.Puesto', verbose_name='Responsable', on_delete=models.PROTECT,
                                    null=True, blank=True, related_name='actividades_ssoma')
    area = models.ForeignKey('organizacion.Area', verbose_name='Área', on_delete=models.PROTECT, null=True,
                             blank=True, related_name='actividades_ssoma')
    meses = models.JSONField('Meses programados', default=list, blank=True)
    meses_ejecutados = models.JSONField('Meses ejecutados', default=list, blank=True)
    # {mes: texto de la evidencia}
    evidencias = models.JSONField('Evidencias por mes', default=dict, blank=True)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Actividad del programa SSOMA'
        verbose_name_plural = 'Actividades del programa SSOMA'
        ordering = ['objetivo__orden', 'orden', 'id']

    @property
    def avance(self):
        p = len(self.meses or [])
        return round(100 * len([m for m in self.meses_ejecutados or [] if m in (self.meses or [])]) / p) if p else 0

    def avance_a_la_fecha(self, mes):
        """Ejecutadas / programadas hasta el mes dado (para el indicador del periodo)."""
        prog = [m for m in self.meses or [] if m <= mes]
        if not prog:
            return None
        return round(100 * len([m for m in self.meses_ejecutados or [] if m in prog]) / len(prog))
