from locust import HttpUser, task, between

class UsuarioSimulado(HttpUser):
    wait_time = between(1, 5)  # tiempo entre acciones (segundos)
    
    @task(2)
    def visitar_home(self):
        """Simula la carga de la página principal"""
        self.client.get("/")
    
    @task(3)
    def visitar_tienda(self):
        """Simula que el usuario visita la tienda"""
        self.client.get("/tienda/")
    
    @task(2)
    def visitar_talleres(self):
        """Simula la carga de la sección de talleres"""
        self.client.get("/tienda/talleres/")
    
    @task(1)
    def ver_contacto(self):
        """Simula la visita al formulario de contacto"""
        self.client.get("/contacto/")
    
    @task(2)
    def ver_categorias(self):
        """Simula la visualización de productos por categoría"""
        self.client.get("/tienda/productos/accesorios/")
        self.client.get("/tienda/productos/velas/")
    
    @task(1)
    def ver_carrito(self):
        """Simula la carga del carrito de compras"""
        self.client.get("/tienda/carrito/")
    
    @task(2)
    def detalle_taller(self):
        """Simula la visualización de detalles de talleres específicos"""
        self.client.get("/tienda/talleres/1/")
        self.client.get("/tienda/talleres/2/")
    
    @task(1)
    def ver_perfil(self):
        """Simula la carga del perfil de usuario"""
        self.client.get("/usuarios/perfil/")
        
    @task(1)
    def registro_login(self):
        """Simula el acceso a las páginas de registro y login"""
        self.client.get("/usuarios/registro/")
        self.client.get("/usuarios/login/")
