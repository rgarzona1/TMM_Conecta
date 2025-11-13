from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import MensajeContactoForm, ResenaForm
from .models import Taller, Producto, Resena
from django.contrib.auth.decorators import login_required



def conectar_view(request):
    if request.method == 'POST':
        form = MensajeContactoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Tu mensaje fue enviado correctamente.')
            return redirect('contacto')
        else:
            messages.error(request, '⚠️ Revisa los campos, hubo un error.')
    else:
        form = MensajeContactoForm()

    return render(request, 'web/contacto.html', {'form': form})

def home_view(request):
    talleres = Taller.objects.filter(activo=True).order_by('-fecha')
    productos = Producto.objects.filter(activo=True).order_by('-nombre')
    # Obtener las últimas 3 reseñas aprobadas
    resenas = Resena.objects.filter(aprobada=True).select_related('usuario')[:3]
    # Procesar formulario de reseña
    if request.method == 'POST':
        if request.user.is_authenticated:
            form = ResenaForm(request.POST)
            if form.is_valid():
                nueva = form.save(commit=False)
                nueva.usuario = request.user
                nueva.aprobada = False  
                nueva.save()
                messages.success(request, "🌷 Tu reseña ha sido enviada y está pendiente de aprobación.")
                return redirect('home')
        else:
            messages.warning(request, "Debes iniciar sesión para dejar una reseña.")
            return redirect('login')
    else:
        form = ResenaForm()
    
    context = {
        'talleres': talleres,
        'productos': productos,
        'resenas': resenas
    }
    return render(request, 'web/home.html', context)

@login_required
def crear_resena_vista(request):
    if request.method == "POST":
        form = ResenaForm(request.POST)
        if form.is_valid():
            nueva = form.save(commit=False)
            nueva.usuario = request.user
            nueva.aprobada = False   
            nueva.save()

            messages.success(request, "Tu reseña fue enviada y está pendiente de aprobación.")
            return redirect('home')  
    else:
        form = ResenaForm()

    return render(request, 'web/resena_formulario.html', {'form': form})