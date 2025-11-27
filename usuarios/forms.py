from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date

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

    def clean_username(self):
        username = self.cleaned_data.get('username')
        
        # Validar si el usuario ingresó solo dígitos
        if username and username.isdigit():
            raise ValidationError("El nombre de usuario no puede estar compuesto solo por números.")
            
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Validar que el email sea único en el registro
        if UserModel.objects.filter(email=email).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean_fecha_cumpleanos(self):
        fecha = self.cleaned_data.get('fecha_cumpleanos')
        if fecha:
            hoy = date.today()
            # 1. Validar que no sea una fecha futura
            if fecha > hoy:
                raise ValidationError("La fecha de nacimiento no puede estar en el futuro.")
            
            # 2. Validar mayoría de edad (Opcional: ajusta el 18 según necesites)
            edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
            if edad < 18:
                raise ValidationError("Debes ser mayor de 18 años para registrarte.")
        return fecha

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

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Validar unicidad EXCLUYENDO al usuario actual (para que pueda guardar su propio email)
        if self.instance.pk:
            if UserModel.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError("Este correo electrónico ya está en uso por otro usuario.")
        return email

    class Meta:
        model = UserModel
        fields = ('username', 'email', 'fecha_cumpleanos', 'avatar')
        
        # Opcional: Si el error persiste, listamos todos los campos que NO queremos.
        # En la mayoría de los casos, la lista 'fields' es suficiente.

    # Al usar 'exclude', el formulario renderizará automáticamente username, email, 
    # fecha_cumpleanos y avatar, ya que son los únicos campos restantes en el modelo 
    # que no fueron excluidos.