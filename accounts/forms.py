from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name')
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError('E-posta adresi zorunludur.')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Bu e-posta adresi zaten kullanılıyor.')
        return email

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'address', 'city', 'avatar', 'is_vendor')

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone', 'address', 'city', 'avatar')
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }
