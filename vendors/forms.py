from django import forms
from django.utils.text import slugify
from django.utils import timezone
from .models import (
    AdPlacementRequest,
    BusinessProfile,
    SponsoredProductCampaign,
    SupportServiceOrder,
    VendorApplication,
)
from decimal import Decimal, InvalidOperation
from store.models import Product, ProductMedia, ProductVariant
import random
import string

class VendorApplicationForm(forms.ModelForm):
    class Meta:
        model = VendorApplication
        fields = ['company_name', 'tax_number', 'phone', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Lütfen faaliyet alanınız ve satacağınız ürünler hakkında detaylı bilgi verin.'}),
        }


class BusinessProfileForm(forms.ModelForm):
    class Meta:
        model = BusinessProfile
        fields = [
            'legal_name',
            'trade_name',
            'tax_office',
            'tax_number',
            'mersis_no',
            'contact_person',
            'phone',
            'billing_email',
            'city',
            'district',
            'address',
            'iban',
            'website',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class SponsoredProductCampaignForm(forms.ModelForm):
    class Meta:
        model = SponsoredProductCampaign
        fields = ['product', 'placement', 'title', 'daily_budget', 'starts_at', 'ends_at']
        widgets = {
            'starts_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'ends_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        vendor = kwargs.pop('vendor')
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = vendor.products.filter(is_active=True).order_by('name')
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['placement'].widget.attrs['class'] = 'form-select'
        self.fields['product'].widget.attrs['class'] = 'form-select'

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error('ends_at', 'Bitiş tarihi başlangıçtan sonra olmalıdır.')
        if ends_at and ends_at <= timezone.now():
            self.add_error('ends_at', 'Bitiş tarihi gelecekte olmalıdır.')
        return cleaned_data


class AdPlacementRequestForm(forms.ModelForm):
    class Meta:
        model = AdPlacementRequest
        fields = ['placement', 'title', 'description', 'image', 'target_url', 'starts_at', 'ends_at']
        widgets = {
            'description': forms.TextInput(attrs={'maxlength': 240}),
            'starts_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'ends_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['placement'].widget.attrs['class'] = 'form-select'

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error('ends_at', 'Bitiş tarihi başlangıçtan sonra olmalıdır.')
        if ends_at and ends_at <= timezone.now():
            self.add_error('ends_at', 'Bitiş tarihi gelecekte olmalıdır.')
        return cleaned_data


class SupportServiceOrderForm(forms.ModelForm):
    class Meta:
        model = SupportServiceOrder
        fields = ['request_note']
        widgets = {
            'request_note': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'İhtiyacınızı, beklediğiniz çıktıyı ve varsa ürün/kategori detaylarını yazın.',
            }),
        }

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(file, initial) for file in files]


class VendorProductForm(forms.ModelForm):
    gallery_images = MultipleFileField(
        label='Ek Ürün Fotoğrafları',
        required=False,
        help_text='Birden fazla fotoğraf seçebilirsiniz. En fazla 12 fotoğraf, fotoğraf başına 8 MB.',
        widget=MultipleFileInput(attrs={
            'accept': 'image/*',
            'multiple': True,
            'class': 'form-control form-control-lg',
        }),
    )
    product_video = forms.FileField(
        label='Ürün Videosu',
        required=False,
        help_text='MP4, WebM veya MOV dosyası yükleyebilirsiniz. En fazla 120 MB.',
        widget=forms.ClearableFileInput(attrs={
            'accept': 'video/mp4,video/webm,video/quicktime',
            'class': 'form-control form-control-lg',
        }),
    )
    variant_rows = forms.CharField(
        label='Ürün Varyantları',
        required=False,
        help_text='Her satır: Seçenek|Değer|SKU|Fiyat farkı|Stok. Örn: Renk|Siyah|IPH-SYH|0|12',
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': 'Renk|Siyah|SKU-001|0|10\nDepolama|256GB|SKU-256|2500|5',
        }),
    )

    class Meta:
        model = Product
        fields = ['name', 'category', 'description', 'price', 'discount_price', 'stock', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        self.vendor = kwargs.pop('vendor', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk and not self.is_bound:
            self.fields['variant_rows'].initial = '\n'.join(
                f'{variant.option_name}|{variant.option_value}|{variant.sku}|{variant.price_delta}|{variant.stock}'
                for variant in self.instance.variants.order_by('display_order', 'id')
            )

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        discount_price = cleaned_data.get('discount_price')

        if price and discount_price and discount_price >= price:
            self.add_error('discount_price', 'İndirimli fiyat, normal fiyattan düşük olmalıdır.')

        gallery_images = cleaned_data.get('gallery_images') or []
        if len(gallery_images) > 12:
            self.add_error('gallery_images', 'Tek seferde en fazla 12 ek fotoğraf yükleyebilirsiniz.')
        for uploaded_file in gallery_images:
            if uploaded_file.size > 8 * 1024 * 1024:
                self.add_error('gallery_images', f'{uploaded_file.name} 8 MB sınırını aşıyor.')
            if uploaded_file.content_type and not uploaded_file.content_type.startswith('image/'):
                self.add_error('gallery_images', f'{uploaded_file.name} geçerli bir fotoğraf dosyası değil.')

        product_video = cleaned_data.get('product_video')
        if product_video:
            allowed_video_types = {'video/mp4', 'video/webm', 'video/quicktime'}
            if product_video.size > 120 * 1024 * 1024:
                self.add_error('product_video', 'Video dosyası 120 MB sınırını aşamaz.')
            if product_video.content_type and product_video.content_type not in allowed_video_types:
                self.add_error('product_video', 'Lütfen MP4, WebM veya MOV formatında video yükleyin.')

        variant_rows = cleaned_data.get('variant_rows') or ''
        parsed_variants = []
        seen_variants = set()
        for line_number, raw_line in enumerate(variant_rows.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split('|')]
            if len(parts) != 5:
                self.add_error('variant_rows', f'{line_number}. satır 5 parçadan oluşmalı: Seçenek|Değer|SKU|Fiyat farkı|Stok.')
                continue
            option_name, option_value, sku, price_delta, stock = parts
            if not option_name or not option_value:
                self.add_error('variant_rows', f'{line_number}. satırda seçenek adı ve değeri zorunludur.')
                continue
            try:
                price_delta = Decimal(price_delta.replace(',', '.'))
                stock = int(stock)
            except (InvalidOperation, ValueError):
                self.add_error('variant_rows', f'{line_number}. satırda fiyat farkı veya stok geçersiz.')
                continue
            if stock < 0:
                self.add_error('variant_rows', f'{line_number}. satırda stok negatif olamaz.')
                continue
            variant_key = (option_name.lower(), option_value.lower())
            if variant_key in seen_variants:
                self.add_error('variant_rows', f'{line_number}. satırda aynı varyant daha önce eklenmiş.')
                continue
            seen_variants.add(variant_key)
            parsed_variants.append({
                'option_name': option_name,
                'option_value': option_value,
                'sku': sku,
                'price_delta': price_delta,
                'stock': stock,
            })
        cleaned_data['parsed_variants'] = parsed_variants

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

    def save_media(self, product):
        next_order = product.media.count() + 1
        for uploaded_file in self.cleaned_data.get('gallery_images') or []:
            ProductMedia.objects.create(
                product=product,
                media_type=ProductMedia.MediaType.IMAGE,
                file=uploaded_file,
                title=uploaded_file.name[:140],
                display_order=next_order,
            )
            next_order += 1

        product_video = self.cleaned_data.get('product_video')
        if product_video:
            ProductMedia.objects.create(
                product=product,
                media_type=ProductMedia.MediaType.VIDEO,
                file=product_video,
                title=product_video.name[:140],
                display_order=next_order,
            )

    def save_variants(self, product):
        if 'variant_rows' not in self.cleaned_data:
            return
        ProductVariant.objects.filter(product=product).delete()
        for index, variant in enumerate(self.cleaned_data.get('parsed_variants') or [], start=1):
            ProductVariant.objects.create(
                product=product,
                display_order=index,
                is_active=True,
                **variant,
            )


class BulkProductUploadForm(forms.Form):
    file = forms.FileField(
        label='Excel Dosyası',
        help_text='Sadece .xlsx dosyası yükleyin. En fazla 5 MB.',
        widget=forms.ClearableFileInput(attrs={
            'accept': '.xlsx',
            'class': 'form-control',
        }),
    )
    update_existing = forms.BooleanField(
        label='Aynı isimli ürünleri güncelle',
        required=False,
        help_text='Kapalıysa aynı isimli ürünler hata olarak raporlanır.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
    )
    activate_products = forms.BooleanField(
        label='Dosyadaki ürünleri aktif olarak işaretle',
        required=False,
        initial=True,
        help_text='Excel içindeki Aktif kolonu boşsa bu seçim kullanılır.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
    )

    def clean_file(self):
        uploaded_file = self.cleaned_data['file']
        if not uploaded_file.name.lower().endswith('.xlsx'):
            raise forms.ValidationError('Lütfen .xlsx uzantılı bir Excel dosyası yükleyin.')
        if uploaded_file.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Dosya boyutu 5 MB sınırını aşamaz.')
        return uploaded_file
