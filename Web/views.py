from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import MensajeContactoForm
from .models import Taller, Producto


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
    context = {
        'talleres': talleres,
        'productos': productos
    }
    return render(request, 'web/home.html', context)