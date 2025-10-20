from django.db import models

# Create your models here.
# usuarios/models.py

from django.contrib.auth.models import AbstractUser
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_delete
import os # Necesario para manejar paths de archivos

class UsuarioPersonalizado(AbstractUser):
    """
    Modelo de usuario personalizado que extiende al modelo base de Django
    para incluir la fecha de cumpleaños y el campo de avatar.
    """
    fecha_cumpleanos = models.DateField(null=True, blank=True)
    
    # Campo para la imagen de perfil. 
    # CRÍTICO: El archivo 'default_avatar.png' debe existir en tu carpeta MEDIA_ROOT/avatars/
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        default='avatars/default_avatar.png'
    )
    
    notificacion_bienvenida_vista = models.BooleanField(default=False)

    def __str__(self):
        return self.email or self.username


class TallerAsistido(models.Model):
    """
    Modelo para registrar el historial de talleres del cliente.
    """
    ESTADO_CHOICES = [
        ('ASISTIDO', 'Asistido'),
        ('POR_REALIZAR', 'Por realizar'),
        ('AUSENTE', 'Ausente'),
    ]
    
    usuario = models.ForeignKey(UsuarioPersonalizado, on_delete=models.CASCADE)
    nombre_taller = models.CharField(max_length=100)
    fecha = models.DateField()
    lugar = models.CharField(max_length=100)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='POR_REALIZAR')
    
    class Meta:
        verbose_name_plural = "Talleres Asistidos"

    def __str__(self):
        return f"{self.nombre_taller} - {self.usuario.username}"


# ===============================================
# SEÑALES PARA LIMPIEZA DE ARCHIVOS DE MEDIOS
# ===============================================

@receiver(pre_save, sender=UsuarioPersonalizado)
def borrar_avatar_anterior_on_change(sender, instance, **kwargs):
    """
    Elimina el archivo de avatar anterior del disco si se sube uno nuevo.
    """
    if not instance.pk:
        return # Nueva instancia, no hay avatar anterior

    try:
        antiguo = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return # La instancia no existía

    antiguo_avatar = antiguo.avatar
    nuevo_avatar = instance.avatar
    default_name = sender._meta.get_field('avatar').default # Obtiene 'avatars/default_avatar.png'

    # Solo proceder si los avatares son diferentes
    if antiguo_avatar and nuevo_avatar and antiguo_avatar.name != nuevo_avatar.name:
        # 1. Aseguramos que el avatar anterior no sea el por defecto
        if antiguo_avatar.name != default_name:
            # 2. Eliminamos el archivo del disco
            if os.path.isfile(antiguo_avatar.path):
                 antiguo_avatar.delete(save=False)


@receiver(post_delete, sender=UsuarioPersonalizado)
def borrar_avatar_on_delete(sender, instance, **kwargs):
    """
    Elimina el archivo de avatar del disco cuando el usuario es eliminado.
    """
    avatar = instance.avatar
    default_name = sender._meta.get_field('avatar').default
    
    if avatar and avatar.name:
        # Aseguramos que el archivo a borrar no sea el por defecto
        if avatar.name != default_name:
            if os.path.isfile(avatar.path):
                avatar.delete(save=False)