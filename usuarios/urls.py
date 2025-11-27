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

    # URLs para recuperación de contraseña (SIN subject_template_name para evitar el error)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='usuario/password_reset_form.html',
             email_template_name='usuario/password_reset_email.html',
             success_url='/usuarios/password-reset/done/' 
         ), 
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='usuario/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='usuario/password_reset_confirm.html',
             success_url='/usuarios/password-reset-complete/'  
         ), 
         name='password_reset_confirm'),
    
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='usuario/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]