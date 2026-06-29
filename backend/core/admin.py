"""
eSYNAPSE 360 — Admin de la app core.
El log de auditoría es de solo lectura: nadie puede editarlo ni eliminarlo.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import LogAuditoria, Permiso, Rol, RolUsuario, Usuario


class PermisoInline(admin.TabularInline):
    model = Permiso
    extra = 0
    fields = ('modulo', 'operacion', 'permitido')


class RolUsuarioInline(admin.TabularInline):
    model = RolUsuario
    fk_name = 'usuario'  # RolUsuario tiene varios FK a Usuario (created_by/updated_by)
    extra = 0
    fields = ('rol', 'is_active')


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'area', 'laboratorio', 'cargo', 'is_active')
    list_filter = ('is_active', 'area', 'laboratorio')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'cargo')
    inlines = [RolUsuarioInline]
    fieldsets = UserAdmin.fieldsets + (
        ('Datos eSYNAPSE 360', {'fields': ('area', 'laboratorio', 'cargo', 'telefono')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos eSYNAPSE 360', {'fields': ('email', 'area', 'laboratorio', 'cargo', 'telefono')}),
    )

    def has_delete_permission(self, request, obj=None):
        # Soft delete: los usuarios se desactivan, nunca se eliminan
        return False


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'es_admin_sistema', 'is_active')
    list_filter = ('is_active', 'es_admin_sistema')
    search_fields = ('nombre',)
    inlines = [PermisoInline]

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # El rol Administrador del Sistema no puede modificarse
        if obj is not None and obj.es_admin_sistema:
            return False
        return super().has_change_permission(request, obj)


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('rol', 'modulo', 'operacion', 'permitido')
    list_filter = ('modulo', 'operacion', 'permitido', 'rol')
    search_fields = ('rol__nombre',)


@admin.register(RolUsuario)
class RolUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'is_active', 'created_at', 'created_by')
    list_filter = ('is_active', 'rol')
    search_fields = ('usuario__username', 'rol__nombre')


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'usuario_nombre', 'accion', 'modulo', 'entidad', 'entidad_id', 'campo', 'ip')
    list_filter = ('accion', 'modulo', 'timestamp')
    search_fields = ('usuario_nombre', 'entidad', 'entidad_id', 'referencia')
    date_hierarchy = 'timestamp'

    # Log inmutable: solo lectura
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
