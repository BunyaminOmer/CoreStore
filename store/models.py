from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


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
    quantity = models.PositiveIntegerField(default=1, verbose_name='Adet')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sepet Ürünü'
        verbose_name_plural = 'Sepet Ürünleri'
        unique_together = ('cart', 'product')

    def __str__(self) -> str:
        return f'{self.product.name} x{self.quantity}'

    @property
    def line_total(self) -> Decimal:
        return self.product.effective_price * self.quantity


class Order(models.Model):
    """Customer order."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Beklemede'
        CONFIRMED = 'confirmed', 'Onaylandı'
        SHIPPED = 'shipped', 'Kargoda'
        DELIVERED = 'delivered', 'Teslim Edildi'
        CANCELLED = 'cancelled', 'İptal Edildi'

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
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Durum',
    )
    shipping_address = models.TextField(verbose_name='Teslimat Adresi')
    phone = models.CharField(max_length=15, verbose_name='Telefon')
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
