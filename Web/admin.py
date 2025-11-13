from django.contrib import admin

# Register your models here.
from .models import MensajeContacto, Producto, Resena, Taller

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
    

@admin.register(Resena)
class ResenaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'calificacion', 'aprobada', 'fecha_creacion')
    list_filter = ('aprobada', 'calificacion', 'fecha_creacion')
    search_fields = ('usuario__username', 'comentario')
    list_editable = ('aprobada',)