
from django.urls import path, re_path
from . import views



urlpatterns = [
    path('', views.tienda_home_vista, name='tienda_home'),
    re_path(r'^productos/(?P<categoria_slug>[\w-]+)/$', views.categoria_vista, name='tienda_categoria'),
    path('carrito/', views.carrito_vista, name='carrito'),
    path('carrito/add/producto/<int:producto_id>/', views.add_to_cart, name='add_to_cart_producto'),
    path('carrito/add/taller/<int:taller_id>/', views.add_to_cart, name='add_to_cart_taller'),
    path('carrito/update/<int:item_id>/<str:action>/', views.update_cart, name='update_cart'),
    path('talleres/', views.catalogo_talleres_vista, name='catalogo_talleres'),
    path('talleres/<int:taller_id>/', views.detalle_taller_vista, name='detalle_taller'),
    path('checkout/preference/', views.crear_preferencia, name='mp_crear_preferencia'),
    path('checkout/retorno/success/', views.retorno_success, name='mp_success'),
    path('checkout/retorno/pending/', views.retorno_pending, name='mp_pending'),
    path('checkout/retorno/failure/', views.retorno_failure, name='mp_failure'),
    path('webhooks/mercadopago/',views.webhook_mercadopago, name='mp_webhook'),
    path('checkout/', views.checkout_vista, name='checkout'),

]