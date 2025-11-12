from django.contrib import admin
from .models import Producto, Carrito, CarritoItem, ImagenTaller
from .models import TallerEvento

class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio')
    list_filter = ('categoria',)
    search_fields = ('nombre',)

class CarritoItemInline(admin.TabularInline):
    model = CarritoItem
    extra = 0 # No mostrar formularios vacíos por defecto
    readonly_fields = ('get_total',)

class CarritoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha_creacion', 'get_total_bruto')
    inlines = [CarritoItemInline]
    readonly_fields = ('get_total_bruto',)
    def mostrar_total(self, obj):
        return f"${obj.get_total_bruto():,.0f}"
    mostrar_total.short_description = "Total Carrito"


@admin.register(TallerEvento)
class TallerEventoAdmin(admin.ModelAdmin):
    list_display = ('taller_base', 'fecha_proxima', 'precio', 'capacidad', 'lugar', 'tipo_taller')
    list_filter = ('tipo_taller', 'fecha_proxima')
    search_fields = ('taller_base__nombre', 'profesor', 'lugar')
# Registra los modelos
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Carrito, CarritoAdmin)

admin.site.register(ImagenTaller)
