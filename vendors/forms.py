from django import forms
from django.utils.text import slugify
from .models import VendorApplication
from store.models import Product
import random
import string

class VendorApplicationForm(forms.ModelForm):
    class Meta:
        model = VendorApplication
        fields = ['company_name', 'tax_number', 'phone', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Lütfen faaliyet alanınız ve satacağınız ürünler hakkında detaylı bilgi verin.'}),
        }

class VendorProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'discount_price', 'stock', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        self.vendor = kwargs.pop('vendor', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        discount_price = cleaned_data.get('discount_price')

        if price and discount_price and discount_price >= price:
            self.add_error('discount_price', 'İndirimli fiyat, normal fiyattan düşük olmalıdır.')

        if not self.instance.pk and self.vendor:
            if not self.vendor.can_add_product:
                raise forms.ValidationError('Ürün ekleme limitinize ulaştınız. Lütfen yönetici ile iletişime geçin.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(instance.name)
            random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            instance.slug = f"{base_slug}-{random_string}"
        
        if commit:
            instance.save()
        return instance
