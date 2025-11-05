from email.mime import base
import traceback
import django
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.views.decorators.http import require_POST
from django.urls import reverse
from flask import json
from .models import Producto, Carrito, CarritoItem, TallerEvento

#IMPORTACIONES PARA MERCADOPAGO
import mercadopago
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from .models import Orden, OrdenItem
from .utils import obtener_items_de_carrito
from django.utils import timezone

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
    return render(request, 'tienda/tienda_home.html', context)


def categoria_vista(request, categoria_slug):
    """ Muestra la página de categoría """
    
    categoria_key = categoria_slug.upper().replace('-', '_')
    
    productos = Producto.objects.filter(categoria=categoria_key)
    
    context = {
        'productos': productos,
        'nombre_categoria': categoria_slug.capitalize(), # Para el título
    }

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
    
    if item.taller_evento:
        messages.info(request, "No se puede modificar la cantidad de un taller.")
        return redirect('carrito')
    
    if action == 'add':
        item.cantidad += 1
        item.save()
        messages.success(request, "Cantidad actualizada.")
    elif action == 'remove':
        if item.cantidad > 1:
            item.cantidad -= 1
            item.save()
            messages.success(request, "Cantidad actualizada.")
        else:
            item.delete()
            messages.success(request, "Producto eliminado del carrito.")
            
    return redirect('carrito')

def catalogo_talleres_vista(request):
    """Listado de todos los talleres/eventos próximos"""
    talleres = TallerEvento.objects.all().order_by('fecha_proxima')
    return render(request, 'tienda/catalogo_talleres.html', {'talleres': talleres})

def detalle_taller_vista(request, taller_id):
    """Vista con todos los detalles de un taller específico"""
    taller = get_object_or_404(TallerEvento, pk=taller_id)
    return render(request, 'tienda/detalle_taller.html', {'taller': taller})

#VISTAS MERCADO PAGO
#CLIENTE
def _mp_client():
    return mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

@login_required
def checkout_vista(request):
    """Pantalla de confirmación antes del pago"""
    carrito = get_user_cart(request.user)
    if not carrito.items.exists():
        messages.warning(request, "Tu carrito está vacío.")
        return redirect('carrito')

    subtotal = carrito.get_total_bruto()
    total_final = subtotal  # Podrías aplicar descuentos luego aquí

    return render(request, 'tienda/checkout.html', {
        'carrito': carrito,
        'subtotal': subtotal,
        'total_final': total_final,
    })

def crear_preferencia(request):
    try:
        if not request.user.is_authenticated:
            return redirect('login') #redirige a login si la sesion no esta iniciada
        
        #construir items desde carrito existente
        
        items, total = obtener_items_de_carrito(request.user)
        
        if not items:
            return JsonResponse({'error': 'El carrito está vacío.'}, status=400)
        
        #crear orden en estado pendiente
        
        orden = Orden.objects.create(
            usuario=request.user,
            total =total,
            estado = 'PENDIENTE'
        )
        for item in items: 
            print("🧾 ITEM:", item)
            OrdenItem.objects.create(
                orden=orden,
                tipo=item['tipo'],
                referencia_id=item['referencia_id'],
                titulo=item['title'],
                cantidad=item['quantity'],
                precio_unitario=Decimal(str(item['unit_price']))
                
            )
            
            #URLs y webhook
            
            base = "https://penny-tingliest-corelatively.ngrok-free.dev"  # tu URL Ngrok temporal
            back_urls = {
                'success': f"{base}/tienda/checkout/retorno/success/",
                'pending': f"{base}/tienda/checkout/retorno/pending/",
                'failure': f"{base}/tienda/checkout/retorno/failure/",
            }
            notification_url = f"{base}/tienda/webhooks/mercadopago/"
            
            #crear preferencia en MP
            
            preference_data={
                "items": [
                    {
                        "title": item['title'],
                        "quantity": item['quantity'],
                        "unit_price": float(item['unit_price']),
                    } for item in items
                ], 
                "payer": {
                    "email": request.user.email or "test_user@test.com",
                    "name": request.user.first_name or "Test",
                    "surname": request.user.last_name or "User",
                },
                "back_urls": back_urls,
                "notification_url": notification_url,
                "auto_return": "approved",
                "external_reference": str(orden.id),
            }
            
            sdk= _mp_client()
            pref= sdk.preference().create(preference_data)
            print("💬 Respuesta MP:", pref)  # 👈 Te muestra la respuesta completa

            
            if pref['status'] != 201:
                return JsonResponse({'error': 'Error al crear la preferencia de pago.'}, status=500)
            
            pref_id = pref['response']['id']
            init_point = pref['response']['init_point']
            orden.mp_preference_id=pref_id
            orden.save()

            return JsonResponse({ "preference_id": pref_id, "init_point": init_point })
    except Exception as e:
        print("❌ ERROR en crear_preferencia:", str(e))
        traceback.print_exc()  # 👈 Esto imprime TODO el error con línea exacta
        return JsonResponse({'error': str(e)}, status=500)

   
@login_required
def retorno_success(request):
    
    messages.success(request, "¡Pago realizado con éxito! 🎉 Gracias por tu compra.")
    return render(request, 'tienda/pago_exitoso.html')


@login_required
def retorno_pending(request):
   
    messages.warning(request, "Tu pago está pendiente. Te notificaremos cuando se confirme.")
    return render(request, 'tienda/pago_pendiente.html')


@login_required
def retorno_failure(request):
    messages.error(request, "El pago no pudo completarse o fue cancelado.")
    return render(request, 'tienda/pago_fallido.html')

@csrf_exempt
@require_POST
def webhook_mercadopago(request):
    """
    Mercado Pago envía notificaciones aquí.
    Debes leer el 'type' o 'topic' y el 'data.id' (payment id),
    luego consultar el pago con SDK y actualizar tu orden.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponse(status=400)

    # Formatos usuales: {"type":"payment","data":{"id":"123456"}}
    tipo = payload.get('type') or payload.get('topic')
    payment_id = None

    data = payload.get('data') or {}
    if isinstance(data, dict):
        payment_id = data.get('id')

    if tipo == 'payment' and payment_id:
        sdk = _mp_client()
        payment_info = sdk.payment().get(payment_id)
        if payment_info["status"] == 200:
            p = payment_info["response"]
            status = p.get("status")  # approved, pending, rejected...
            external_reference = p.get("external_reference")  # nuestra orden.id

            from .models import Orden
            try:
                orden = Orden.objects.get(id=external_reference)
            except Orden.DoesNotExist:
                return HttpResponse(status=404)

            if status == "approved":
                orden.estado = "aprobado"
                orden.mp_payment_id = str(payment_id)
                orden.pagado_en = timezone.now()
                orden.save()

                # Aquí puedes: descontar stock, “reservar cupos” en TallerEvento,
                # generar comprobante, limpiar carrito, enviar email, etc.

            elif status == "rejected":
                orden.estado = "rechazado"
                orden.mp_payment_id = str(payment_id)
                orden.save()

    return HttpResponse(status=200)

