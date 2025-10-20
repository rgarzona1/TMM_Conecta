from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'), 
    path('contacto/', views.conectar_view, name='contacto'),
]
