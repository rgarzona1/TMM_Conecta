# tienda/admin.py
from django.contrib import admin
from .models import Producto, Carrito, CarritoItem

# Opcional: Para mejorar la visualización en el admin
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
# Registra los modelos
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Carrito, CarritoAdmin)
# Nota: CarritoItem se añade a través de CarritoInline, no necesita registro directo