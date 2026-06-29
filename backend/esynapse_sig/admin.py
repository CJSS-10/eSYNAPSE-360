from django.contrib import admin

from .models import Documento, VersionDocumento


class VersionInline(admin.TabularInline):
    model = VersionDocumento
    fk_name = 'documento'
    extra = 0
    fields = ('version', 'estado', 'archivo', 'elaborado_por', 'aprobado_por', 'fecha_vigencia', 'fecha_proxima_revision')
    readonly_fields = ('estado',)


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'titulo', 'tipo', 'proceso', 'is_active')
    list_filter = ('tipo', 'is_active')
    search_fields = ('codigo', 'titulo')
    inlines = [VersionInline]

    def has_delete_permission(self, request, obj=None):
        return False
