from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import MensajeContactoForm, ResenaForm
from .models import Taller, Producto, Resena
from django.contrib.auth.decorators import login_required
from Web.models import MensajeContacto


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

@login_required
def panel_consultas(request):
    """Vista para gestionar los mensajes de contacto"""
    
    # Filtro por asunto
    asunto_filtro = request.GET.get('asunto', 'TODOS')
    
    if asunto_filtro == 'TODOS':
        consultas = MensajeContacto.objects.all().order_by('-fecha_envio')
    else:
        consultas = MensajeContacto.objects.filter(asunto=asunto_filtro).order_by('-fecha_envio')
    
    # Estadísticas
    total_consultas = MensajeContacto.objects.count()
    cotizaciones = MensajeContacto.objects.filter(asunto='cotizacion').count()
    dudas = MensajeContacto.objects.filter(asunto='dudas').count()
    problemas = MensajeContacto.objects.filter(asunto='problemas').count()
    otros = MensajeContacto.objects.filter(asunto='otros').count()
    
    context = {
        'consultas': consultas,
        'asunto_filtro': asunto_filtro,
        'total_consultas': total_consultas,
        'cotizaciones': cotizaciones,
        'dudas': dudas,
        'problemas': problemas,
        'otros': otros,
    }
    
    return render(request, 'tienda/panel_mensajes.html', context)


@login_required
def detalle_consulta(request, pk):
    """Vista para ver el detalle de una consulta"""
    consulta = get_object_or_404(MensajeContacto, pk=pk)
    return render(request, 'tienda/detalle_consulta.html', {'consulta': consulta})


@login_required
def eliminar_consulta(request, pk):
    """Vista para eliminar una consulta"""
    consulta = get_object_or_404(MensajeContacto, pk=pk)
    
    if request.method == 'POST':
        nombre = consulta.nombre_completo
        consulta.delete()
        messages.success(request, f'🗑️ Consulta de "{nombre}" eliminada correctamente.')
        return redirect('panel_consultas')
    
    return render(request, 'Web/confirmar_eliminar_consulta.html', {'consulta': consulta})

