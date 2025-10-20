#este coso es el menú desplegable
from .models import Producto

def categorias_tienda(request):
    
    return {
        'CATEGORIAS_TIENDA': Producto.CATEGORIA_CHOICES,
    }