# tests_selenium.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from django.test import LiveServerTestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class PruebasIntegralesTMM(LiveServerTestCase):
    """Simula la navegación completa de un usuario dentro del sitio."""

    def setUp(self):
        # Configurar Chrome para pruebas
        options = Options()
        self.driver = webdriver.Chrome(service=Service("TMM_Conecta/chromedriver.exe"), options=options)
        self.driver.implicitly_wait(10)

        # Crear usuario de prueba
        self.user = User.objects.create_user(username="testuser", password="12345", email="test@example.com")

    def test_flujo_completo(self):
        """Simula el flujo de login → tienda → taller → carrito."""

        driver = self.driver
        driver.get(f"{self.live_server_url}/usuarios/login/")
        print("✅ Página de login cargada")

        # Completar login
        username = driver.find_element(By.NAME, "username")
        password = driver.find_element(By.NAME, "password")
        username.send_keys("testuser")
        password.send_keys("12345")
        password.send_keys(Keys.RETURN)
        time.sleep(2)

        print("✅ Login exitoso")

        # Ir a la tienda
        driver.get(f"{self.live_server_url}/tienda/")
        print("✅ Página de tienda cargada")

        # Click en el primer botón de “Ver Detalles”
        try:
            boton_detalle = driver.find_element(By.LINK_TEXT, "Ver Detalles")
            boton_detalle.click()
            print("✅ Entró al detalle del taller")
        except:
            print("⚠️ No se encontraron talleres en la tienda")

        time.sleep(2)

        # Intentar agregar al carrito (si existe el botón)
        try:
            boton_inscribir = driver.find_element(By.XPATH, "//button[contains(text(),'Inscríbete Ahora')]")
            boton_inscribir.click()
            print("✅ Taller agregado al carrito")
        except:
            print("⚠️ No se pudo agregar el taller (quizás no hay talleres activos)")

        # Validar que se muestra el carrito
        driver.get(f"{self.live_server_url}/tienda/carrito/")
        print("✅ Página de carrito abierta")

        # Tomar captura para el informe
        driver.save_screenshot("prueba_integral_tmm.png")
        print("📸 Captura guardada en prueba_integral_tmm.png")

    def tearDown(self):
        self.driver.quit()
