from django.conf import settings
from django.db import models


class Vendor(models.Model):
    """Approved vendor profile linked to a user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_profile',
        verbose_name='Kullanıcı',
    )
    store_name = models.CharField(max_length=200, verbose_name='Mağaza Adı')
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, verbose_name='Açıklama')
    logo = models.ImageField(
        upload_to='vendors/logos/',
        blank=True,
        null=True,
        verbose_name='Logo',
    )
    tax_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Vergi Numarası',
    )
    phone = models.CharField(max_length=15, blank=True, verbose_name='Telefon')
    is_approved = models.BooleanField(default=False, verbose_name='Onaylı')
    product_limit = models.PositiveIntegerField(
        default=50,
        verbose_name='Ürün Limiti',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Satıcı'
        verbose_name_plural = 'Satıcılar'

    def __str__(self) -> str:
        return self.store_name

    @property
    def product_count(self) -> int:
        return self.products.count()

    @property
    def can_add_product(self) -> bool:
        return self.product_count < self.product_limit


class VendorApplication(models.Model):
    """Application submitted by a user to become a vendor."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Beklemede'
        APPROVED = 'approved', 'Onaylandı'
        REJECTED = 'rejected', 'Reddedildi'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_applications',
        verbose_name='Kullanıcı',
    )
    company_name = models.CharField(max_length=200, verbose_name='Şirket Adı')
    tax_number = models.CharField(max_length=20, verbose_name='Vergi Numarası')
    phone = models.CharField(max_length=15, verbose_name='Telefon')
    description = models.TextField(verbose_name='Açıklama')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Durum',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Satıcı Başvurusu'
        verbose_name_plural = 'Satıcı Başvuruları'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.company_name} - {self.get_status_display()}'
