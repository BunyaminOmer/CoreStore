from django import forms
from .models import CustomerAddress, Order, OrderServiceRequest, ProductQuestion, ProductReview, SiteFeedback


class CheckoutForm(forms.Form):
    ADDRESS_ACTION_PLACE_ORDER = 'place_order'
    ADDRESS_ACTION_SAVE = 'save_address'
    ADDRESS_ACTION_UPDATE = 'update_address'
    ADDRESS_ACTION_DELETE = 'delete_address'

    address_action = forms.CharField(widget=forms.HiddenInput(), initial=ADDRESS_ACTION_PLACE_ORDER)
    address_id = forms.ModelChoiceField(
        queryset=CustomerAddress.objects.none(),
        required=False,
        empty_label=None,
    )
    save_address = forms.BooleanField(label='Bu adresi kaydet', required=False, initial=True)
    set_default_address = forms.BooleanField(label='Varsayılan adres yap', required=False)
    address_title = forms.CharField(label='Adres Başlığı', max_length=80, required=False)
    shipping_recipient_name = forms.CharField(label='Alıcı Ad Soyad', max_length=160, required=False)
    phone = forms.CharField(label='Kargo Telefonu', max_length=20, required=False)
    shipping_city = forms.CharField(label='Şehir', max_length=80, required=False)
    shipping_district = forms.CharField(label='İlçe', max_length=80, required=False)
    shipping_postal_code = forms.CharField(label='Posta Kodu', max_length=12, required=False)
    shipping_address = forms.CharField(
        label='Açık Teslimat Adresi',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    billing_type = forms.ChoiceField(label='Fatura Tipi', choices=Order.BillingType.choices)
    billing_full_name = forms.CharField(label='Fatura Ad Soyad', max_length=180, required=False)
    billing_company_name = forms.CharField(label='Firma Ünvanı', max_length=200, required=False)
    billing_tax_office = forms.CharField(label='Vergi Dairesi', max_length=120, required=False)
    billing_tax_number = forms.CharField(label='Vergi/TCKN No', max_length=40, required=False)
    billing_email = forms.EmailField(label='Fatura E-postası', required=False)
    billing_phone = forms.CharField(label='Fatura Telefonu', max_length=20, required=False)
    billing_address = forms.CharField(
        label='Fatura Adresi',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    billing_same_as_shipping = forms.BooleanField(label='Fatura adresi teslimat adresiyle aynı', required=False, initial=True)
    note = forms.CharField(
        label='Sipariş Notu',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None:
            self.fields['address_id'].queryset = user.saved_addresses.all()

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('address_action') or self.ADDRESS_ACTION_PLACE_ORDER
        address = cleaned_data.get('address_id')

        if action in {self.ADDRESS_ACTION_UPDATE, self.ADDRESS_ACTION_DELETE} and not address:
            raise forms.ValidationError('Bu işlem için kayıtlı bir adres seçmelisiniz.')

        if action == self.ADDRESS_ACTION_DELETE:
            return cleaned_data

        required_fields = {
            'shipping_recipient_name': 'Alıcı ad soyad',
            'phone': 'Kargo telefonu',
            'shipping_city': 'Şehir',
            'shipping_address': 'Açık teslimat adresi',
        }
        for field, label in required_fields.items():
            if not cleaned_data.get(field):
                self.add_error(field, f'{label} zorunludur.')

        if cleaned_data.get('billing_same_as_shipping'):
            cleaned_data['billing_address'] = cleaned_data.get('shipping_address')
            cleaned_data['billing_phone'] = cleaned_data.get('phone')
            if not cleaned_data.get('billing_full_name'):
                cleaned_data['billing_full_name'] = cleaned_data.get('shipping_recipient_name')

        if cleaned_data.get('billing_type') == Order.BillingType.CORPORATE:
            for field, label in {
                'billing_company_name': 'Firma ünvanı',
                'billing_tax_office': 'Vergi dairesi',
                'billing_tax_number': 'Vergi numarası',
            }.items():
                if not cleaned_data.get(field):
                    self.add_error(field, f'{label} kurumsal fatura için zorunludur.')
        elif not cleaned_data.get('billing_full_name'):
            self.add_error('billing_full_name', 'Bireysel fatura için ad soyad zorunludur.')

        return cleaned_data

    def save_address_record(self, user):
        address = self.cleaned_data.get('address_id')
        action = self.cleaned_data.get('address_action') or self.ADDRESS_ACTION_PLACE_ORDER

        if action == self.ADDRESS_ACTION_DELETE and address:
            address.delete()
            return None

        should_save = action in {self.ADDRESS_ACTION_SAVE, self.ADDRESS_ACTION_UPDATE} or self.cleaned_data.get('save_address')
        if not should_save:
            return address

        if action != self.ADDRESS_ACTION_UPDATE or address is None:
            address = CustomerAddress(user=user)

        address.title = self.cleaned_data.get('address_title') or 'Adresim'
        address.recipient_name = self.cleaned_data['shipping_recipient_name']
        address.phone = self.cleaned_data['phone']
        address.city = self.cleaned_data['shipping_city']
        address.district = self.cleaned_data.get('shipping_district', '')
        address.address_line = self.cleaned_data['shipping_address']
        address.postal_code = self.cleaned_data.get('shipping_postal_code', '')
        address.is_default = self.cleaned_data.get('set_default_address') or not user.saved_addresses.exclude(pk=address.pk).exists()
        address.save()
        return address

    def build_order(self, user, total_amount, coupon=None, installment=None):
        address = self.save_address_record(user)
        installment = installment or {}
        return Order(
            user=user,
            total_amount=total_amount,
            installment_base_amount=installment.get('base_amount', total_amount),
            installment_card_group=installment.get('card_group'),
            installment_card_group_name=installment.get('card_group_name', ''),
            installment_count=installment.get('count', 1),
            installment_rate_percent=installment.get('rate_percent', 0),
            installment_monthly_amount=installment.get('monthly_amount', total_amount),
            coupon=coupon,
            shipping_address_ref=address,
            shipping_recipient_name=self.cleaned_data['shipping_recipient_name'],
            shipping_city=self.cleaned_data['shipping_city'],
            shipping_district=self.cleaned_data.get('shipping_district', ''),
            shipping_postal_code=self.cleaned_data.get('shipping_postal_code', ''),
            shipping_address=self.cleaned_data['shipping_address'],
            phone=self.cleaned_data['phone'],
            billing_type=self.cleaned_data['billing_type'],
            billing_full_name=self.cleaned_data.get('billing_full_name', ''),
            billing_company_name=self.cleaned_data.get('billing_company_name', ''),
            billing_tax_office=self.cleaned_data.get('billing_tax_office', ''),
            billing_tax_number=self.cleaned_data.get('billing_tax_number', ''),
            billing_email=self.cleaned_data.get('billing_email', ''),
            billing_phone=self.cleaned_data.get('billing_phone', ''),
            billing_address=self.cleaned_data.get('billing_address', ''),
            note=self.cleaned_data.get('note', ''),
        )

class CouponForm(forms.Form):
    code = forms.CharField(
        max_length=50, 
        widget=forms.TextInput(attrs={'placeholder': 'Kupon Kodu', 'class': 'form-control'})
    )


class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'title', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[(value, f'{value} / 5') for value in range(5, 0, -1)],
                attrs={'class': 'form-control-custom'},
            ),
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Ürün hakkındaki deneyiminizi yazın.',
                'class': 'form-control-custom',
            }),
        }


class ProductQuestionForm(forms.ModelForm):
    class Meta:
        model = ProductQuestion
        fields = ['question']
        widgets = {
            'question': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Ürün hakkında merak ettiğiniz şeyi yazın.',
                'class': 'form-control-custom',
            }),
        }


class OrderServiceRequestForm(forms.ModelForm):
    class Meta:
        model = OrderServiceRequest
        fields = ['request_type', 'reason', 'description']
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'reason': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Örn: Yanlış ürün, vazgeçtim, hasarlı geldi',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Talebinizle ilgili kısa bir açıklama yazın.',
            }),
        }


class SiteFeedbackForm(forms.ModelForm):
    class Meta:
        model = SiteFeedback
        fields = ['name', 'email', 'topic', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Geri bildiriminizi yazın.'}),
        }
