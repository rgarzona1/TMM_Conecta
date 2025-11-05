# 🌸 TMM Conecta – Bienestar y Conexión

**TMM Conecta** es una plataforma web desarrollada para **TMM Bienestar y Conexión**, un emprendimiento que promueve el bienestar integral a través de talleres creativos y productos personalizados.  
El proyecto busca **digitalizar la experiencia de reserva, compra y fidelización de clientes**, ofreciendo una plataforma intuitiva y funcional tanto para los usuarios como para la administradora del sitio.

---

## 🧩 Descripción General

El sistema permite que los usuarios:
- Visualicen **talleres** y **productos** ofrecidos por la empresa.  
- Realicen **compras y reservas** mediante un **carrito de compras** conectado a **Mercado Pago**.  
- Se **registren e inicien sesión** para acceder a beneficios exclusivos.  
- Reciban **cupones de fidelización** por fechas especiales.  
- Se comuniquen con la empresa a través de un **formulario de contacto**.

Por otro lado, el cliente (administrador) puede gestionar todo el contenido desde un **panel administrativo**, donde tiene control total sobre talleres, productos, usuarios y pedidos.

---

## ⚙️ Funcionalidades Principales

| # | Funcionalidad | Descripción |
|---|----------------|-------------|
| 1 | 🛒 **Carrito de compras** | Permite añadir productos y talleres, con integración a Mercado Pago. |
| 2 | 🎨 **Compra de talleres** | Los talleres pueden ser agregados al carrito e inscritos automáticamente tras el pago. |
| 3 | 📬 **Formulario de contacto** | Los usuarios pueden enviar consultas o solicitudes, registradas en la base de datos. |
| 4 | 🎁 **Fidelización** | Envío de cupones de descuento automáticos por cumpleaños o eventos. |
| 5 | 🔐 **Inicio de sesión y registro** | Acceso seguro a perfiles de usuario con avatares y datos personales. |
| 6 | 🧾 **Visualización de talleres y productos** | Catálogo dinámico con fotos, precios, fechas y disponibilidad. |
| 7 | 🌟 **Calificaciones y reseñas** | Muestra opiniones y experiencias de usuarios reales. |
| 8 | ⚙️ **Panel de administración** | Gestión completa de contenido (CRUD) para la administradora del sitio. |

---

## 🗃️ Estructura del Proyecto

/pending


---

## 🧠 Modelos Principales

- **UsuarioPersonalizado** – Extiende el modelo de usuario de Django con avatar y fecha de cumpleaños.  
- **Taller** – Representa la categoría base de talleres disponibles.  
- **TallerEvento** – Define talleres programados con fecha, hora, profesor y capacidad.  
- **Producto** – Catálogo de insumos y materiales.  
- **Carrito** y **CarritoItem** – Manejan la lógica de compra.  
- **MensajeContacto** – Registra las consultas enviadas desde el formulario.

---

## 🧰 Tecnologías Utilizadas

| Categoría | Herramientas |
|------------|--------------|
| **Framework Backend** | Django 5.2 (Python 3.13) |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Base de datos** | MySQL |
| **Autenticación** | Django Auth (modelo personalizado) |
| **Pasarela de Pago** | Mercado Pago API |
| **Pruebas Unitarias e Integrales** | `unittest`, `Selenium`, `Locust` |
| **Control de versiones** | Git + GitHub |
| **Entorno Virtual** | venv |
| **Servidor Local** | Django Development Server |

---

🧪 Pruebas Implementadas

Unitarias: Validación de modelos, relaciones y cálculos en el carrito.

Integrales (Selenium): Flujo completo de registro, inicio de sesión, y navegación por la tienda.

Rendimiento (Locust): Medición de tiempos de respuesta y carga de la aplicación.
