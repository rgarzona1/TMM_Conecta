from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.perfil_vista, name='usuario_base'),
    path('registro/', views.registro_vista, name='registro'),
    path('perfil/', views.perfil_vista, name='perfil'),
    path('login/', auth_views.LoginView.as_view(template_name='usuario/login.html'), name='login'),
    path('logout/', views.logout_vista, name='logout'),
    path('editar/', views.editar_perfil, name='editar_perfil'),
]
