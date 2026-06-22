from django import forms
from .models import Order

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['shipping_address', 'phone', 'note']
        widgets = {
            'shipping_address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Açık teslimat adresinizi giriniz.'}),
            'phone': forms.TextInput(attrs={'placeholder': '05XX XXX XX XX'}),
            'note': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Siparişinizle ilgili eklemek istedikleriniz (opsiyonel)'}),
        }

class CouponForm(forms.Form):
    code = forms.CharField(
        max_length=50, 
        widget=forms.TextInput(attrs={'placeholder': 'Kupon Kodu', 'class': 'form-control'})
    )
