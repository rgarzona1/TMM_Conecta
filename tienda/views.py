from datetime import datetime, date
from email.mime import base
import traceback
from django.db import transaction
from django.core.mail import send_mail
import django
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from decimal import Decimal
from django.conf import settings
import json

# IMPORTACIONES PROPIAS
from usuarios.models import UsuarioPersonalizado, TallerAsistido
from Web.models import Taller
from .models import (
    CuponAsignado, Producto, Carrito, CarritoItem, 
    TallerEvento, Orden, OrdenItem, Cupon
)
from .utils import obtener_items_de_carrito 

# IMPORTACIONES MERCADOPAGO
import mercadopago

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


from datetime import date
from django.shortcuts import render, get_object_or_404

# ========================================================
#  CATEGORÍA (TIENDA GENERAL)
# ========================================================
def categoria_vista(request, categoria_slug):
    """
    Muestra productos filtrados por categoría.
    """
    categoria_key = categoria_slug.upper().replace('-', '_')
    productos = Producto.objects.filter(categoria=categoria_key)

    context = {
        'productos': productos,
        'nombre_categoria': categoria_slug.capitalize(),  # Título en el template
    }
    return render(request, 'tienda/tienda_categoria.html', context)


# ========================================================
#  CATÁLOGO DE TALLERES (SOLO EL MÁS PRÓXIMO)
# ========================================================
def catalogo_talleres_vista(request):
    """
    Muestra solo una tarjeta por taller con su fecha más próxima.
    """
    hoy = date.today()
    talleres_base = Taller.objects.all()
    talleres_para_mostrar = []

    for base in talleres_base:
        # Fecha más cercana hacia el futuro
        proximo_evento = base.eventos.filter(fecha_proxima__gte=hoy).order_by('fecha_proxima').first()
        if proximo_evento:
            talleres_para_mostrar.append(proximo_evento)

    context = {'talleres': talleres_para_mostrar}
    return render(request, 'tienda/catalogo_talleres.html', context)


# ========================================================
#  DETALLE DEL TALLER (CON OTRAS FECHAS DISPONIBLES)
# ========================================================
def detalle_taller_vista(request, taller_id):
    """
    Muestra el detalle de una fecha específica y otras fechas
    futuras del mismo taller.
    """
    hoy = date.today()
    taller_seleccionado = get_object_or_404(TallerEvento, pk=taller_id)

    otras_fechas = TallerEvento.objects.filter(
        taller_base=taller_seleccionado.taller_base,
        fecha_proxima__gte=hoy
    ).exclude(id=taller_seleccionado.id).order_by('fecha_proxima')

    context = {
        'taller': taller_seleccionado,
        'otras_fechas': otras_fechas,
    }
    return render(request, 'tienda/detalle_taller.html', context)

# ========================================================
#  VISTA DE CARRITO (VISUALIZACIÓN)
# ========================================================
@login_required
def carrito_vista(request):
    cart = get_user_cart(request.user)
    subtotal = cart.get_total_bruto()
    descuento_aplicado = 0
    cupon_aplicado = None

    if request.method == "POST":
        accion = request.POST.get("accion")
        # APLICAR CUPÓN
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

        # QUITAR CUPÓN
        elif accion == "quitar":
            if "cupon_codigo" in request.session:
                del request.session["cupon_codigo"]
            messages.success(request, "Cupón eliminado del carrito.")
            return redirect("carrito")

    # CALCULAR DESCUENTO SI HAY CUPÓN EN SESIÓN
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

    # TOTAL FINAL
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


# ========================================================
#  AGREGAR AL CARRITO (Lógica de Regalos y Cupos)
# ========================================================
@login_required
def add_to_cart(request, producto_id=None, taller_id=None):
    carrito = get_user_cart(request.user)

    # --- CASO 1: AGREGAR PRODUCTO ---
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

    # --- CASO 2: AGREGAR TALLER (Con lógica de regalo) ---
    elif taller_id:
        taller_evento = get_object_or_404(TallerEvento, pk=taller_id)
        
        # 1. Obtener datos del formulario (si es regalo)
        es_regalo = request.POST.get('es_regalo') == 'on'
        nombre_beneficiario = request.POST.get('nombre_beneficiario', '').strip()
        email_beneficiario = request.POST.get('email_beneficiario', '').strip()

        # 2. Calcular cupos disponibles reales
        # Cupos reales = Capacidad Total - (Items en mi carrito)
        
        items_en_mi_carrito = CarritoItem.objects.filter(carrito=carrito, taller_evento=taller_evento).count()
        cupos_restantes_usuario = taller_evento.capacidad - items_en_mi_carrito

        if cupos_restantes_usuario <= 0:
            messages.error(request, "No quedan suficientes cupos disponibles para agregar otro.")
            return redirect('detalle_taller', taller_id=taller_id)

        # 3. Lógica para REGALO (Múltiples beneficiarios)
        if es_regalo:
            # Recibimos listas de nombres y correos
            nombres = request.POST.getlist('nombre_beneficiario')
            emails = request.POST.getlist('email_beneficiario')
            
            cantidad_solicitada = len(nombres)

            # Validaciones básicas
            if cantidad_solicitada == 0:
                messages.error(request, "Debes agregar al menos un beneficiario.")
                return redirect('detalle_taller', taller_id=taller_id)
            
            if any(not n.strip() for n in nombres) or any(not e.strip() for e in emails):
                messages.error(request, "Todos los campos de nombre y correo son obligatorios.")
                return redirect('detalle_taller', taller_id=taller_id)

            # Verificar stock para la cantidad total solicitada
            if cupos_restantes_usuario < cantidad_solicitada:
                 messages.error(request, f"No alcanzan los cupos. Solo quedan {cupos_restantes_usuario} disponibles.")
                 return redirect('detalle_taller', taller_id=taller_id)

            # Crear un ítem por cada beneficiario
            creados = 0
            for nombre, email in zip(nombres, emails):
                CarritoItem.objects.create(
                    carrito=carrito,
                    taller_evento=taller_evento,
                    cantidad=1, # Siempre es 1 por beneficiario específico
                    es_regalo=True,
                    nombre_beneficiario=nombre,
                    email_beneficiario=email
                )
                creados += 1
            
            messages.success(request, f"¡Listo! Se agregaron {creados} cupos de regalo al carrito.")

        # 4. Lógica para COMPRA PERSONAL
        else:
            # Validar si ya está inscrito en el pasado (Asistido o Por realizar)
            ya_inscrito = TallerAsistido.objects.filter(
                usuario=request.user, 
                nombre_taller=taller_evento.taller_base.titulo, # Idealmente usar ID de evento si el modelo lo permite
                estado__in=['ASISTIDO', 'POR_REALIZAR']
            ).exists()
            
            # Validar si ya tiene un ítem personal en el carrito
            ya_en_carrito = CarritoItem.objects.filter(
                carrito=carrito, 
                taller_evento=taller_evento, 
                es_regalo=False
            ).exists()

            if ya_inscrito:
                messages.info(request, f"Ya estás inscrito en {taller_evento.taller_base.titulo}.")
            elif ya_en_carrito:
                messages.info(request, "Ya tienes tu cupo personal en el carrito. ¿Quizás querías comprar un regalo?")
            else:
                CarritoItem.objects.create(
                    carrito=carrito,
                    taller_evento=taller_evento,
                    cantidad=1,
                    es_regalo=False
                )
                messages.success(request, f"Tu cupo para {taller_evento.taller_base.titulo} agregado al carrito.")

    else:
        messages.error(request, "No se pudo agregar al carrito.")

    return redirect('carrito')


# ========================================================
#  ACTUALIZAR CARRITO (Eliminar taller habilitado)
# ========================================================
@login_required
def update_cart(request, item_id, action):
    item = get_object_or_404(CarritoItem, id=item_id, carrito__usuario=request.user)
    
    # 1. Si es TALLER: Solo permitimos eliminar, no cambiar cantidad (add)
    if item.taller_evento:
        if action == 'delete' or action == 'remove':
            item.delete()
            messages.success(request, "Cupo de taller eliminado del carrito.")
        elif action == 'add':
            messages.info(request, "Para agregar más cupos de taller, vuelve al catálogo y selecciona si es regalo.")
        return redirect('carrito')

    # 2. Si es PRODUCTO: Lógica normal
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


# ========================================================
#  SIMULAR COMPRA (Envío de Invitaciones)
# ========================================================
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
        estado='APROBADO',  # pago exitoso
        pagado_en=timezone.now()
    )

    resumen = []
    
    for item in carrito.items.all():
        titulo = ""
        precio = 0
        
        # --- PROCESAR PRODUCTO ---
        if item.producto:
            titulo = item.producto.nombre
            precio = item.producto.precio
            OrdenItem.objects.create(
                orden=orden,
                tipo='PRODUCTO',
                referencia_id=item.producto.id,
                titulo=titulo,
                cantidad=item.cantidad,
                precio_unitario=precio
            )
            resumen.append(f"- {titulo} x{item.cantidad}")

        # --- PROCESAR TALLER ---
        elif item.taller_evento:
            titulo_base = item.taller_evento.taller_base.titulo
            precio = item.taller_evento.precio
            
            # Descontar cupo GLOBAL
            if item.taller_evento.capacidad > 0:
                item.taller_evento.capacidad -= 1
                item.taller_evento.save()

            # Guardar ítem en la orden con datos de regalo
            OrdenItem.objects.create(
                orden=orden,
                tipo='TALLER',
                referencia_id=item.taller_evento.id,
                titulo=f"Taller: {titulo_base}",
                cantidad=1,
                precio_unitario=precio,
                es_regalo=item.es_regalo,
                nombre_beneficiario=item.nombre_beneficiario,
                email_beneficiario=item.email_beneficiario
            )

            # LÓGICA DIFERENCIADA: REGALO vs PERSONAL
            if item.es_regalo:
                # ENVIAR INVITACIÓN AL AMIGO
                titulo = f"REGALO: Taller {titulo_base} (Para: {item.nombre_beneficiario})"
                
                msj_invitacion = f"""
                ¡Hola {item.nombre_beneficiario}! 🎁
                
                {usuario.first_name or usuario.username} te ha regalado un cupo para el taller:
                "{titulo_base}"
                
                Fecha: {item.taller_evento.fecha_proxima}
                Hora: {item.taller_evento.hora_inicio}
                Lugar: {item.taller_evento.lugar}
                
                IMPORTANTE:
                Para confirmar tu asistencia y recibir los materiales, por favor regístrate en nuestra web:
                https://tmmconecta.cl/registro
                
                ¡Te esperamos!
                """
                send_mail(
                    subject=f"¡Te regalaron un Taller en TMM! 🎁",
                    message=msj_invitacion,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[item.email_beneficiario],
                    fail_silently=True
                )
            else:
                # INSCRIPCIÓN PERSONAL
                titulo = f"Taller: {titulo_base}"
                # Crear registro de asistencia para el usuario logueado
                TallerAsistido.objects.create(
                    usuario=usuario,
                    nombre_taller=titulo_base,
                    fecha=item.taller_evento.fecha_proxima,
                    lugar=item.taller_evento.lugar,
                    estado='POR_REALIZAR'
                )

            resumen.append(f"- {titulo} - ${precio:,.0f}")

    # Limpiar carrito
    carrito.items.all().delete()

    # Emails de confirmación al comprador
    total_str = f"${orden.total:,.0f}"
    detalles_compra = "\n".join(resumen)
    numero_orden = f"TMM-{orden.id:04d}"

    mensaje_usuario = f"""
    ¡Gracias por tu compra, {usuario.first_name or usuario.username}! 🧾
    
    Tu número de orden es: {numero_orden}
    Detalles de tu compra:
    {detalles_compra}

    Total: {total_str}
    
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
    Total: {total_str}

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


# ========================================================
# VISTAS MERCADO PAGO
# ========================================================
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
            return redirect('login')
        
        # 1. Obtenemos el carrito y items DIRECTAMENTE del modelo para no perder datos (regalos)
        carrito = get_user_cart(request.user)
        items = carrito.items.all()
        
        if not items.exists():
            return JsonResponse({'error': 'El carrito está vacío.'}, status=400)
        
        # Calcular total y aplicar cupón si existe
        total = carrito.get_total_bruto()
        
        cupon_codigo = request.session.get('cupon_codigo')
        cupon_obj = None

        if cupon_codigo:
            cupon_obj = Cupon.objects.filter(codigo=cupon_codigo).first()
            if cupon_obj and cupon_obj.esta_vigente():
                descuento = total * (cupon_obj.porcentaje_descuento / 100)
                total = total - descuento
            else:
                request.session.pop('cupon_codigo', None)

        
        # 2. Crear Orden PENDIENTE
        orden = Orden.objects.create(
            usuario=request.user,
            total=total,
            estado='PENDIENTE',
            mp_preference_id='',
            cupon_codigo = cupon_obj.codigo if cupon_obj else None
        )

        mp_items = []

        # 3. Crear OrdenItems copiando los datos del CarritoItem (incluyendo regalos)
        for item in items:
            titulo = ""
            precio_unit = 0
            
            if item.producto:
                titulo = item.producto.nombre
                precio_unit = item.producto.precio
                tipo = 'PRODUCTO'
                ref_id = item.producto.id
            elif item.taller_evento:
                titulo = item.taller_evento.taller_base.titulo
                precio_unit = item.taller_evento.precio
                tipo = 'TALLER'
                ref_id = item.taller_evento.id
            
            OrdenItem.objects.create(
                orden=orden,
                tipo=tipo,
                referencia_id=ref_id,
                titulo=titulo,
                cantidad=item.cantidad,
                precio_unitario=precio_unit,
                # Copiamos datos de regalo
                es_regalo=item.es_regalo,
                nombre_beneficiario=item.nombre_beneficiario,
                email_beneficiario=item.email_beneficiario
            )
            
            # Preparar ítem para MercadoPago
            mp_items.append({
                "title": titulo,
                "quantity": item.cantidad,
                "unit_price": float(precio_unit),
            })
            
        # 4. URLs y webhook
        base = "https://penny-tingliest-corelatively.ngrok-free.dev"  # URL Ngrok
        back_urls = {
            'success': f"{base}/tienda/checkout/retorno/success/",
            'pending': f"{base}/tienda/checkout/retorno/pending/",
            'failure': f"{base}/tienda/checkout/retorno/failure/",
        }
        notification_url = f"{base}/tienda/webhooks/mercadopago/"
        
        # 5. Crear preferencia en MP
        preference_data={
            "items": mp_items, 
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

        if pref['status'] != 201:
            return JsonResponse({'error': 'Error al crear la preferencia de pago.'}, status=500)
        
        pref_id = pref['response']['id']
        init_point = pref['response']['init_point']
        orden.mp_preference_id=pref_id
        orden.save()

        return JsonResponse({ "preference_id": pref_id, "init_point": init_point })

    except Exception as e:
        print("❌ ERROR en crear_preferencia:", str(e))
        traceback.print_exc()
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
    Si el pago se aprueba, debemos activar la lógica de inscripción/regalo (Similar a simular_compra).
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponse(status=400)

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
            status = p.get("status")
            external_reference = p.get("external_reference")

            from .models import Orden
            try:
                orden = Orden.objects.get(id=external_reference)
            except Orden.DoesNotExist:
                return HttpResponse(status=404)

            if status == "approved" and orden.estado != "aprobado":
                # 1. Actualizar Orden
                orden.estado = "aprobado"
                orden.mp_payment_id = str(payment_id)
                orden.pagado_en = timezone.now()
                orden.save()
                
                # 2. Lógica de Negocio (Inscripciones y Regalos)
                items = orden.items.all()
                for item in items:
                    if item.tipo == 'TALLER':
                        # Descontar Cupos
                        try:
                            evento = TallerEvento.objects.get(id=item.referencia_id)
                            if evento.capacidad > 0:
                                evento.capacidad -= 1
                                evento.save()
                                
                            # Si es Regalo -> Email Invitación
                            if item.es_regalo:
                                msj = f"Hola {item.nombre_beneficiario}, {orden.usuario.first_name} te regaló un taller..."
                                send_mail(
                                    "¡Regalo TMM!", msj, settings.DEFAULT_FROM_EMAIL, [item.email_beneficiario], fail_silently=True
                                )
                            else:
                                # Inscripción Personal
                                TallerAsistido.objects.create(
                                    usuario=orden.usuario,
                                    nombre_taller=item.titulo,
                                    fecha=evento.fecha_proxima,
                                    lugar=evento.lugar,
                                    estado='POR_REALIZAR'
                                )
                        except TallerEvento.DoesNotExist:
                            pass

                # 3. Marcar Cupón
                codigo = getattr(orden, 'cupon_codigo', None)
                if codigo:
                    cupon = Cupon.objects.filter(codigo=codigo).first()
                    if cupon:
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
@user_passes_test(es_duena)
def panel_duena_inicio(request):
    from django.db.models import Count
    from django.db.models.functions import TruncMonth

    modo_demo = request.GET.get("demo") == "1"

    if modo_demo:
        labels_categorias = ["Resina", "Vinilo", "Soja", "Aromaterapia", "Kit"]
        data_categorias = [12, 9, 15, 7, 10]
        labels_tipo = ["Presencial", "Online"]
        data_tipo = [8, 5]
        labels_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo"]
        data_meses = [3, 4, 2, 6, 5]
        total_productos = sum(data_categorias)
        total_talleres = sum(data_meses)
    else:
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
        "modo_demo": modo_demo,
    }

    return render(request, "tienda/panel_inicio.html", context)


# ==================================================
# PANEL - CRUD UNIFICADO DE TALLERES
# ==================================================
@login_required
@user_passes_test(es_duena)
def panel_talleres(request):
    """Vista única para listar, crear, editar y eliminar TallerEvento"""
    from tienda.models import TallerEvento
    from Web.models import Taller

    talleres = TallerEvento.objects.all().order_by('-fecha_proxima')
    talleres_base = Taller.objects.all()

    # ELIMINAR TALLER (GET)
    if request.method == 'GET' and 'eliminar' in request.GET:
        id_taller = request.GET.get('eliminar')
        taller = get_object_or_404(TallerEvento, id=id_taller)
        taller.delete()
        messages.success(request, "🗑️ Taller eliminado correctamente.")
        return redirect('panel_talleres')

    # CREAR O EDITAR TALLER (POST)
    if request.method == 'POST':
        try:
            accion = request.POST.get('accion')
            id_taller = request.POST.get('id')
            
            # Obtener datos del formulario
            taller_base_id = request.POST.get('taller_base')
            nuevo_taller_base = request.POST.get('nuevo_taller_base', '').strip()
            descripcion_completa = request.POST.get('descripcion_completa', '').strip()
            precio = request.POST.get('precio')
            fechas_proximas = request.POST.getlist('fecha_proxima')
            horas_inicio = request.POST.getlist('hora_inicio')
            lugar = request.POST.get('lugar', '').strip()
            profesor = request.POST.get('profesor', '').strip()
            capacidad = request.POST.get('capacidad')
            tipo_taller = request.POST.get('tipo_taller')
            imagen = request.FILES.get('imagen')

            # VALIDACIONES BÁSICAS
            if not taller_base_id and not nuevo_taller_base:
                messages.error(request, '⚠️ Debes seleccionar un taller existente o crear uno nuevo.')
                return redirect('panel_talleres')
            
            if not descripcion_completa or len(descripcion_completa) < 10:
                messages.error(request, '⚠️ La descripción debe tener al menos 10 caracteres.')
                return redirect('panel_talleres')

            # Determinar el taller base
            if nuevo_taller_base:
                taller_base, created = Taller.objects.get_or_create(
                    titulo=nuevo_taller_base,
                    defaults={'descripcion': descripcion_completa[:100]}
                )
                if created:
                    messages.info(request, f'📝 Nuevo taller base "{nuevo_taller_base}" creado.')
            elif taller_base_id:
                taller_base = get_object_or_404(Taller, id=taller_base_id)
            else:
                messages.error(request, "⚠️ Error al determinar el taller base.")
                return redirect('panel_talleres')

            # VALIDACIÓN: Precio y capacidad
            try:
                precio_decimal = float(precio)
                if precio_decimal < 0:
                    messages.error(request, '⚠️ El precio no puede ser negativo.')
                    return redirect('panel_talleres')
            except (ValueError, TypeError):
                messages.error(request, '⚠️ Precio inválido.')
                return redirect('panel_talleres')
            
            try:
                capacidad_int = int(capacidad)
                if capacidad_int < 1:
                    messages.error(request, '⚠️ La capacidad debe ser al menos 1 persona.')
                    return redirect('panel_talleres')
            except (ValueError, TypeError):
                messages.error(request, '⚠️ Capacidad inválida.')
                return redirect('panel_talleres')

            # CREAR NUEVOS TALLERES (MÚLTIPLES FECHAS)
            if accion == 'crear':
                talleres_creados = 0
                
                if not fechas_proximas or not any(fechas_proximas):
                    messages.error(request, '⚠️ Debe agregar al menos una fecha para el taller.')
                    return redirect('panel_talleres')
                
                for i, (fecha_str, hora_str) in enumerate(zip(fechas_proximas, horas_inicio)):
                    if fecha_str and hora_str:
                        try:
                            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                            if fecha_obj < date.today():
                                messages.warning(request, f'⚠️ Se omitió la fecha {fecha_str} porque es pasada.')
                                continue
                            
                            taller_evento = TallerEvento.objects.create(
                                taller_base=taller_base,
                                descripcion_completa=descripcion_completa,
                                precio=precio_decimal,
                                fecha_proxima=fecha_obj,
                                hora_inicio=hora_str,
                                lugar=lugar,
                                profesor=profesor,
                                capacidad=capacidad_int,
                                tipo_taller=tipo_taller
                            )
                            
                            if imagen and i == 0:
                                taller_evento.imagen = imagen
                                taller_evento.save()
                            
                            talleres_creados += 1
                            
                        except Exception as e:
                            error_msg = f'❌ Error al crear taller para fecha {fecha_str}: {str(e)}'
                            messages.error(request, error_msg)
                
                if talleres_creados > 0:
                    messages.success(request, f"✅ {talleres_creados} taller(es) creado(s) con éxito.")
                else:
                    messages.error(request, "❌ No se pudo crear ningún taller.")

            # EDITAR TALLER EXISTENTE - CORREGIDO: Ahora también puede agregar nuevas fechas
            elif accion == 'editar' and id_taller:
                # 1. Primero actualizamos el taller existente
                taller_original = get_object_or_404(TallerEvento, id=id_taller)
                taller_original.taller_base = taller_base
                taller_original.descripcion_completa = descripcion_completa
                taller_original.precio = precio_decimal
                taller_original.lugar = lugar
                taller_original.profesor = profesor
                taller_original.capacidad = capacidad_int
                taller_original.tipo_taller = tipo_taller
                
                # Actualizar fecha y hora del taller original (solo la primera)
                if fechas_proximas and fechas_proximas[0]:
                    fecha_obj = datetime.strptime(fechas_proximas[0], '%Y-%m-%d').date()
                    taller_original.fecha_proxima = fecha_obj
                
                if horas_inicio and horas_inicio[0]:
                    taller_original.hora_inicio = horas_inicio[0]
                
                if imagen:  
                    taller_original.imagen = imagen
                
                taller_original.save()
                
                # 2. Crear NUEVOS talleres para las fechas adicionales (si las hay)
                talleres_nuevos_creados = 0
                if len(fechas_proximas) > 1:
                    for i in range(1, len(fechas_proximas)):
                        fecha_str = fechas_proximas[i]
                        hora_str = horas_inicio[i] if i < len(horas_inicio) else horas_inicio[0]
                        
                        if fecha_str and hora_str:
                            try:
                                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                                if fecha_obj < date.today():
                                    continue
                                
                                # Crear nuevo TallerEvento con los mismos datos
                                nuevo_taller = TallerEvento.objects.create(
                                    taller_base=taller_base,
                                    descripcion_completa=descripcion_completa,
                                    precio=precio_decimal,
                                    fecha_proxima=fecha_obj,
                                    hora_inicio=hora_str,
                                    lugar=lugar,
                                    profesor=profesor,
                                    capacidad=capacidad_int,
                                    tipo_taller=tipo_taller,
                                    imagen=taller_original.imagen  # Usar la misma imagen
                                )
                                talleres_nuevos_creados += 1
                                
                            except Exception as e:
                                messages.error(request, f'❌ Error al crear fecha adicional {fecha_str}: {str(e)}')
                
                if talleres_nuevos_creados > 0:
                    messages.success(request, f"📝 Taller actualizado y {talleres_nuevos_creados} fecha(s) adicional(es) creada(s).")
                else:
                    messages.success(request, "📝 Taller actualizado correctamente.")

            return redirect('panel_talleres')
            
        except Exception as e:
            messages.error(request, f'❌ Error al guardar el taller: {str(e)}')
            return redirect('panel_talleres')
        
    context = {
        'talleres': talleres,
        'talleres_base': talleres_base,
    }
    return render(request, 'tienda/panel_talleres.html', context)

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