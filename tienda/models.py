from django.db import models
from usuarios.models import UsuarioPersonalizado # Importamos tu modelo
from Web.models import Taller  # Importa el modelo base que usas en home
from django.conf import settings

class Producto(models.Model):
    CATEGORIA_CHOICES = [
        ('ENCUADERNACION', 'Encuadernación'),
        ('KIT', 'Kit de Iniciación'),
        ('RESINA', 'Resina Epóxica'),
        ('AROMATERAPIA', 'Aromaterapia'),
        ('SOJA', 'Velas de Soja'),
        ('VINILO', 'Vinilo'),
    ]
    
    nombre = models.CharField(max_length=150)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='ENCUADERNACION')
    precio = models.DecimalField(max_digits=10, decimal_places=0) # Asumimos precio entero sin decimales (ej. 54990)
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    descripcion_corta = models.CharField(max_length=255, default='Insumo de alta calidad.')

    def __str__(self):
        return self.nombre

class Carrito(models.Model):
    # Un carrito por usuario (o por sesión anónima, pero aquí usamos el usuario)
    usuario = models.OneToOneField(UsuarioPersonalizado, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def get_total_bruto(self):
        # Calcula la suma de todos los totales de los ítems
        total = sum(item.get_total() for item in self.items.all())
        return total

    def __str__(self):
        return f"Carrito de {self.usuario.username}"

class CarritoItem(models.Model):
    carrito = models.ForeignKey(Carrito, related_name='items', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True)
    taller_evento = models.ForeignKey('TallerEvento', on_delete=models.CASCADE, null=True, blank=True)

    cantidad = models.IntegerField(default=1)
    
    def get_total(self):
        # Calcula el precio total del ítem (precio unitario * cantidad)
        if self.producto:
            return self.producto.precio * self.cantidad
        elif self.taller_evento:
            return self.taller_evento.precio * self.cantidad
        return 0
        
    def __str__(self):
        if self.producto:
            return f"{self.cantidad} x {self.producto.nombre}"
        elif self.taller_evento:
            return f"{self.cantidad} x Taller: {self.taller_evento.taller_base.titulo}"
        return "Ítem sin referencia"
    
#TALLERES ESPECIFICOS PROXIMOS PARA RESERVAS

class TallerEvento(models.Model):
    taller_base = models.ForeignKey(
        Taller,
        on_delete=models.CASCADE,
        related_name="eventos",
        verbose_name="Tipo de Taller"
    )

    descripcion_completa = models.TextField(verbose_name="Descripción, objetivos y materiales")
    precio = models.DecimalField(max_digits=10, decimal_places=0)
    imagen = models.ImageField(upload_to='talleres/', null=True, blank=True)
    
    fecha_proxima = models.DateField(verbose_name="Fecha del Evento")
    hora_inicio = models.TimeField(verbose_name="Hora de Inicio")
    lugar = models.CharField(max_length=255, verbose_name="Ubicación")
    profesor = models.CharField(max_length=100, default="Carolina López Pérez")
    capacidad = models.IntegerField(default=8, verbose_name="Capacidad Máxima") 

    TIPO_CHOICES = [('PRESENCIAL', 'Presencial'), ('ONLINE', 'Online')]
    tipo_taller = models.CharField(max_length=20, choices=TIPO_CHOICES, default='PRESENCIAL')

    def __str__(self):
        return f"{self.taller_base.titulo} ({self.fecha_proxima})"

    class Meta:
        verbose_name = "Taller Programado"
        verbose_name_plural = "Talleres Programados"

class ImagenTaller(models.Model):
    taller = models.ForeignKey(
        TallerEvento,
        on_delete=models.CASCADE,
        related_name='galeria'
    )
    imagen = models.ImageField(upload_to='talleres/galeria/')
    descripcion = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Imagen de {self.taller.taller_base.titulo}"


#ORDENES DE COMPRA
class Orden(models.Model):
    usuario= models.ForeignKey(UsuarioPersonalizado, on_delete=models.PROTECT)
    total= models.DecimalField(max_digits=12, decimal_places=2)
    estado= models.CharField(max_length=20, default='PENDIENTE')
    mp_preference_id=models.CharField(max_length=100,blank=True, null=True)
    mp_payment_id=models.CharField(max_length=100,blank=True, null=True)
    pagado_en = models.DateTimeField(blank=True, null=True)
    creado_en= models.DateTimeField(auto_now_add=True)
    
    
class OrdenItem(models.Model):
    orden= models.ForeignKey(Orden, related_name='items', on_delete=models.CASCADE)
    tipo= models.CharField(max_length=20, default='PRODUCTO') # 'PRODUCTO' o 'TALLER'
    referencia_id= models.PositiveBigIntegerField()
    titulo= models.CharField(max_length=200)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario= models.DecimalField(max_digits=12, decimal_places=2)