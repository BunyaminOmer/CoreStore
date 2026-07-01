from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


class Category(models.Model):
    """Product category with optional parent for nested categories."""

    name = models.CharField(max_length=200, verbose_name='Kategori Adı')
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, verbose_name='Açıklama')
    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True,
        verbose_name='Görsel',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='children',
        verbose_name='Üst Kategori',
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Kategori'
        verbose_name_plural = 'Kategoriler'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        if self.parent_id and self.pk and self.parent_id == self.pk:
            raise ValidationError({'parent': 'Bir kategori kendi üst kategorisi olamaz.'})

        parent = self.parent
        seen_ids = {self.pk} if self.pk else set()
        while parent:
            if parent.pk in seen_ids:
                raise ValidationError({'parent': 'Kategori üst ağacında döngü oluşamaz.'})
            seen_ids.add(parent.pk)
            parent = parent.parent


class Product(models.Model):
    """Product listed by a vendor under a category."""

    vendor = models.ForeignKey(
        'vendors.Vendor',
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Satıcı',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Kategori',
    )
    name = models.CharField(max_length=300, verbose_name='Ürün Adı')
    slug = models.SlugField(max_length=300, unique=True)
    description = models.TextField(blank=True, verbose_name='Açıklama')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Fiyat',
    )
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='İndirimli Fiyat',
    )
    stock = models.PositiveIntegerField(default=0, verbose_name='Stok')
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name='Ürün Görseli',
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    is_approved = models.BooleanField(default=False, verbose_name='Onaylı')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ürün'
        verbose_name_plural = 'Ürünler'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.name

    @property
    def effective_price(self) -> Decimal:
        """Return discount price if set, otherwise regular price."""
        if self.discount_price is not None:
            return self.discount_price
        return self.price

    @property
    def is_on_sale(self) -> bool:
        """Return True if the product has a discount price and it's less than regular price."""
        return self.discount_price is not None and self.discount_price < self.price


class ProductMedia(models.Model):
    """Additional images and videos shown on the product detail page."""

    class MediaType(models.TextChoices):
        IMAGE = 'image', 'Fotoğraf'
        VIDEO = 'video', 'Video'

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='media',
        verbose_name='Ürün',
    )
    media_type = models.CharField(
        max_length=12,
        choices=MediaType.choices,
        default=MediaType.IMAGE,
        verbose_name='Medya Tipi',
    )
    file = models.FileField(
        upload_to='product_media/',
        verbose_name='Dosya',
    )
    title = models.CharField(max_length=140, blank=True, verbose_name='Başlık')
    display_order = models.PositiveIntegerField(default=0, verbose_name='Sıra')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ürün Medyası'
        verbose_name_plural = 'Ürün Medyaları'
        ordering = ['display_order', 'id']

    def __str__(self) -> str:
        return f'{self.product.name} - {self.get_media_type_display()}'

    @property
    def is_image(self) -> bool:
        return self.media_type == self.MediaType.IMAGE

    @property
    def is_video(self) -> bool:
        return self.media_type == self.MediaType.VIDEO


class ProductVariant(models.Model):
    """Sellable option for a product such as color, storage, size, or bundle."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name='Ürün',
    )
    option_name = models.CharField(max_length=80, verbose_name='Seçenek Adı')
    option_value = models.CharField(max_length=120, verbose_name='Seçenek Değeri')
    sku = models.CharField(max_length=80, blank=True, verbose_name='Stok Kodu')
    price_delta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Fiyat Farkı',
        help_text='Ana ürün fiyatına eklenecek tutar. Negatif değer indirim gibi çalışır.',
    )
    stock = models.PositiveIntegerField(default=0, verbose_name='Varyant Stok')
    display_order = models.PositiveIntegerField(default=0, verbose_name='Sıra')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ürün Varyantı'
        verbose_name_plural = 'Ürün Varyantları'
        ordering = ['display_order', 'option_name', 'option_value']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'option_name', 'option_value'],
                name='unique_product_variant_option',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.product.name} - {self.option_name}: {self.option_value}'

    @property
    def label(self) -> str:
        return f'{self.option_name}: {self.option_value}'

    @property
    def effective_price(self) -> Decimal:
        price = self.product.effective_price + self.price_delta
        return max(price, Decimal('0'))


class FavoriteProduct(models.Model):
    """Product saved to a customer's favorites list."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_products',
        verbose_name='Kullanıcı',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Ürün',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Favori Ürün'
        verbose_name_plural = 'Favori Ürünler'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_favorite_product_per_user',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.user} - {self.product.name}'


class CompareProduct(models.Model):
    """Product selected by a customer for side-by-side comparison."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='compare_products',
        verbose_name='Kullanıcı',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='compared_by',
        verbose_name='Ürün',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Karşılaştırma Ürünü'
        verbose_name_plural = 'Karşılaştırma Ürünleri'
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_compare_product_per_user',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.user} - {self.product.name}'


class HeroCampaign(models.Model):
    """Homepage campaign shown in the scrolling promotion board."""

    title = models.CharField(max_length=160, verbose_name='Manşet')
    subtitle = models.CharField(
        max_length=240,
        blank=True,
        verbose_name='Kampanya Metni',
    )
    badge_text = models.CharField(
        max_length=60,
        blank=True,
        verbose_name='Etiket',
        help_text='Örn: Hafta sonu fırsatı, Yeni sezon, %20 indirim',
    )
    image = models.ImageField(
        upload_to='campaigns/',
        blank=True,
        null=True,
        verbose_name='Kampanya Görseli',
    )
    link_text = models.CharField(
        max_length=60,
        blank=True,
        default='İncele',
        verbose_name='Buton Metni',
    )
    link_url = models.CharField(
        max_length=300,
        blank=True,
        verbose_name='Bağlantı',
        help_text='Site içi veya dış bağlantı. Boş bırakılırsa ana sayfaya gider.',
    )
    display_order = models.PositiveIntegerField(default=0, verbose_name='Sıra')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    starts_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Başlangıç Tarihi',
    )
    ends_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Bitiş Tarihi',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ana Sayfa Reklam Panosu'
        verbose_name_plural = 'Ana Sayfa Reklam Panoları'
        ordering = ['display_order', '-created_at']

    def __str__(self) -> str:
        return self.title

    @property
    def is_live(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        return True


class HomeFeaturedProduct(models.Model):
    """Product selected by admins for the homepage showcase."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='homepage_slots',
        verbose_name='Ürün',
    )
    title_override = models.CharField(
        max_length=180,
        blank=True,
        verbose_name='Vitrin Başlığı',
        help_text='Boş bırakılırsa ürün adı kullanılır.',
    )
    display_order = models.PositiveIntegerField(default=0, verbose_name='Sıra')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ana Sayfa Vitrin Ürünü'
        verbose_name_plural = 'Ana Sayfa Vitrin Ürünleri'
        ordering = ['display_order', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                name='unique_home_featured_product',
            ),
        ]

    def __str__(self) -> str:
        return self.title_override or self.product.name


class HomeFeaturedCategory(models.Model):
    """Category selected by admins for the homepage quick access area."""

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='homepage_slots',
        verbose_name='Kategori',
    )
    label_override = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Görünen Ad',
        help_text='Boş bırakılırsa kategori adı kullanılır.',
    )
    display_order = models.PositiveIntegerField(default=0, verbose_name='Sıra')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ana Sayfa Sık Kullanılan Kategori'
        verbose_name_plural = 'Ana Sayfa Sık Kullanılan Kategoriler'
        ordering = ['display_order', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['category'],
                name='unique_home_featured_category',
            ),
        ]

    def __str__(self) -> str:
        return self.label_override or self.category.name


class Cart(models.Model):
    """Shopping cart tied to either a user or a session."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts',
        verbose_name='Kullanıcı',
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name='Session Key',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sepet'
        verbose_name_plural = 'Sepetler'

    def __str__(self) -> str:
        return f'Sepet #{self.pk}'

    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self) -> Decimal:
        return sum(item.line_total for item in self.items.all())


class CartItem(models.Model):
    """Individual item in a shopping cart."""

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Sepet',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Ürün',
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cart_items',
        verbose_name='Varyant',
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='Adet')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sepet Ürünü'
        verbose_name_plural = 'Sepet Ürünleri'
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product', 'variant'],
                name='unique_cart_product_variant',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.product.name} x{self.quantity}'

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity

    @property
    def unit_price(self) -> Decimal:
        if self.variant_id:
            return self.variant.effective_price
        return self.product.effective_price

    @property
    def available_stock(self) -> int:
        if self.variant_id:
            return self.variant.stock
        return self.product.stock


class CustomerAddress(models.Model):
    """Saved shipping address for a customer."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_addresses',
        verbose_name='Kullanıcı',
    )
    title = models.CharField(max_length=80, default='Adresim', verbose_name='Adres Başlığı')
    recipient_name = models.CharField(max_length=160, verbose_name='Alıcı Ad Soyad')
    phone = models.CharField(max_length=20, verbose_name='Kargo Telefonu')
    city = models.CharField(max_length=80, verbose_name='Şehir')
    district = models.CharField(max_length=80, blank=True, verbose_name='İlçe')
    address_line = models.TextField(verbose_name='Açık Adres')
    postal_code = models.CharField(max_length=12, blank=True, verbose_name='Posta Kodu')
    is_default = models.BooleanField(default=False, verbose_name='Varsayılan')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Kayıtlı Adres'
        verbose_name_plural = 'Kayıtlı Adresler'
        ordering = ['-is_default', '-updated_at']

    def __str__(self) -> str:
        return f'{self.title} - {self.user}'

    @property
    def formatted_address(self) -> str:
        parts = [self.address_line, self.district, self.city, self.postal_code]
        return ', '.join(part for part in parts if part)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            CustomerAddress.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)


class CardInstallmentGroup(models.Model):
    """Admin-defined card group used when calculating installment options."""

    name = models.CharField(max_length=120, verbose_name='Kart Grubu Adı')
    slug = models.SlugField(max_length=140, unique=True, verbose_name='Kod')
    description = models.CharField(max_length=240, blank=True, verbose_name='Açıklama')
    default_max_installments = models.PositiveSmallIntegerField(default=1, verbose_name='Varsayılan En Fazla Taksit')
    is_default_for_unknown_cards = models.BooleanField(default=False, verbose_name='Tanımsız Kartlar İçin Varsayılan')
    display_order = models.PositiveIntegerField(default=0, verbose_name='Sıra')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kart Taksit Grubu'
        verbose_name_plural = 'Kart Taksit Grupları'
        ordering = ['display_order', 'name']

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default_for_unknown_cards:
            CardInstallmentGroup.objects.filter(is_default_for_unknown_cards=True).exclude(pk=self.pk).update(
                is_default_for_unknown_cards=False,
            )


class CardBinPrefix(models.Model):
    """Bank/card BIN prefix mapped to an installment group by admins."""

    card_group = models.ForeignKey(
        CardInstallmentGroup,
        on_delete=models.CASCADE,
        related_name='bin_prefixes',
        verbose_name='Taksit Grubu',
    )
    bank_name = models.CharField(max_length=120, verbose_name='Banka/Kart Adı')
    prefix = models.CharField(
        max_length=8,
        unique=True,
        verbose_name='Kart İlk 6-8 Hane',
        help_text='Kart numarasının ilk 6, 7 veya 8 hanesi. Örn: 454360 veya 45436012',
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kart BIN Tanımı'
        verbose_name_plural = 'Kart BIN Tanımları'
        ordering = ['bank_name', '-prefix']

    def __str__(self) -> str:
        return f'{self.bank_name} - {self.prefix}'

    def clean(self):
        super().clean()
        if self.prefix and (not self.prefix.isdigit() or len(self.prefix) not in {6, 7, 8}):
            raise ValidationError({'prefix': 'BIN değeri sadece rakamlardan oluşmalı ve 6-8 hane olmalıdır.'})


class CategoryInstallmentRule(models.Model):
    """Maximum installment rule for a category and card group."""

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='installment_rules',
        verbose_name='Kategori',
    )
    card_group = models.ForeignKey(
        CardInstallmentGroup,
        on_delete=models.CASCADE,
        related_name='category_rules',
        verbose_name='Kart Grubu',
    )
    max_installments = models.PositiveSmallIntegerField(default=1, verbose_name='En Fazla Taksit')
    min_cart_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Minimum Sepet Tutarı',
        help_text='Bu tutarın altındaki sepetlerde kural uygulanmaz.',
    )
    priority = models.PositiveSmallIntegerField(default=0, verbose_name='Öncelik')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kategori Taksit Kuralı'
        verbose_name_plural = 'Kategori Taksit Kuralları'
        ordering = ['category__name', 'card_group__display_order', '-priority']

    def __str__(self) -> str:
        return f'{self.category} / {self.card_group} - {self.max_installments} taksit'


class InstallmentRate(models.Model):
    """Finance rate for a specific installment count within a category rule."""

    rule = models.ForeignKey(
        CategoryInstallmentRule,
        on_delete=models.CASCADE,
        related_name='rates',
        verbose_name='Taksit Kuralı',
    )
    installment_count = models.PositiveSmallIntegerField(verbose_name='Taksit Sayısı')
    interest_rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Vade Farkı (%)',
        help_text='Örn: 7.50 yazılırsa toplam tutara yüzde 7,5 eklenir.',
    )

    class Meta:
        verbose_name = 'Taksit Vade Oranı'
        verbose_name_plural = 'Taksit Vade Oranları'
        ordering = ['installment_count']
        constraints = [
            models.UniqueConstraint(
                fields=['rule', 'installment_count'],
                name='unique_installment_rate_per_rule',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.installment_count} taksit / %{self.interest_rate_percent}'


class Order(models.Model):
    """Customer order."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Beklemede'
        CONFIRMED = 'confirmed', 'Onaylandı'
        SHIPPED = 'shipped', 'Kargoda'
        DELIVERED = 'delivered', 'Teslim Edildi'
        CANCELLED = 'cancelled', 'İptal Edildi'

    class BillingType(models.TextChoices):
        INDIVIDUAL = 'individual', 'Bireysel'
        CORPORATE = 'corporate', 'Kurumsal'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Kullanıcı',
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Toplam Tutar',
    )
    installment_base_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Taksit Öncesi Tutar',
    )
    installment_card_group = models.ForeignKey(
        CardInstallmentGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Taksit Kart Grubu',
    )
    installment_card_group_name = models.CharField(max_length=120, blank=True, verbose_name='Kart Grubu Adı')
    installment_count = models.PositiveSmallIntegerField(default=1, verbose_name='Taksit Sayısı')
    installment_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Vade Farkı (%)')
    installment_monthly_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Aylık Tutar')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Durum',
    )
    public_token = models.CharField(max_length=40, unique=True, blank=True, null=True, verbose_name='Bilgilendirme Token')
    shipping_address_ref = models.ForeignKey(
        CustomerAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Kayıtlı Adres',
    )
    shipping_recipient_name = models.CharField(max_length=160, blank=True, verbose_name='Alıcı Ad Soyad')
    shipping_city = models.CharField(max_length=80, blank=True, verbose_name='Teslimat Şehri')
    shipping_district = models.CharField(max_length=80, blank=True, verbose_name='Teslimat İlçesi')
    shipping_postal_code = models.CharField(max_length=12, blank=True, verbose_name='Posta Kodu')
    shipping_address = models.TextField(verbose_name='Teslimat Adresi')
    phone = models.CharField(max_length=20, verbose_name='Telefon')
    billing_type = models.CharField(
        max_length=20,
        choices=BillingType.choices,
        default=BillingType.INDIVIDUAL,
        verbose_name='Fatura Tipi',
    )
    billing_full_name = models.CharField(max_length=180, blank=True, verbose_name='Fatura Ad Soyad')
    billing_company_name = models.CharField(max_length=200, blank=True, verbose_name='Firma Ünvanı')
    billing_tax_office = models.CharField(max_length=120, blank=True, verbose_name='Vergi Dairesi')
    billing_tax_number = models.CharField(max_length=40, blank=True, verbose_name='Vergi/TCKN No')
    billing_email = models.EmailField(blank=True, verbose_name='Fatura E-postası')
    billing_phone = models.CharField(max_length=20, blank=True, verbose_name='Fatura Telefonu')
    billing_address = models.TextField(blank=True, verbose_name='Fatura Adresi')
    note = models.TextField(blank=True, verbose_name='Not')
    coupon = models.ForeignKey(
        'Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Kupon',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Sipariş'
        verbose_name_plural = 'Siparişler'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Sipariş #{self.pk}'

    def save(self, *args, **kwargs):
        if not self.public_token:
            self.public_token = get_random_string(32)
        super().save(*args, **kwargs)


class OrderPhoneNotification(models.Model):
    """Phone/SMS notification queue item for a placed order."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Gönderim Bekliyor'
        SENT = 'sent', 'Gönderildi'
        FAILED = 'failed', 'Başarısız'

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='phone_notifications',
        verbose_name='Sipariş',
    )
    phone = models.CharField(max_length=20, verbose_name='Telefon')
    message = models.TextField(verbose_name='Mesaj')
    tracking_link = models.URLField(max_length=500, verbose_name='Bilgilendirme Linki')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name='Durum')
    provider_response = models.TextField(blank=True, verbose_name='Sağlayıcı Yanıtı')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Telefon Bilgilendirme Kaydı'
        verbose_name_plural = 'Telefon Bilgilendirme Kayıtları'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'Sipariş #{self.order_id} - {self.phone}'


class OrderServiceRequest(models.Model):
    """Customer cancellation or return request for an order."""

    class RequestType(models.TextChoices):
        CANCEL = 'cancel', 'İptal Talebi'
        RETURN = 'return', 'İade Talebi'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Beklemede'
        APPROVED = 'approved', 'Onaylandı'
        REJECTED = 'rejected', 'Reddedildi'
        COMPLETED = 'completed', 'Tamamlandı'

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='service_requests',
        verbose_name='Sipariş',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='order_service_requests',
        verbose_name='Kullanıcı',
    )
    request_type = models.CharField(
        max_length=12,
        choices=RequestType.choices,
        verbose_name='Talep Tipi',
    )
    reason = models.CharField(max_length=160, verbose_name='Sebep')
    description = models.TextField(blank=True, verbose_name='Açıklama')
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Durum',
    )
    admin_note = models.TextField(blank=True, verbose_name='Yönetici Notu')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'İade/İptal Talebi'
        verbose_name_plural = 'İade/İptal Talepleri'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'request_type'],
                name='unique_order_service_request_type',
            ),
        ]

    def __str__(self) -> str:
        return f'Sipariş #{self.order_id} - {self.get_request_type_display()}'


class Notification(models.Model):
    """In-app notification shown in the customer/seller notification center."""

    class NotificationType(models.TextChoices):
        ORDER = 'order', 'Sipariş'
        SHIPPING = 'shipping', 'Kargo'
        SUPPORT = 'support', 'Destek'
        QUESTION = 'question', 'Soru-Cevap'
        REVIEW = 'review', 'Yorum'
        SYSTEM = 'system', 'Sistem'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Alıcı',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        verbose_name='İşlemi Yapan',
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        verbose_name='Bildirim Tipi',
    )
    title = models.CharField(max_length=160, verbose_name='Başlık')
    message = models.TextField(blank=True, verbose_name='Mesaj')
    link_url = models.CharField(max_length=320, blank=True, verbose_name='Bağlantı')
    read_at = models.DateTimeField(blank=True, null=True, verbose_name='Okunma Zamanı')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma Zamanı')

    class Meta:
        verbose_name = 'Bildirim'
        verbose_name_plural = 'Bildirimler'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'read_at', '-created_at']),
        ]

    def __str__(self) -> str:
        return f'{self.recipient} - {self.title}'

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])


class SupportTicket(models.Model):
    """Customer support/return ticket with chat and AI-assisted guidance."""

    class TicketType(models.TextChoices):
        GENERAL = 'general', 'Genel Destek'
        RETURN = 'return', 'İade'
        CANCEL = 'cancel', 'İptal'
        SHIPPING = 'shipping', 'Kargo'
        BILLING = 'billing', 'Fatura/Ödeme'
        DAMAGED = 'damaged', 'Hasarlı Ürün'

    class Status(models.TextChoices):
        OPEN = 'open', 'Açık'
        WAITING_CUSTOMER = 'waiting_customer', 'Müşteri Yanıtı Bekleniyor'
        WAITING_SUPPORT = 'waiting_support', 'Destek Yanıtı Bekleniyor'
        RESOLVED = 'resolved', 'Çözüldü'
        CLOSED = 'closed', 'Kapatıldı'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets',
        verbose_name='Müşteri',
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets',
        verbose_name='Sipariş',
    )
    service_request = models.OneToOneField(
        OrderServiceRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_ticket',
        verbose_name='İade/İptal Talebi',
    )
    ticket_type = models.CharField(
        max_length=20,
        choices=TicketType.choices,
        default=TicketType.GENERAL,
        verbose_name='Talep Tipi',
    )
    subject = models.CharField(max_length=180, verbose_name='Konu')
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.OPEN,
        verbose_name='Durum',
    )
    ai_summary = models.TextField(blank=True, verbose_name='AI Özet')
    ai_suggestion = models.TextField(blank=True, verbose_name='AI Önerisi')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma Zamanı')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Güncellenme Zamanı')

    class Meta:
        verbose_name = 'Destek Talebi'
        verbose_name_plural = 'Destek Talepleri'
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return f'#{self.id} - {self.subject}'


class SupportTicketMessage(models.Model):
    """Message inside a support ticket conversation."""

    class SenderType(models.TextChoices):
        CUSTOMER = 'customer', 'Müşteri'
        SUPPORT = 'support', 'Destek'
        VENDOR = 'vendor', 'Satıcı'
        AI = 'ai', 'AI Destek'
        SYSTEM = 'system', 'Sistem'

    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Destek Talebi',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_messages',
        verbose_name='Yazan',
    )
    sender_type = models.CharField(max_length=16, choices=SenderType.choices, verbose_name='Gönderen Tipi')
    message = models.TextField(verbose_name='Mesaj')
    is_internal = models.BooleanField(default=False, verbose_name='İç Not')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma Zamanı')

    class Meta:
        verbose_name = 'Destek Mesajı'
        verbose_name_plural = 'Destek Mesajları'
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'{self.ticket_id} - {self.get_sender_type_display()}'


class ShippingCompany(models.Model):
    """Shipping company used for order tracking."""

    name = models.CharField(max_length=120, unique=True, verbose_name='Kargo Firması')
    code = models.CharField(max_length=20, unique=True, verbose_name='Firma Kodu')
    support_phone = models.CharField(max_length=20, blank=True, verbose_name='Destek Telefonu')
    tracking_url = models.URLField(blank=True, verbose_name='Takip URL')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kargo Firması'
        verbose_name_plural = 'Kargo Firmaları'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class CargoStation(models.Model):
    """Station/hub for a shipping company's delivery flow."""

    company = models.ForeignKey(
        ShippingCompany,
        on_delete=models.CASCADE,
        related_name='stations',
        verbose_name='Kargo Firması',
    )
    name = models.CharField(max_length=160, verbose_name='İstasyon Adı')
    city = models.CharField(max_length=80, verbose_name='Şehir')
    code = models.CharField(max_length=24, verbose_name='İstasyon Kodu')
    address = models.CharField(max_length=260, blank=True, verbose_name='Adres')
    display_order = models.PositiveIntegerField(default=0, verbose_name='Sıra')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')

    class Meta:
        verbose_name = 'Kargo İstasyonu'
        verbose_name_plural = 'Kargo İstasyonları'
        ordering = ['display_order', 'city', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'code'],
                name='unique_company_station_code',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.company.name} - {self.name}'


class Shipment(models.Model):
    """Tracking record connected to a customer order."""

    class Status(models.TextChoices):
        CREATED = 'created', 'Kargo Kaydı Oluşturuldu'
        PICKED_UP = 'picked_up', 'Satıcıdan Alındı'
        IN_TRANSIT = 'in_transit', 'Transfer Sürecinde'
        AT_STATION = 'at_station', 'İstasyonda'
        OUT_FOR_DELIVERY = 'out_for_delivery', 'Dağıtıma Çıktı'
        DELIVERED = 'delivered', 'Teslim Edildi'
        EXCEPTION = 'exception', 'Sorun Bildirildi'
        RETURNED = 'returned', 'İade Sürecinde'

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='shipment',
        verbose_name='Sipariş',
    )
    company = models.ForeignKey(
        ShippingCompany,
        on_delete=models.PROTECT,
        related_name='shipments',
        verbose_name='Kargo Firması',
    )
    tracking_number = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
        verbose_name='Takip Numarası',
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.CREATED,
        verbose_name='Kargo Durumu',
    )
    current_station = models.ForeignKey(
        CargoStation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_shipments',
        verbose_name='Mevcut İstasyon',
    )
    estimated_delivery = models.DateField(
        blank=True,
        null=True,
        verbose_name='Tahmini Teslimat',
    )
    note = models.CharField(max_length=240, blank=True, verbose_name='Kargo Notu')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Kargo Takip Kaydı'
        verbose_name_plural = 'Kargo Takip Kayıtları'
        ordering = ['-updated_at']

    def __str__(self) -> str:
        return f'{self.tracking_number or "Takip Yok"} - Sipariş #{self.order_id}'

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            prefix = self.company.code if self.company_id and self.company.code else 'CJ'
            today = timezone.now().strftime('%Y%m%d')
            self.tracking_number = f'{prefix}{today}{get_random_string(6).upper()}'
        super().save(*args, **kwargs)


class ShipmentEvent(models.Model):
    """Movement history for a shipment."""

    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name='Kargo Takip Kaydı',
    )
    station = models.ForeignKey(
        CargoStation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='İstasyon',
    )
    status = models.CharField(
        max_length=24,
        choices=Shipment.Status.choices,
        verbose_name='Durum',
    )
    description = models.CharField(max_length=240, blank=True, verbose_name='Açıklama')
    happened_at = models.DateTimeField(default=timezone.now, verbose_name='İşlem Zamanı')

    class Meta:
        verbose_name = 'Kargo Hareketi'
        verbose_name_plural = 'Kargo Hareketleri'
        ordering = ['-happened_at']

    def __str__(self) -> str:
        return f'{self.get_status_display()} - {self.happened_at:%d.%m.%Y %H:%M}'


class ProductQuestion(models.Model):
    """Customer question and seller/admin answer shown on product detail pages."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name='Ürün',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='product_questions',
        verbose_name='Soran Kullanıcı',
    )
    question = models.TextField(verbose_name='Soru')
    answer = models.TextField(blank=True, verbose_name='Cevap')
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='answered_product_questions',
        verbose_name='Cevaplayan',
    )
    is_public = models.BooleanField(default=True, verbose_name='Yayında')
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Ürün Soru-Cevap'
        verbose_name_plural = 'Ürün Soru-Cevapları'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.product.name} - {self.user}'

    def save(self, *args, **kwargs):
        if self.answer and not self.answered_at:
            self.answered_at = timezone.now()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Individual item within an order, snapshot of product at purchase time."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Sipariş',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Ürün',
    )
    product_name = models.CharField(max_length=300, verbose_name='Ürün Adı')
    variant_name = models.CharField(max_length=220, blank=True, verbose_name='Varyant')
    variant_sku = models.CharField(max_length=80, blank=True, verbose_name='Varyant Stok Kodu')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Birim Fiyat',
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='Adet')

    class Meta:
        verbose_name = 'Sipariş Kalemi'
        verbose_name_plural = 'Sipariş Kalemleri'

    def __str__(self) -> str:
        return f'{self.product_name} x{self.quantity}'

    @property
    def line_total(self) -> Decimal:
        return self.price * self.quantity


class Coupon(models.Model):
    """Discount coupon with usage tracking."""

    code = models.CharField(max_length=50, unique=True, verbose_name='Kupon Kodu')
    discount_percent = models.PositiveIntegerField(verbose_name='İndirim Yüzdesi')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    valid_from = models.DateTimeField(verbose_name='Geçerlilik Başlangıcı')
    valid_until = models.DateTimeField(verbose_name='Geçerlilik Bitişi')
    times_used = models.PositiveIntegerField(default=0, verbose_name='Kullanım Sayısı')
    usage_limit = models.PositiveIntegerField(
        default=100,
        verbose_name='Kullanım Limiti',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kupon'
        verbose_name_plural = 'Kuponlar'

    def __str__(self) -> str:
        return self.code

    @property
    def is_valid(self) -> bool:
        now = timezone.now()
        return (
            self.is_active
            and self.valid_from <= now <= self.valid_until
            and self.times_used < self.usage_limit
        )


class ProductReview(models.Model):
    """Customer review displayed on a product detail page."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Ürün',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='product_reviews',
        verbose_name='Kullanıcı',
    )
    rating = models.PositiveSmallIntegerField(default=5, verbose_name='Puan')
    title = models.CharField(max_length=120, blank=True, verbose_name='Başlık')
    comment = models.TextField(verbose_name='Yorum')
    is_approved = models.BooleanField(default=True, verbose_name='Yayında')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ürün Yorumu'
        verbose_name_plural = 'Ürün Yorumları'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'user'],
                name='unique_product_review_per_user',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.product.name} - {self.user}'


class SiteFeedback(models.Model):
    """General customer feedback submitted from the site."""

    class Topic(models.TextChoices):
        GENERAL = 'general', 'Genel'
        ORDER = 'order', 'Sipariş'
        PRODUCT = 'product', 'Ürün'
        TECHNICAL = 'technical', 'Teknik'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_feedbacks',
        verbose_name='Kullanıcı',
    )
    name = models.CharField(max_length=140, verbose_name='Ad Soyad')
    email = models.EmailField(verbose_name='E-posta')
    topic = models.CharField(max_length=24, choices=Topic.choices, default=Topic.GENERAL, verbose_name='Konu')
    message = models.TextField(verbose_name='Mesaj')
    is_resolved = models.BooleanField(default=False, verbose_name='Çözüldü')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Geri Bildirim'
        verbose_name_plural = 'Geri Bildirimler'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.get_topic_display()} - {self.email}'
