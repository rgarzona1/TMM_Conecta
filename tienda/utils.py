from decimal import Decimal
from .models import Carrito, Producto
from .models import TallerEvento  

def obtener_items_de_carrito(usuario):

    items = []
    total = Decimal('0')

    try:
        carrito = Carrito.objects.get(usuario=usuario)
    except Carrito.DoesNotExist:
        return [], Decimal('0')

    for it in carrito.items.all():
        if it.producto:
            title = it.producto.nombre
            unit_price = Decimal(str(it.producto.precio))
            items.append({
                "title": title,
                "quantity": it.cantidad,
                "unit_price": float(unit_price),
                "tipo": "producto",
                "referencia_id": it.producto.id
            })
            total += unit_price * it.cantidad
        elif hasattr(it, "taller_evento") and it.taller_evento:
            title = f"Taller: {it.taller_evento.taller_base.titulo} ({it.taller_evento.fecha_proxima})"
            unit_price = Decimal(str(it.taller_evento.precio))
            items.append({
                "title": title,
                "quantity": it.cantidad,  
                "unit_price": float(unit_price),
                "tipo": "taller",
                "referencia_id": it.taller_evento.id
            })
            total += unit_price * it.cantidad

    return items, total
