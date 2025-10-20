from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Producto, Carrito, CarritoItem

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
def add_to_cart(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    cart = get_user_cart(request.user)
    
    item, created = CarritoItem.objects.get_or_create(carrito=cart, producto=producto, defaults={'cantidad': 1})
    if not created:
        item.cantidad += 1
        item.save()
        
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