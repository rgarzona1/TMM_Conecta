from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'), 
    path('contacto/', views.conectar_view, name='contacto'),
    path('reseñas/nueva/', views.crear_resena_vista, name='crear_resena'),
    path('panel/consultas/', views.panel_consultas, name='panel_consultas'),
    path('panel/consultas/<int:pk>/', views.detalle_consulta, name='detalle_consulta'),
    path('panel/consultas/<int:pk>/eliminar/', views.eliminar_consulta, name='eliminar_consulta'),
    path('panel/resenas/aprobar/<int:id>/', views.aprobar_resena, name='aprobar_resena'),
    path('panel/resenas/eliminar/<int:id>/', views.eliminar_resena, name='eliminar_resena'),

]
