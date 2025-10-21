from django.db import models

class MensajeContacto(models.Model):
    OPCIONES_ASUNTO = [
        ('cotizacion', 'Cotización de taller para empresa'),
        ('dudas', 'Dudas generales'),
        ('problemas', 'Problemas con mi reserva'),
        ('otros', 'Otros'),
    ]

    nombre_completo = models.CharField(max_length=100)
    correo_electronico = models.EmailField(max_length=254)
    asunto = models.CharField(max_length=50, choices=OPCIONES_ASUNTO)
    mensaje = models.TextField()
    suscripcion = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_completo} - {self.asunto}"

class Producto(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    activo = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)

    class Meta:
        db_table = 'producto'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return self.nombre

class Taller(models.Model):
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    fecha = models.DateField(blank=True, null=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    imagen = models.ImageField(upload_to='talleres/', blank=True, null=True)
    activo = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)

    class Meta:
        db_table = 'taller'
        verbose_name = 'Taller'
        verbose_name_plural = 'Talleres'

    def __str__(self):
        return self.titulo
    

