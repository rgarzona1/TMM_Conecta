from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse

def enviar_solicitud_resena(usuario, taller):
    """
    Envía un correo electrónico al usuario solicitando una reseña del taller.
    """
    context = {
        'usuario': usuario,
        'taller': taller,
        'review_url': settings.SITE_URL + reverse('mis_talleres')
    }
    
    # Renderizar el template HTML
    html_message = render_to_string('emails/solicitud_resena.html', context)
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject='¡Cuéntanos tu experiencia en TMM!',
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        html_message=html_message
    )