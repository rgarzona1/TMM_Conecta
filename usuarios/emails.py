from django.core.mail import send_mail 
from django.conf import settings


def enviar_correo_bienvenida(usuario):
    asunto = "¡Bienvenido a TMM Conecta!"
    mensaje = f"Hola {usuario.username},\n\nGracias por registrarte en TMM Conecta. Estamos emocionados de tenerte con nosotros.\n\nSaludos,\nEl equipo de TMM Conecta"
    email_desde = settings.DEFAULT_FROM_EMAIL
    destinatario = [usuario.email]
    
    send_mail(
        asunto,
        mensaje,
        email_desde,
        destinatario,
        fail_silently=False,
    )
    
    
