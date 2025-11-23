from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from tienda.models import Cupon, CuponAsignado
from usuarios.models import UsuarioPersonalizado

@receiver(post_save, sender=UsuarioPersonalizado)
def asignar_cupon_cumple(sender, instance, created, **kwargs):
    """
    Si es el día del cumpleaños del usuario, crea/recupera un cupón específico de cumpleaños y lo asigna.
    """
    try:
        if not instance.fecha_cumpleanos:
            return
        hoy = date.today()
        if instance.fecha_cumpleanos.month == hoy.month and instance.fecha_cumpleanos.day == hoy.day:
            codigo = f"CUMPLE{hoy.year}"
            cupon, created_c = Cupon.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'descripcion': 'Cupón de cumpleaños',
                    'porcentaje_descuento': 20,
                    'fecha_inicio': hoy,
                    'fecha_expiracion': hoy,  # dura un día (ajustable)
                    'uso_unico': True,
                    'activo': True
                }
            )
            # asignar solo si no está ya asignado
            asignacion, _ = CuponAsignado.objects.get_or_create(cupon=cupon, usuario=instance)
    except Exception as e:
        print("Error al asignar cupón de cumpleaños:", e)