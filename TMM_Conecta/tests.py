import uuid
from django.test import TestCase
from django.urls import reverse
from Web.models import Taller
from usuarios.models import UsuarioPersonalizado
from tienda.models import Producto, Carrito, CarritoItem

class PruebasBasicas(TestCase):
    def setUp(self):
        self.user = UsuarioPersonalizado.objects.create_user(username='test', password='12345')
        self.producto = Producto.objects.create(nombre='Vela Aromática', precio=5000)
        self.taller = Taller.objects.create(titulo="Taller de Velas", valor=12000)
        self.carrito = Carrito.objects.create(usuario=self.user)


    def test_relacion_carrito_y_usuario(self):
        self.assertEqual(self.carrito.usuario.username, "test")

    def test_agregar_producto_al_carrito(self):
        self.client.login(username='test', password='12345')
        response = self.client.post(reverse('add_to_cart_producto', args=[self.producto.id]))
        self.assertEqual(response.status_code, 302)  # redirección

    
class SeguridadTests(TestCase):
    def test_csrf_protegido_en_formularios(self):
        response = self.client.get(reverse('registro'))
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_perfil_restringido_a_usuarios_no_logueados(self):
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.status_code, 302)  # Redirección al login

class VistasTests(TestCase):
    def setUp(self):
        self.user = UsuarioPersonalizado.objects.create_user(username="testuser", password="12345")

    def test_home_carga_correctamente(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_login_funciona(self):
        login = self.client.login(username="testuser", password="12345")
        self.assertTrue(login)

    def test_perfil_requiere_login(self):
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.status_code, 302)  # redirige al login

    def test_contacto_carga(self):
        response = self.client.get(reverse('contacto'))
        self.assertEqual(response.status_code, 200)
        
class CarritoTests(TestCase):
    def setUp(self):
        # Crear un usuario único para cada ejecución (evita duplicados)
        self.user = UsuarioPersonalizado.objects.create_user(
            username=f"user_{uuid.uuid4()}",
            password="12345"
        )
        self.producto = Producto.objects.create(nombre="Taller Creativo", precio=20000)

        # Crear el carrito sin riesgo de duplicados
        self.carrito, created = Carrito.objects.get_or_create(usuario=self.user)

    def test_agregar_producto_al_carrito(self):
        """Verifica que el total del carrito se calcule correctamente"""
        item = CarritoItem.objects.create(carrito=self.carrito, producto=self.producto, cantidad=1)
        self.assertEqual(self.carrito.get_total_bruto(), 20000)

    def test_carrito_vacio(self):
        """Verifica que el carrito vacío devuelva total = 0"""
        # usuario distinto para evitar conflicto
        nuevo_usuario = UsuarioPersonalizado.objects.create_user(username=f"user_{uuid.uuid4()}", password="12345")
        carrito_vacio, _ = Carrito.objects.get_or_create(usuario=nuevo_usuario)
        self.assertEqual(carrito_vacio.get_total_bruto(), 0)