from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

# Obtener el modelo de usuario personalizado
UserModel = get_user_model()

# =======================================================
# 1. FORMULARIO DE REGISTRO (Base)
# =======================================================
class FormularioRegistroPersonalizado(UserCreationForm):
    username = forms.CharField(
        error_messages={
            'unique': 'Este nombre de usuario ya está en uso.',
            'required': 'Por favor, ingrese un nombre de usuario.',
        },
        widget=forms.TextInput(attrs={'placeholder': 'Nombre de usuario'})
    )
    
    email = forms.EmailField(
        error_messages={
            'invalid': 'Por favor, ingrese un correo electrónico válido.',
            'required': 'Por favor, ingrese un correo electrónico.',
        },
        widget=forms.EmailInput(attrs={'placeholder': 'Correo electrónico'})
    )
    
    password1 = forms.CharField(
        error_messages={
            'required': 'Por favor, ingrese una contraseña.',
        },
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña'})
    )
    
    password2 = forms.CharField(
        error_messages={
            'required': 'Por favor, confirme su contraseña.',
        },
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirmar contraseña'})
    )

    fecha_cumpleanos = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'text', 'placeholder': 'DD - MM - AAAA'}),
        input_formats=['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d'], 
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_messages['password_mismatch'] = 'Las contraseñas no coinciden.'
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None

    class Meta(UserCreationForm.Meta):
        model = UserModel
        fields = ('username', 'email', 'fecha_cumpleanos')

# =======================================================
# 2. FORMULARIO DE EDICIÓN DE PERFIL (Carga de Archivo y Exclusión de Contraseña)
# =======================================================

class UsuarioEdicionForm(forms.ModelForm):
    # Campos de entrada
    username = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'campo-estilo', 'placeholder': 'Nuevo Nombre de Usuario'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'campo-estilo', 'placeholder': 'Nuevo Correo Electrónico'})
    )
    fecha_cumpleanos = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'campo-estilo', 'placeholder': 'AAAA-MM-DD'}),
        input_formats=['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']
    )

    # Campo de carga de archivo
    avatar = forms.ImageField(
        required=False,
        label="Subir nueva imagen de perfil"
    )
    class Meta:
        model = UserModel
        # 🚨 SOLUCIÓN DEFINITIVA: Listar explícitamente SÓLO los campos que queremos renderizar
        fields = ('username', 'email', 'fecha_cumpleanos', 'avatar')
        
        # Opcional: Si el error persiste, listamos todos los campos que NO queremos.
        # En la mayoría de los casos, la lista 'fields' es suficiente.

    # Al usar 'exclude', el formulario renderizará automáticamente username, email, 
    # fecha_cumpleanos y avatar, ya que son los únicos campos restantes en el modelo 
    # que no fueron excluidos.