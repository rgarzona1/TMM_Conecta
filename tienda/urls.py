from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.tienda_home_vista, name='tienda_home'),
    re_path(r'^productos/(?P<categoria_slug>[\w-]+)/$', views.categoria_vista, name='tienda_categoria'),
    path('carrito/', views.carrito_vista, name='carrito'),
    path('carrito/add/<int:producto_id>/', views.add_to_cart, name='add_to_cart'),
    path('carrito/update/<int:item_id>/<str:action>/', views.update_cart, name='update_cart'),
]