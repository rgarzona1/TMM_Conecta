from pyexpat.errors import messages
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Producto, Carrito, CarritoItem, TallerEvento

# Helper para obtener/crear el carrito del usuario
def get_user_cart(usuario):
    cart, created = Carrito.objects.get_or_create(usuario=usuario)
    return cart

def tienda_home_vista(request):
    """ Muestra la página principal de la tienda """
    
    promociones_simuladas = Producto.objects.all()[:6] 
    
    context = {
        'productos': promociones_simuladas,
        'categorias': Producto.CATEGORIA_CHOICES, # Usamos esto para el menú
    }
    # 🚨 CORRECCIÓN: Añadimos el prefijo 'tienda/' 🚨
    return render(request, 'tienda/tienda_home.html', context)


def categoria_vista(request, categoria_slug):
    """ Muestra la página de categoría """
    
    categoria_key = categoria_slug.upper().replace('-', '_')
    
    productos = Producto.objects.filter(categoria=categoria_key)
    
    context = {
        'productos': productos,
        'nombre_categoria': categoria_slug.capitalize(), # Para el título
    }
    # 🚨 CORRECCIÓN: Añadimos el prefijo 'tienda/' 🚨
    return render(request, 'tienda/tienda_categoria.html', context)


@login_required
def carrito_vista(request):
    """ Muestra el carrito de compras (Mockup: image_a7003c.png) """
    
    cart = get_user_cart(request.user)
    
    # Simulación de costos y descuento
    subtotal = cart.get_total_bruto()
    descuento_aplicado = 0 
    total_final = subtotal - descuento_aplicado
    
    context = {
        'carrito': cart,
        'subtotal': subtotal,
        'total_final': total_final,
        'descuento': descuento_aplicado,
        'direccion': {
            'calle': "Av Libertador Bernardo O'Higgins",
            'numero': "1234, Depto. 5B",
            'ciudad': "Santiago",
            'zip': "8320000"
        }
    }
    # 🚨 CORRECCIÓN: Añadimos el prefijo 'tienda/' 🚨
    return render(request, 'tienda/carrito.html', context)


# Vistas de acción del carrito (prototipo funcional)
@login_required
def add_to_cart(request, producto_id=None, taller_id=None):
    carrito, created = Carrito.objects.get_or_create(usuario=request.user)

    if producto_id:
        producto = get_object_or_404(Producto, pk=producto_id)
        item, created = CarritoItem.objects.get_or_create(
            carrito=carrito,
            producto=producto,
            defaults={'cantidad': 1}
        )
        if not created:
            item.cantidad += 1
        item.save()
        messages.success(request, f"{producto.nombre} agregado al carrito.")

    elif taller_id:
        taller_evento = get_object_or_404(TallerEvento, pk=taller_id)
        item, created = CarritoItem.objects.get_or_create(
            carrito=carrito,
            taller_evento=taller_evento,
            defaults={'cantidad': 1}
        )
        if not created:
            messages.info(request, f"Ya estás inscrito en {taller_evento.taller_base.titulo}.")
        else:
            item.save()
            messages.success(request, f"Taller {taller_evento.taller_base.titulo} agregado al carrito.")

    else:
        messages.error(request, "No se pudo agregar al carrito.")

    return redirect('carrito')


@login_required
def update_cart(request, item_id, action):
    item = get_object_or_404(CarritoItem, id=item_id, carrito__usuario=request.user)
    
    if action == 'add':
        item.cantidad += 1
        item.save()
    elif action == 'remove':
        if item.cantidad > 1:
            item.cantidad -= 1
            item.save()
        else:
            item.delete() 
            
    return redirect('carrito')

def catalogo_talleres_vista(request):
    """Listado de todos los talleres/eventos próximos"""
    talleres = TallerEvento.objects.all().order_by('fecha_proxima')
    return render(request, 'tienda/catalogo_talleres.html', {'talleres': talleres})

def detalle_taller_vista(request, taller_id):
    """Vista con todos los detalles de un taller específico"""
    taller = get_object_or_404(TallerEvento, pk=taller_id)
    return render(request, 'tienda/detalle_taller.html', {'taller': taller})