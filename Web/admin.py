from django.contrib import admin

# Register your models here.
from .models import MensajeContacto, Producto, Taller

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'activo', 'destacado')
    list_filter = ('activo', 'destacado')
    search_fields = ('nombre',)
    list_editable = ('activo', 'destacado')

@admin.register(Taller)
class TallerAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha', 'valor', 'activo', 'destacado')
    list_filter = ('activo', 'destacado')
    search_fields = ('titulo',)
    list_editable = ('activo', 'destacado')
    
@admin.register(MensajeContacto)
class MensajeContactoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'correo_electronico', 'asunto', 'fecha_envio', 'suscripcion')
    list_filter = ('asunto', 'suscripcion', 'fecha_envio')
    search_fields = ('nombre_completo', 'correo_electronico', 'mensaje')
    readonly_fields = ('fecha_envio',)