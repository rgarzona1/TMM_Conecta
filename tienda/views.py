from datetime import date
from email.mime import base
import traceback
from django.db import transaction
from django.core.mail import send_mail
import django
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.views.decorators.http import require_POST
from django.urls import reverse
from flask import json, request

from usuarios.models import UsuarioPersonalizado
from .models import CuponAsignado, Producto, Carrito, CarritoItem, TallerEvento
from django.db.models import Count
from django.contrib.auth.decorators import login_required, user_passes_test
from Web.models import Taller
from .models import Producto, Cupon
from decimal import Decimal 

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

    cart = get_user_cart(request.user)
    subtotal = cart.get_total_bruto()
    descuento_aplicado = 0
    cupon_aplicado = None


    if request.method == "POST":
        accion = request.POST.get("accion")
        #APLICAR CUPÓN
        if accion == "aplicar":
            codigo = request.POST.get("codigo", "").strip()

            try:
                cupon = Cupon.objects.get(codigo=codigo)

              
                if not cupon.esta_vigente():
                    messages.error(request, "El cupón no está vigente.")
                    return redirect("carrito")

                if cupon.usuarios.exists() and request.user not in cupon.usuarios.all():
                    messages.error(request, "Este cupón no está asignado a tu usuario.")
                    return redirect("carrito")

                request.session["cupon_codigo"] = cupon.codigo
                messages.success(request, f"Cupón «{cupon.codigo}» aplicado correctamente.")
                return redirect("carrito")

            except Cupon.DoesNotExist:
                messages.error(request, "El cupón ingresado no es válido.")
                return redirect("carrito")

        #  QUITAR CUPÓN
        elif accion == "quitar":
            if "cupon_codigo" in request.session:
                del request.session["cupon_codigo"]
            messages.success(request, "Cupón eliminado del carrito.")
            return redirect("carrito")

    #  CALCULAR DESCUENTO SI HAY CUPÓN EN SESIÓN
    cupon_codigo = request.session.get("cupon_codigo")

    if cupon_codigo:
        cupon = Cupon.objects.filter(codigo=cupon_codigo).first()

        # Validar vigencia cada vez que se carga el carrito
        if cupon and cupon.esta_vigente():
            cupon_aplicado = cupon
            descuento_aplicado = (subtotal * (Decimal(cupon.porcentaje_descuento) / Decimal(100)))
            descuento_aplicado = int(descuento_aplicado)
        else:
            # Si expiró o fue borrado → eliminarlo
            if "cupon_codigo" in request.session:
                del request.session["cupon_codigo"]
            cupon_aplicado = None
            descuento_aplicado = 0

    #  TOTAL FINAL

    total_final = subtotal - descuento_aplicado

    # Detectar si el carrito tiene productos
    items = cart.items.all()
    tiene_productos = any(item.producto for item in items)
    solo_talleres = not tiene_productos   # Si NO hay productos → solo talleres

    # Dirección real del usuario desde BD
    usuario = request.user
    direccion = {
        "calle": usuario.direccion_calle,
        "numero": usuario.direccion_numero,
        "ciudad": usuario.direccion_ciudad,
        "zip": usuario.direccion_zip,
    }

    context = {
        'carrito': cart,
        'subtotal': subtotal,
        'total_final': total_final,
        'descuento': int(descuento_aplicado),
        'cupon': cupon_aplicado,
        'solo_talleres': solo_talleres,
        'direccion': direccion,
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
    elif action == 'delete':
        item.delete()
        messages.success(request, "Producto eliminado del carrito.")
            
    return redirect('carrito')

def catalogo_talleres_vista(request):
    """Listado de talleres futuros (filtrando por fecha_proxima >= hoy)"""
    hoy = date.today()  # fecha actual sin hora

    # Filtramos talleres cuya fecha sea hoy o futura
    talleres = (
        TallerEvento.objects
        .filter(fecha_proxima__gte=hoy)
        .order_by('fecha_proxima')
    )

    context = {'talleres': talleres}
    return render(request, 'tienda/catalogo_talleres.html', context)

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
        
        # después de obtener items y total:
        cupon_codigo = request.session.get('cupon_codigo')
        descuento = 0
        cupon_obj = None

        if cupon_codigo:
            cupon_obj = Cupon.objects.filter(codigo=cupon_codigo).first()
            if cupon_obj and cupon_obj.esta_vigente():
                descuento = total * (cupon_obj.porcentaje_descuento / 100)
                total = total - descuento
            else:
                # limpiar sesion si ya no es valido
                request.session.pop('cupon_codigo', None)

        
        #crear orden en estado pendiente
        
        orden = Orden.objects.create(
            usuario=request.user,
            total=total,
            estado='PENDIENTE',
            mp_preference_id='',
            cupon_codigo = cupon_obj.codigo if cupon_obj else None
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
                codigo = getattr(orden, 'cupon_codigo', None)
                if codigo:
                    cupon = Cupon.objects.filter(codigo=codigo).first()
                    if cupon:
                        # si cupon tiene usuarios asignados, marcar asignacion
                        asignacion = CuponAsignado.objects.filter(cupon=cupon, usuario=orden.usuario, usado=False).first()
                        if asignacion:
                            asignacion.marcar_usado()

            elif status == "rejected":
                orden.estado = "rechazado"
                orden.mp_payment_id = str(payment_id)
                orden.save()

    return HttpResponse(status=200)

# Verifica que el usuario sea la dueña.
def es_duena(user):
    return user.is_authenticated and user.email == "duena@tmmconecta.cl"


# Vista principal del panel
@login_required
# Vista principal del panel
@login_required
@user_passes_test(es_duena)
def panel_duena_inicio(request):
    from django.db.models import Count
    from django.db.models.functions import TruncMonth

    # 🔧 1️⃣ Si la URL contiene ?demo=1, se activa modo demo
    modo_demo = request.GET.get("demo") == "1"

    if modo_demo:
        # 🔧 2️⃣ Datos de prueba simulados
        labels_categorias = ["Resina", "Vinilo", "Soja", "Aromaterapia", "Kit"]
        data_categorias = [12, 9, 15, 7, 10]

        labels_tipo = ["Presencial", "Online"]
        data_tipo = [8, 5]

        labels_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo"]
        data_meses = [3, 4, 2, 6, 5]

        total_productos = sum(data_categorias)
        total_talleres = sum(data_meses)

    else:
        # 🔹 Datos reales desde la BD
        total_productos = Producto.objects.count()
        total_talleres = TallerEvento.objects.count()

        categoria_stats = (
            Producto.objects
            .values('categoria')
            .annotate(total=Count('id'))
            .order_by('categoria')
        )
        labels_categorias = [item['categoria'] or 'Sin categoría' for item in categoria_stats]
        data_categorias = [item['total'] for item in categoria_stats]

        tipo_stats = (
            TallerEvento.objects
            .values('tipo_taller')
            .annotate(total=Count('id'))
            .order_by('tipo_taller')
        )
        labels_tipo = [item['tipo_taller'] for item in tipo_stats]
        data_tipo = [item['total'] for item in tipo_stats]

        talleres_por_mes = (
            TallerEvento.objects
            .annotate(mes=TruncMonth('fecha_proxima'))
            .values('mes')
            .annotate(total=Count('id'))
            .order_by('mes')
        )
        labels_meses = [t['mes'].strftime("%b %Y") for t in talleres_por_mes]
        data_meses = [t['total'] for t in talleres_por_mes]

    context = {
        "total_productos": total_productos,
        "total_talleres": total_talleres,
        "labels_categorias": json.dumps(labels_categorias),
        "data_categorias": json.dumps(data_categorias),
        "labels_tipo": json.dumps(labels_tipo),
        "data_tipo": json.dumps(data_tipo),
        "labels_meses": json.dumps(labels_meses),
        "data_meses": json.dumps(data_meses),
        "modo_demo": modo_demo,  # 🔧 Lo mandamos al template
    }

    return render(request, "tienda/panel_inicio.html", context)


# ==================================================
# PANEL - CRUD UNIFICADO DE TALLERES
# ==================================================
@login_required
@user_passes_test(es_duena)
def panel_talleres(request):
    """Vista única para listar, crear, editar y eliminar TallerEvento"""
    from Web.models import Taller  # Import dentro para evitar conflictos circulares

    talleres = TallerEvento.objects.all().order_by('-fecha_proxima')
    talleres_base = Taller.objects.all()

    if request.method == 'POST':
        accion = request.POST.get('accion')
        id_taller = request.POST.get('id')
        imagen = request.FILES.get('imagen')


        # Datos del formulario
        taller_base_id = request.POST.get('taller_base')
        nuevo_taller_base = request.POST.get('nuevo_taller_base', '').strip()
        descripcion_completa = request.POST.get('descripcion_completa')
        precio = request.POST.get('precio')
        fecha_proxima = request.POST.get('fecha_proxima')
        hora_inicio = request.POST.get('hora_inicio')
        lugar = request.POST.get('lugar')
        profesor = request.POST.get('profesor')
        capacidad = request.POST.get('capacidad')
        tipo_taller = request.POST.get('tipo_taller')

        # Validación del taller base (crear uno nuevo si no existe)
        if nuevo_taller_base:
            taller_base = Taller.objects.create(titulo=nuevo_taller_base)
        elif taller_base_id:
            taller_base = get_object_or_404(Taller, id=taller_base_id)
        else:
            messages.error(request, "⚠️ Debes seleccionar o ingresar un Taller Base.")
            return redirect('panel_talleres')

        # CREAR TALLER
        if accion == 'crear':
            TallerEvento.objects.create(
                taller_base=taller_base,
                descripcion_completa=descripcion_completa,
                precio=precio,
                fecha_proxima=fecha_proxima,
                hora_inicio=hora_inicio,
                lugar=lugar,
                profesor=profesor,
                capacidad=capacidad,
                tipo_taller=tipo_taller,
                imagen=imagen
            )
            messages.success(request, "✅ Taller creado con éxito.")

        # EDITAR TALLER
        elif accion == 'editar' and id_taller:
            taller = get_object_or_404(TallerEvento, id=id_taller)
            taller.taller_base = taller_base
            taller.descripcion_completa = descripcion_completa
            taller.precio = precio
            taller.fecha_proxima = fecha_proxima
            taller.hora_inicio = hora_inicio
            taller.lugar = lugar
            taller.profesor = profesor
            taller.capacidad = capacidad
            taller.tipo_taller = tipo_taller
            if imagen:  
                taller.imagen = imagen
            taller.save()
            messages.success(request, "📝 Taller actualizado correctamente.")

        return redirect('panel_talleres')

    # ELIMINAR TALLER
    if request.method == 'GET' and 'eliminar' in request.GET:
        id_taller = request.GET.get('eliminar')
        taller = get_object_or_404(TallerEvento, id=id_taller)
        taller.delete()
        messages.success(request, "🗑️ Taller eliminado correctamente.")
        return redirect('panel_talleres')

    return render(request, 'tienda/panel_talleres.html', {
        'talleres': talleres,
        'talleres_base': talleres_base
    })

@login_required
@user_passes_test(es_duena)
def panel_ventas(request):
    """Panel administrativo para ver las órdenes y estadísticas de ventas"""
    from django.db.models.functions import TruncMonth

    # Todas las órdenes
    ordenes = Orden.objects.all().order_by('-creado_en')

    # Resumen de totales
    total_ventas = Orden.objects.filter(estado__iexact='aprobado').aggregate(Sum('total'))['total__sum'] or 0
    total_pendientes = Orden.objects.filter(estado__iexact='pendiente').count()
    total_aprobadas = Orden.objects.filter(estado__iexact='aprobado').count()

    # Ventas por mes (para gráfico)
    ventas_por_mes = (
        Orden.objects.filter(estado__iexact='aprobado')
        .annotate(mes=TruncMonth('pagado_en'))
        .values('mes')
        .annotate(total=Sum('total'))
        .order_by('mes')
    )

    labels_meses = [v['mes'].strftime("%b %Y") for v in ventas_por_mes if v['mes']]
    data_meses = [float(v['total']) for v in ventas_por_mes if v['total']]

    context = {
        'ordenes': ordenes,
        'total_ventas': total_ventas,
        'total_pendientes': total_pendientes,
        'total_aprobadas': total_aprobadas,
        'labels_meses': json.dumps(labels_meses),
        'data_meses': json.dumps(data_meses),
    }

    return render(request, 'tienda/panel_ventas.html', context)

@login_required
@user_passes_test(es_duena)
def panel_ventas_detalle(request, orden_id):
    """Detalle de una orden específica"""
    orden = get_object_or_404(Orden, id=orden_id)
    items = orden.items.all()

    context = {
        'orden': orden,
        'items': items,
    }
    return render(request, 'tienda/panel_ventas_detalle.html', context)

from django.contrib.auth import get_user_model
User = get_user_model()

@login_required
@user_passes_test(es_duena)
def panel_usuarios(request):
    """Panel para administrar y revisar usuarios registrados"""
    from usuarios.models import TallerAsistido  # Si existe este modelo

    usuarios = User.objects.all().order_by('-date_joined')

    usuarios_info = []
    for u in usuarios:
        total_ordenes = Orden.objects.filter(usuario=u).count()
        talleres_asistidos = (
            TallerAsistido.objects.filter(usuario=u).count()
            if hasattr(u, 'tallerasistido_set') or 'TallerAsistido' in globals()
            else 0
        )
        usuarios_info.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'fecha_registro': u.date_joined,
            'ultimo_login': u.last_login,
            'total_ordenes': total_ordenes,
            'talleres_asistidos': talleres_asistidos,
            'es_duena': es_duena(u),
        })

    context = {
        'usuarios_info': usuarios_info,
    }

    return render(request, 'tienda/panel_usuarios.html', context)

@login_required
@transaction.atomic
def simular_compra(request):
    """Simular una compra local: crear orden, resta cupos, y envía correos."""
    usuario = request.user
    carrito = get_object_or_404(Carrito, usuario=usuario)

    if not carrito.items.exists():
        return JsonResponse({'message': 'Tu carrito está vacío.'}, status=400)

    # Crear orden
    orden = Orden.objects.create(
        usuario=usuario,
        total=carrito.get_total_bruto(),
        estado='APROBADO',  #  pago exitoso
        pagado_en=timezone.now()
    )

    resumen = []
    for item in carrito.items.all():
        titulo = ""
        cantidad = item.cantidad
        precio = 0

        if item.producto:
            titulo = item.producto.nombre
            precio = item.producto.precio

        elif hasattr(item, 'taller_evento') and item.taller_evento:
            titulo = f"Taller: {item.taller_evento.taller_base.titulo} ({item.taller_evento.fecha_proxima})"
            precio = item.taller_evento.precio

            # Descontar cupos
            if item.taller_evento.capacidad > 0:
                item.taller_evento.capacidad -= 1
                item.taller_evento.save()

        OrdenItem.objects.create(
            orden=orden,
            tipo='TALLER' if hasattr(item, 'taller_evento') and item.taller_evento else 'PRODUCTO',
            referencia_id=item.id,
            titulo=titulo,
            precio_unitario=precio,
        )

        resumen.append(f"- {titulo} x{cantidad} — ${precio * cantidad}")

    # Limpiar carrito
    carrito.items.all().delete()

    # ----------- EMAILS -------------
    total = f"${orden.total:,.0f}"
    detalles_compra = "\n".join(resumen)
    numero_orden = f"TMM-{orden.id:04d}"

    # Email al comprador
    mensaje_usuario = f"""
¡Gracias por tu compra, {usuario.first_name or usuario.username}! 🧾

Tu número de orden es: {numero_orden}
Detalles de tu compra:
{detalles_compra}

Total: {total}

Te has inscrito exitosamente a tus talleres seleccionados 
Nos vemos pronto en Talleres TMM 💕
"""
    send_mail(
        subject=f"Confirmación de compra - {numero_orden}",
        message=mensaje_usuario,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        fail_silently=True,
    )

    # Email a la dueña
    mensaje_duena = f"""
 NUEVA COMPRA RECIBIDA 

Orden: {numero_orden}
Cliente: {usuario.username} ({usuario.email})
Total: {total}

Detalles:
{detalles_compra}

Revisa los cupos actualizados en el panel de administración.
"""
    send_mail(
        subject=f"🛒 Nueva compra - {numero_orden}",
        message=mensaje_duena,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=["rod2480yt@gmail.com"],
        fail_silently=True,
    )

    return JsonResponse({
        'message': f"Compra simulada con éxito 🎉 Orden {numero_orden} generada.",
        'redirect': reverse('carrito')
    })


@login_required
def guardar_direccion(request):
    if request.method == "POST":
        u = request.user
        u.direccion_calle = request.POST.get("calle")
        u.direccion_numero = request.POST.get("numero")
        u.direccion_ciudad = request.POST.get("ciudad")
        u.direccion_zip = request.POST.get("zip")
        u.save()
        messages.success(request, "Dirección actualizada correctamente.")
    return redirect("carrito")

@login_required
def panel_insumos(request):
    """Vista para gestionar los insumos/productos"""
    
    # CREAR O EDITAR INSUMO
    if request.method == 'POST':
        insumo_id = request.POST.get('id')
        accion = request.POST.get('accion')
        
        # Recoger datos del formulario
        nombre = request.POST.get('nombre')
        categoria = request.POST.get('categoria')
        precio = request.POST.get('precio')
        descripcion_corta = request.POST.get('descripcion_corta')
        imagen = request.FILES.get('imagen')
        
        if accion == 'editar' and insumo_id:
            # EDITAR insumo existente
            try:
                insumo = Producto.objects.get(id=insumo_id)
                insumo.nombre = nombre
                insumo.categoria = categoria
                insumo.precio = precio
                insumo.descripcion_corta = descripcion_corta
                
                if imagen:
                    insumo.imagen = imagen
                
                insumo.save()
                messages.success(request, f'✅ Insumo "{nombre}" actualizado correctamente.')
            except Producto.DoesNotExist:
                messages.error(request, '❌ El insumo no existe.')
        else:
            # CREAR nuevo insumo
            nuevo_insumo = Producto(
                nombre=nombre,
                categoria=categoria,
                precio=precio,
                descripcion_corta=descripcion_corta
            )
            
            if imagen:
                nuevo_insumo.imagen = imagen
            
            nuevo_insumo.save()
            messages.success(request, f'✅ Insumo "{nombre}" creado correctamente.')
        
        return redirect('panel_insumos')
    
    # ELIMINAR INSUMO
    if request.GET.get('eliminar'):
        try:
            insumo_id = request.GET.get('eliminar')
            insumo = Producto.objects.get(id=insumo_id)
            nombre = insumo.nombre
            insumo.delete()
            messages.success(request, f'🗑️ Insumo "{nombre}" eliminado.')
        except Producto.DoesNotExist:
            messages.error(request, '❌ El insumo no existe.')
        return redirect('panel_insumos')
    
    insumos = Producto.objects.all().order_by('categoria', 'nombre')
    
    context = {
        'insumos': insumos,
        'categorias': Producto.CATEGORIA_CHOICES,
    }
    
    return render(request, 'tienda/panel_insumos.html', context)


@login_required
@user_passes_test(es_duena)
def panel_cupones(request):
    """CRUD de cupones para la dueña (listar, crear, eliminar, asignar)."""
    cupones = Cupon.objects.all().order_by('-creado_en')
    usuarios = UsuarioPersonalizado.objects.all().order_by('-date_joined')

    if request.method == "POST":
        accion = request.POST.get('accion')
        if accion == 'crear':
            codigo = request.POST.get('codigo').strip().upper()
            descripcion = request.POST.get('descripcion', '').strip()
            porcentaje = int(request.POST.get('porcentaje') or 0)
            inicio = request.POST.get('fecha_inicio') or None
            fin = request.POST.get('fecha_expiracion') or None
            uso_unico = request.POST.get('uso_unico') == 'on'
            aplica = request.POST.get('aplica') or 'ALL'

            if not codigo or porcentaje <= 0:
                messages.error(request, "Código y porcentaje válidos son requeridos.")
                return redirect('panel_cupones')

            cupon = Cupon.objects.create(
                codigo=codigo,
                descripcion=descripcion,
                porcentaje_descuento=porcentaje,
                fecha_inicio=inicio,
                fecha_expiracion=fin,
                uso_unico=uso_unico,
                aplica=aplica,
                activo=True
            )
            messages.success(request, f"Cupón {cupon.codigo} creado.")
            return redirect('panel_cupones')

        elif accion == 'eliminar':
            id_c = request.POST.get('id')
            Cupon.objects.filter(id=id_c).delete()
            messages.success(request, "Cupón eliminado.")
            return redirect('panel_cupones')

        elif accion == 'asignar':
            id_c = request.POST.get('id_cupon')
            user_id = request.POST.get('user_id')
            cupon = get_object_or_404(Cupon, id=id_c)
            user = get_object_or_404(UsuarioPersonalizado, id=user_id)
            cupon.usuarios.add(user)
            # crear registro en CuponAsignado si no existe
            CuponAsignado.objects.get_or_create(cupon=cupon, usuario=user)
            messages.success(request, f"Cupón {cupon.codigo} asignado a {user.username}.")
            return redirect('panel_cupones')

    return render(request, 'tienda/panel_cupones.html', {
        'cupones': cupones,
        'usuarios': usuarios,
    })

@login_required
def quitar_cupon(request):
    """Elimina el cupón activo desde la sesión del usuario."""
    if "cupon_codigo" in request.session:
        del request.session["cupon_codigo"]

    messages.success(request, "Cupón eliminado del carrito.")
    return redirect("carrito")
