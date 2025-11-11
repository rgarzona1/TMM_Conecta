from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import FormularioRegistroPersonalizado, UsuarioEdicionForm
from .models import UsuarioPersonalizado, TallerAsistido
from django.contrib.auth import logout
from tienda.views import es_duena

# ==========================
# REGISTRO DE USUARIO
# ==========================
def registro_vista(request):
    if request.method == 'POST':
        form = FormularioRegistroPersonalizado(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True  # aseguramos que pueda loguearse
            user.save()

            # Autenticar con username y password1 (UserCreationForm)
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user_auth = authenticate(request, username=username, password=password)

            if user_auth is not None:
                login(request, user_auth)
                messages.success(request, "¡Registro exitoso! Bienvenido.")
                return redirect('perfil')
            else:
                messages.error(request, "Usuario registrado pero ocurrió un error al iniciar sesión.")
                return redirect('login')
        else:
            messages.error(request, "Formulario inválido. Revisa los datos ingresados.")
    else:
        form = FormularioRegistroPersonalizado()

    return render(request, 'usuario/registro.html', {'form': form})

# ==========================
# PERFIL DE USUARIO
# ==========================
@login_required
def perfil_vista(request):
    usuario = request.user

    if es_duena(usuario):
        return redirect('panel_duena_inicio')
    
    mostrar_notificacion_exito = False

    if not usuario.notificacion_bienvenida_vista:
        mostrar_notificacion_exito = True
        usuario.notificacion_bienvenida_vista = True
        usuario.save()

    historial_talleres = TallerAsistido.objects.filter(usuario=usuario).order_by('-fecha')

    context = {
        'usuario': usuario,
        'historial_talleres': historial_talleres,
        'mostrar_notificacion_exito': mostrar_notificacion_exito,
    }
    return render(request, 'usuario/perfil.html', context)

# ==========================
# EDICIÓN DE PERFIL
# ==========================
@login_required
def editar_perfil(request):
    user = request.user

    
    if request.method == 'POST':
        form = UsuarioEdicionForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado correctamente.')
            return redirect('perfil')
        else:
            messages.error(request, 'Hubo un error al actualizar tu perfil.')
    else:
        form = UsuarioEdicionForm(instance=user)

    return render(request, 'usuario/editar_perfil.html', {'form': form, 'usuario': user})

# ==========================
# LOGOUT
# ==========================
@login_required
def logout_vista(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('login')
