"""
eSYNAPSE 360 — Modelos de la app core (Fase 0).
Usuario personalizado, roles con permisos granulares y log de auditoría inmutable.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import ACCIONES_AUDITORIA, MODULOS, OPERACIONES


class AuditableModel(models.Model):
    """
    Base abstracta: todo modelo del SIGE lleva auditoría de creación/edición.
    Regla de desarrollo #2 del CLAUDE.md.
    """
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Fecha de actualización', auto_now=True)
    created_by = models.ForeignKey(
        'core.Usuario',
        verbose_name='Creado por',
        on_delete=models.PROTECT,
        related_name='%(class)s_creados',
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        'core.Usuario',
        verbose_name='Actualizado por',
        on_delete=models.PROTECT,
        related_name='%(class)s_actualizados',
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class Usuario(AbstractUser):
    """
    Usuario del sistema. Extiende AbstractUser con los campos del CLAUDE.md.
    Nunca se elimina físicamente — se desactiva con is_active=False (soft delete).
    """
    email = models.EmailField('Correo electrónico', unique=True)
    area = models.CharField('Área', max_length=100)
    laboratorio = models.CharField('Laboratorio', max_length=100, blank=True)
    cargo = models.CharField('Cargo', max_length=100)
    telefono = models.CharField('Teléfono', max_length=20, blank=True)
    # is_active ya viene en AbstractUser — se usa para soft delete

    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Fecha de actualización', auto_now=True)
    created_by = models.ForeignKey(
        'self', verbose_name='Creado por', on_delete=models.PROTECT,
        related_name='usuarios_creados', null=True, blank=True,
    )
    updated_by = models.ForeignKey(
        'self', verbose_name='Actualizado por', on_delete=models.PROTECT,
        related_name='usuarios_actualizados', null=True, blank=True,
    )

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['username']

    def __str__(self):
        nombre = self.get_full_name() or self.username
        return f'{nombre} ({self.cargo})' if self.cargo else nombre

    def tiene_permiso(self, modulo: str, operacion: str) -> bool:
        """
        Un usuario con múltiples roles tiene la UNIÓN de todos sus permisos
        (regla 0.2 de SIGE_Flujos_Detallados.md). Superusuario: acceso total.
        """
        if self.is_superuser:
            return True
        return Permiso.objects.filter(
            rol__usuarios_asignados__usuario=self,
            rol__usuarios_asignados__is_active=True,
            rol__is_active=True,
            modulo=modulo,
            operacion=operacion,
            permitido=True,
        ).exists()


class Rol(AuditableModel):
    """
    Rol del sistema (ej: Metrólogo, Encargado de Lab, Comercial).
    El rol 'Administrador del Sistema' (es_admin_sistema=True) no puede
    modificarse ni eliminarse.
    """
    nombre = models.CharField('Nombre del rol', max_length=100, unique=True)
    descripcion = models.TextField('Descripción', blank=True)
    es_admin_sistema = models.BooleanField('Es administrador del sistema', default=False)
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Permiso(AuditableModel):
    """
    Permiso granular: una operación sobre un módulo, asignada a un rol.
    Combinaciones posibles: 36 módulos × 5 operaciones por rol.
    """
    MODULO_CHOICES = MODULOS
    OPERACION_CHOICES = OPERACIONES

    rol = models.ForeignKey(
        Rol, verbose_name='Rol', on_delete=models.CASCADE, related_name='permisos'
    )
    modulo = models.CharField('Módulo', max_length=50, choices=MODULO_CHOICES)
    operacion = models.CharField('Operación', max_length=20, choices=OPERACION_CHOICES)
    permitido = models.BooleanField('Permitido', default=True)

    class Meta:
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'
        constraints = [
            models.UniqueConstraint(
                fields=['rol', 'modulo', 'operacion'],
                name='unique_permiso_rol_modulo_operacion',
            )
        ]
        ordering = ['rol', 'modulo', 'operacion']

    def __str__(self):
        return f'{self.rol} — {self.get_modulo_display()} — {self.get_operacion_display()}'


class RolUsuario(AuditableModel):
    """
    Asignación de roles a usuarios (muchos a muchos con auditoría).
    Los permisos se aplican inmediatamente al asignar.
    """
    usuario = models.ForeignKey(
        Usuario, verbose_name='Usuario', on_delete=models.CASCADE,
        related_name='roles_asignados',
    )
    rol = models.ForeignKey(
        Rol, verbose_name='Rol', on_delete=models.CASCADE,
        related_name='usuarios_asignados',
    )
    is_active = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Rol de usuario'
        verbose_name_plural = 'Roles de usuarios'
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'rol'], name='unique_rol_usuario'
            )
        ]
        ordering = ['usuario', 'rol']

    def __str__(self):
        return f'{self.usuario.username} → {self.rol.nombre}'


class LogAuditoria(models.Model):
    """
    Log de auditoría INMUTABLE (sección 0.3 de SIGE_Flujos_Detallados.md).
    Ningún usuario puede editar ni eliminar entradas. Retención mínima: 5 años.
    No hereda de AuditableModel: el log no se edita jamás.
    """
    timestamp = models.DateTimeField('Timestamp', auto_now_add=True, db_index=True)
    usuario = models.ForeignKey(
        Usuario, verbose_name='Usuario', on_delete=models.PROTECT,
        related_name='acciones_auditoria', null=True, blank=True,
    )
    usuario_nombre = models.CharField('Nombre del usuario', max_length=255, blank=True)
    rol = models.CharField('Rol', max_length=255, blank=True)
    ip = models.GenericIPAddressField('Dirección IP', null=True, blank=True)
    dispositivo = models.CharField('Dispositivo / User-Agent', max_length=255, blank=True)
    modulo = models.CharField('Módulo', max_length=50, db_index=True, blank=True)
    accion = models.CharField('Acción', max_length=30, choices=ACCIONES_AUDITORIA, db_index=True)
    entidad = models.CharField('Entidad', max_length=100, blank=True)
    entidad_id = models.CharField('ID de la entidad', max_length=50, blank=True)
    campo = models.CharField('Campo', max_length=100, blank=True)
    valor_anterior = models.TextField('Valor anterior', null=True, blank=True)
    valor_nuevo = models.TextField('Valor nuevo', null=True, blank=True)
    referencia = models.CharField('Referencia', max_length=100, blank=True)
    detalle = models.JSONField('Detalle adicional', null=True, blank=True)

    class Meta:
        verbose_name = 'Entrada de log de auditoría'
        verbose_name_plural = 'Log de auditoría'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['entidad', 'entidad_id']),
            models.Index(fields=['usuario', 'timestamp']),
        ]

    def __str__(self):
        return f'[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.usuario_nombre} — {self.accion} — {self.entidad}'

    # ---- Inmutabilidad: el log no se edita ni se elimina ----
    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError('El log de auditoría es inmutable: no se puede editar una entrada.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError('El log de auditoría es inmutable: no se puede eliminar una entrada.')


# ============================================================
# CONFIGURACIÓN DEL SISTEMA (marca white-label + licenciamiento)
# ============================================================

class ConfiguracionSistema(models.Model):
    """
    Configuración global (singleton). Permite personalizar la marca del
    sistema por instalación/cliente sin tocar código (white-label).
    """
    nombre_sistema = models.CharField('Nombre del sistema', max_length=100, default='eSYNAPSE 360°')
    nombre_corto = models.CharField('Nombre corto / sigla', max_length=30, default='eSYNAPSE 360°', blank=True)
    subtitulo = models.CharField('Subtítulo / empresa', max_length=150, default='Metrindust S.A.C.', blank=True)
    logo = models.FileField('Logo del producto', upload_to='config/', null=True, blank=True)
    logo_empresa = models.FileField('Logo de la empresa (cliente)', upload_to='config/', null=True, blank=True)
    color_primario = models.CharField('Color primario (hex)', max_length=7, blank=True)
    # --- Formato "Hoja de Vida" de Equipos: vínculo con la lista maestra (M6) ---
    formato_hv_codigo = models.CharField(
        'Documento formato Hoja de Vida (código)', max_length=30, blank=True,
        help_text='Código del documento de la lista maestra que define el formato; '
                  'el PDF toma de su versión vigente el código, la versión y la fecha de aprobación.',
    )
    formato_hv_elaborado = models.CharField('Sigla Elaborado', max_length=20, blank=True)
    formato_hv_revisado = models.CharField('Sigla Revisado', max_length=20, blank=True)
    formato_hv_aprobado = models.CharField('Sigla Aprobado', max_length=20, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración del sistema'
        verbose_name_plural = 'Configuración del sistema'

    def __str__(self):
        return self.nombre_sistema

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    @classmethod
    def cargar(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ModuloHabilitado(models.Model):
    """
    Registro de licenciamiento: qué módulos están habilitados en esta
    instalación. Permite vender el sistema por módulos. Lleva las
    dependencias para no habilitar/deshabilitar de forma incoherente.
    """
    clave = models.CharField('Clave', max_length=40, unique=True)
    nombre = models.CharField('Nombre', max_length=100)
    habilitado = models.BooleanField('Habilitado', default=True)
    dependencias = models.JSONField('Depende de', default=list, blank=True)
    orden = models.PositiveIntegerField('Orden', default=0)

    class Meta:
        verbose_name = 'Módulo habilitado'
        verbose_name_plural = 'Módulos habilitados (licenciamiento)'
        ordering = ['orden']

    def __str__(self):
        return f'{self.nombre} ({"ON" if self.habilitado else "OFF"})'

    @classmethod
    def claves_habilitadas(cls):
        """Conjunto de claves de módulos habilitados (incluye los núcleo)."""
        from .constants import MODULOS_NUCLEO
        habilitados = set(cls.objects.filter(habilitado=True).values_list('clave', flat=True))
        habilitados.update(MODULOS_NUCLEO)
        return habilitados
