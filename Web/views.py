from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import MensajeContactoForm
from .models import Taller, Producto, Resena


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
    # Obtener las últimas 6 reseñas aprobadas
    resenas = Resena.objects.filter(aprobada=True).select_related('usuario', 'taller')[:6]
    context = {
        'talleres': talleres,
        'productos': productos,
        'resenas': resenas
    }
    return render(request, 'web/home.html', context)