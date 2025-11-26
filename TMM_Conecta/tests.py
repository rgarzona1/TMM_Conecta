import uuid
from django.test import TestCase
from django.urls import reverse
from usuarios.models import UsuarioPersonalizado
from tienda.models import Producto, Carrito, CarritoItem, Orden, OrdenItem, Carrito, CarritoItem, Producto, Cupon
from django.utils import timezone
from tienda.models import Cupon, CuponAsignado
from Web.models import Resena, Taller 
from datetime import timedelta


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
        
        
class CuponTest(TestCase):

    def setUp(self):
        self.user = UsuarioPersonalizado.objects.create_user(
            username="rod", email="rod@test.com", password="1234"
        )

    def test_cupon_vigente(self):
        cupon = Cupon.objects.create(
            codigo="DESC10",
            porcentaje_descuento=10,
            fecha_inicio=timezone.localdate() - timedelta(days=1),
            fecha_expiracion=timezone.localdate() + timedelta(days=5),
            activo=True
        )
        self.assertTrue(cupon.esta_vigente())

    def test_cupon_expirado(self):
        cupon = Cupon.objects.create(
            codigo="OLD",
            porcentaje_descuento=20,
            fecha_inicio=timezone.localdate() - timedelta(days=10),
            fecha_expiracion=timezone.localdate() - timedelta(days=1),
            activo=True
        )
        self.assertFalse(cupon.esta_vigente())

    def test_marcar_cupon_usado(self):
        cupon = Cupon.objects.create(codigo="TEST", porcentaje_descuento=15)
        asign = CuponAsignado.objects.create(cupon=cupon, usuario=self.user)
        asign.marcar_usado()
        self.assertTrue(asign.usado)
        

class OrdenTest(TestCase):

    def setUp(self):
        self.user = UsuarioPersonalizado.objects.create_user("rod", "123")
        self.carrito = Carrito.objects.create(usuario=self.user)
        self.producto = Producto.objects.create(nombre="Kit", categoria="KIT", precio=10000)

    def test_crear_orden_con_descuento(self):
        CarritoItem.objects.create(carrito=self.carrito, producto=self.producto, cantidad=2)

        cupon = Cupon.objects.create(codigo="DESC20", porcentaje_descuento=20)

        total_bruto = self.carrito.get_total_bruto()  # 20000
        descuento = total_bruto * 0.20                # 4000

        orden = Orden.objects.create(usuario=self.user, total=total_bruto-descuento)

        self.assertEqual(orden.total, 16000)
        
        
        
class ResenaTest(TestCase):

    def setUp(self):
        self.user = UsuarioPersonalizado.objects.create_user("rod", "123")

    def test_crear_resena(self):
        r = Resena.objects.create(
            usuario=self.user,
            comentario="Muy bueno!", 
            calificacion=5
        )
        self.assertFalse(r.aprobada)
        self.assertEqual(r.usuario.username, "rod")
        
        
class PanelAdminTest(TestCase):

    def setUp(self):
        self.duena = UsuarioPersonalizado.objects.create_user(
            username="admin",
            email="duena@tmmconecta.cl",
            password="1234"
        )
        self.user = UsuarioPersonalizado.objects.create_user(
            username="rod",
            email="rod@test.com",
            password="1234"
        )

    def test_duena_accede_panel(self):
        self.client.login(username="admin", password="1234")
        r = self.client.get(reverse('panel_duena_inicio'))
        self.assertEqual(r.status_code, 200)

    def test_usuario_normal_no_accede(self):
        self.client.login(username="rod", password="1234")
        r = self.client.get(reverse('panel_duena_inicio'))
        self.assertEqual(r.status_code, 403)
        
        
class CompraSimuladaTest(TestCase):

    def setUp(self):
        self.user = UsuarioPersonalizado.objects.create_user("rod", "1234")
        self.client.login(username="rod", password="1234")
        self.carrito = Carrito.objects.create(usuario=self.user)
        self.prod = Producto.objects.create(
            nombre="Cera",
            categoria="SOJA",
            precio=10000
        )
        CarritoItem.objects.create(carrito=self.carrito, producto=self.prod, cantidad=1)

    def test_simulacion_compra(self):
        r = self.client.post(reverse('simular_compra'))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Orden.objects.filter(usuario=self.user).exists())
        orden = Orden.objects.last()
        self.assertEqual(orden.total, 10000)