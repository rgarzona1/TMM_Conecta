from django.db import models
from usuarios.models import UsuarioPersonalizado # Importamos tu modelo

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
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    
    def get_total(self):
        # Calcula el precio total del ítem (precio unitario * cantidad)
        return self.producto.precio * self.cantidad
        
    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"