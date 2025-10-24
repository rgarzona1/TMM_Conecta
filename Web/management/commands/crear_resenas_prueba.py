from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tienda.models import TallerEvento
from Web.models import Resena
from django.utils import timezone
import random

class Command(BaseCommand):
    help = 'Crea reseñas de prueba para la web'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        
        # Lista de nombres de prueba
        nombres = [
            "María García", "Ana Rodríguez", "Laura López", "Sofía Martínez",
            "Isabella Sánchez", "Valentina Díaz", "Emma Torres", "Lucía Ruiz"
        ]
        
        # Comentarios de prueba
        comentarios = [
            "¡Una experiencia increíble! El taller superó todas mis expectativas. La instructora fue muy profesional y el ambiente era perfecto para aprender.",
            "Me encantó la dinámica del taller. Aprendí técnicas muy útiles que ahora aplico en mi día a día. ¡Totalmente recomendado!",
            "Un espacio maravilloso para conectar contigo misma. La energía del grupo fue muy especial y me llevo aprendizajes muy valiosos.",
            "Excelente taller, muy bien organizado y con contenido de calidad. Me gustó especialmente la parte práctica.",
            "Una experiencia transformadora. El taller me ayudó a encontrar nuevas formas de cuidarme y conectar con mi bienestar.",
            "Superó mis expectativas. La facilitadora creó un ambiente muy acogedor y las actividades fueron muy enriquecedoras.",
            "Me encantó la metodología del taller. Fue muy dinámico y práctico. Aprendí herramientas que ya estoy aplicando.",
            "Una experiencia única. El taller me dio exactamente lo que necesitaba en este momento de mi vida."
        ]

        # Crear usuarios de prueba si no existen
        usuarios_creados = []
        for nombre in nombres:
            username = nombre.lower().replace(" ", "_")
            email = f"{username}@example.com"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_active': True
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            usuarios_creados.append(user)

        # Obtener talleres existentes
        talleres = list(TallerEvento.objects.all())
        
        if not talleres:
            self.stdout.write(self.style.ERROR('No hay talleres en la base de datos. Crea algunos talleres primero.'))
            return

        # Crear reseñas
        for usuario in usuarios_creados:
            # Crear 1-3 reseñas por usuario
            for _ in range(random.randint(1, 3)):
                taller = random.choice(talleres)
                fecha = timezone.now() - timezone.timedelta(days=random.randint(1, 60))
                
                Resena.objects.create(
                    usuario=usuario,
                    taller=taller,
                    calificacion=random.randint(4, 5),  # Mayormente reseñas positivas
                    comentario=random.choice(comentarios),
                    fecha=fecha,
                    aprobada=True
                )

        self.stdout.write(self.style.SUCCESS('Reseñas de prueba creadas exitosamente'))