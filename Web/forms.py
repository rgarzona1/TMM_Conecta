from django import forms
from .models import MensajeContacto

class MensajeContactoForm(forms.ModelForm):
    class Meta:
        model = MensajeContacto
        fields = ['nombre_completo', 'correo_electronico', 'asunto', 'mensaje', 'suscripcion']

        widgets = {
            'nombre_completo': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Tu nombre completo'
            }),
            'correo_electronico': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'tu@correo.com'
            }),
            'asunto': forms.Select(attrs={
                'class': 'form-select'
            }),
            'mensaje': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 5,
                'placeholder': 'Escribe tu mensaje aquí...'
            }),
            'suscripcion': forms.CheckboxInput(attrs={'class': 'form-checkbox'})
        }

        labels = {
            'nombre_completo': 'Nombre :',
            'correo_electronico': 'E-mail:',
            'asunto': 'Tipo de consulta',
            'mensaje': 'Mensaje:',
            'suscripcion': 'Quiero recibir actualizaciones sobre nuevos talleres y actividades de TMM - Bienestar y Conexión',
        }
        
