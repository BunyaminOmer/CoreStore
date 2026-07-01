from django.conf import settings
from django.db import models
from django.utils import timezone


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

    @property
    def has_business_profile(self) -> bool:
        return hasattr(self, 'business_profile') and self.business_profile.is_complete

    @property
    def active_subscription(self):
        return self.subscriptions.filter(
            status=VendorSubscription.Status.ACTIVE,
            starts_at__lte=timezone.now(),
            ends_at__gte=timezone.now(),
        ).select_related('plan').first()


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


class BusinessProfile(models.Model):
    """Detailed legal/business profile required before paid seller tools."""

    vendor = models.OneToOneField(
        Vendor,
        on_delete=models.CASCADE,
        related_name='business_profile',
        verbose_name='Satıcı',
    )
    legal_name = models.CharField(max_length=220, verbose_name='Resmi Ünvan')
    trade_name = models.CharField(max_length=220, blank=True, verbose_name='Ticari Ünvan / Marka')
    tax_office = models.CharField(max_length=120, verbose_name='Vergi Dairesi')
    tax_number = models.CharField(max_length=20, verbose_name='Vergi / TCKN No')
    mersis_no = models.CharField(max_length=32, blank=True, verbose_name='MERSİS No')
    contact_person = models.CharField(max_length=160, verbose_name='Yetkili Kişi')
    phone = models.CharField(max_length=20, verbose_name='Telefon')
    billing_email = models.EmailField(verbose_name='Fatura E-postası')
    city = models.CharField(max_length=80, verbose_name='Şehir')
    district = models.CharField(max_length=80, blank=True, verbose_name='İlçe')
    address = models.TextField(verbose_name='İşletme Adresi')
    iban = models.CharField(max_length=34, blank=True, verbose_name='IBAN')
    website = models.URLField(blank=True, verbose_name='Web Sitesi')
    is_verified = models.BooleanField(default=False, verbose_name='Yönetici Onaylı')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'İşletme Profili'
        verbose_name_plural = 'İşletme Profilleri'

    def __str__(self) -> str:
        return self.legal_name

    @property
    def is_complete(self) -> bool:
        required = [
            self.legal_name,
            self.tax_office,
            self.tax_number,
            self.contact_person,
            self.phone,
            self.billing_email,
            self.city,
            self.address,
        ]
        return all(str(value).strip() for value in required)


class VendorSubscriptionPlan(models.Model):
    """Monthly seller package with limits and monetization perks."""

    name = models.CharField(max_length=120, verbose_name='Paket Adı')
    slug = models.SlugField(max_length=140, unique=True)
    description = models.CharField(max_length=260, blank=True, verbose_name='Açıklama')
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Aylık Ücret')
    product_limit = models.PositiveIntegerField(default=20, verbose_name='Ürün Limiti')
    sponsored_product_quota = models.PositiveIntegerField(default=0, verbose_name='Sponsorlu Ürün Hakkı')
    ad_credit = models.PositiveIntegerField(default=0, verbose_name='Reklam Kredisi')
    support_level = models.CharField(max_length=120, default='Standart destek', verbose_name='Destek Seviyesi')
    is_featured = models.BooleanField(default=False, verbose_name='Öne Çıkan')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    display_order = models.PositiveIntegerField(default=0, verbose_name='Sıra')

    class Meta:
        verbose_name = 'Satıcı Abonelik Paketi'
        verbose_name_plural = 'Satıcı Abonelik Paketleri'
        ordering = ['display_order', 'monthly_price']

    def __str__(self) -> str:
        return self.name


class VendorSubscription(models.Model):
    """A vendor's selected seller package."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Ödeme/Onay Bekliyor'
        ACTIVE = 'active', 'Aktif'
        EXPIRED = 'expired', 'Süresi Doldu'
        CANCELLED = 'cancelled', 'İptal'

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Satıcı',
    )
    plan = models.ForeignKey(
        VendorSubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        verbose_name='Paket',
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, verbose_name='Durum')
    starts_at = models.DateTimeField(default=timezone.now, verbose_name='Başlangıç')
    ends_at = models.DateTimeField(verbose_name='Bitiş')
    auto_renew = models.BooleanField(default=False, verbose_name='Otomatik Yenile')
    payment_note = models.CharField(max_length=240, blank=True, verbose_name='Ödeme Notu')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Satıcı Aboneliği'
        verbose_name_plural = 'Satıcı Abonelikleri'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.vendor.store_name} - {self.plan.name}'

    @property
    def is_active_now(self) -> bool:
        now = timezone.now()
        return self.status == self.Status.ACTIVE and self.starts_at <= now <= self.ends_at


class SponsoredProductCampaign(models.Model):
    """Vendor request to promote a product in key storefront placements."""

    class Placement(models.TextChoices):
        HOME = 'home', 'Ana Sayfa'
        CATEGORY = 'category', 'Kategori Sayfası'
        SEARCH = 'search', 'Arama Sonuçları'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Taslak'
        PENDING = 'pending', 'Onay Bekliyor'
        ACTIVE = 'active', 'Yayında'
        PAUSED = 'paused', 'Duraklatıldı'
        REJECTED = 'rejected', 'Reddedildi'
        ENDED = 'ended', 'Bitti'

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='sponsored_campaigns', verbose_name='Satıcı')
    product = models.ForeignKey('store.Product', on_delete=models.CASCADE, related_name='sponsored_campaigns', verbose_name='Ürün')
    placement = models.CharField(max_length=16, choices=Placement.choices, default=Placement.HOME, verbose_name='Yerleşim')
    title = models.CharField(max_length=160, blank=True, verbose_name='Kampanya Başlığı')
    daily_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Günlük Bütçe')
    starts_at = models.DateTimeField(default=timezone.now, verbose_name='Başlangıç')
    ends_at = models.DateTimeField(verbose_name='Bitiş')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, verbose_name='Durum')
    admin_note = models.CharField(max_length=240, blank=True, verbose_name='Yönetici Notu')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Sponsorlu Ürün Kampanyası'
        verbose_name_plural = 'Sponsorlu Ürün Kampanyaları'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.vendor.store_name} - {self.product.name}'

    @property
    def is_live(self) -> bool:
        now = timezone.now()
        return self.status == self.Status.ACTIVE and self.starts_at <= now <= self.ends_at


class AdPlacementRequest(models.Model):
    """Vendor request for banner/advertising placements."""

    class Placement(models.TextChoices):
        HOME_BOARD = 'home_board', 'Ana Sayfa Reklam Panosu'
        CATEGORY_TOP = 'category_top', 'Kategori Üst Banner'
        SEARCH_TOP = 'search_top', 'Arama Üst Banner'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Onay Bekliyor'
        ACTIVE = 'active', 'Yayında'
        REJECTED = 'rejected', 'Reddedildi'
        ENDED = 'ended', 'Bitti'

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='ad_requests', verbose_name='Satıcı')
    placement = models.CharField(max_length=20, choices=Placement.choices, verbose_name='Reklam Alanı')
    title = models.CharField(max_length=160, verbose_name='Başlık')
    description = models.CharField(max_length=240, blank=True, verbose_name='Kısa Açıklama')
    image = models.ImageField(upload_to='vendor_ads/', blank=True, null=True, verbose_name='Görsel')
    target_url = models.CharField(max_length=300, blank=True, verbose_name='Hedef Link')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Tutar')
    starts_at = models.DateTimeField(default=timezone.now, verbose_name='Başlangıç')
    ends_at = models.DateTimeField(verbose_name='Bitiş')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, verbose_name='Durum')
    admin_note = models.CharField(max_length=240, blank=True, verbose_name='Yönetici Notu')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reklam Alanı Talebi'
        verbose_name_plural = 'Reklam Alanı Talepleri'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.vendor.store_name} - {self.title}'

    @property
    def is_live(self) -> bool:
        now = timezone.now()
        return self.status == self.Status.ACTIVE and self.starts_at <= now <= self.ends_at


class SupportServicePackage(models.Model):
    """Paid service/support package vendors can request."""

    class ServiceType(models.TextChoices):
        SETUP = 'setup', 'Mağaza Kurulum'
        PRODUCT_UPLOAD = 'product_upload', 'Ürün Yükleme'
        DESIGN = 'design', 'Görsel / Vitrin Tasarım'
        CONSULTING = 'consulting', 'Satış Danışmanlığı'
        PRIORITY_SUPPORT = 'priority_support', 'Öncelikli Destek'

    name = models.CharField(max_length=140, verbose_name='Paket Adı')
    slug = models.SlugField(max_length=160, unique=True)
    service_type = models.CharField(max_length=24, choices=ServiceType.choices, verbose_name='Hizmet Tipi')
    description = models.TextField(verbose_name='Açıklama')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Fiyat')
    delivery_days = models.PositiveIntegerField(default=3, verbose_name='Teslim Süresi (Gün)')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    is_featured = models.BooleanField(default=False, verbose_name='Öne Çıkan')
    display_order = models.PositiveIntegerField(default=0, verbose_name='Sıra')

    class Meta:
        verbose_name = 'Hizmet ve Destek Paketi'
        verbose_name_plural = 'Hizmet ve Destek Paketleri'
        ordering = ['display_order', 'price']

    def __str__(self) -> str:
        return self.name


class SupportServiceOrder(models.Model):
    """Vendor order/request for a paid support service."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Talep Alındı'
        IN_PROGRESS = 'in_progress', 'İşlemde'
        COMPLETED = 'completed', 'Tamamlandı'
        CANCELLED = 'cancelled', 'İptal'

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='service_orders', verbose_name='Satıcı')
    package = models.ForeignKey(SupportServicePackage, on_delete=models.PROTECT, related_name='orders', verbose_name='Paket')
    request_note = models.TextField(blank=True, verbose_name='Talep Notu')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, verbose_name='Durum')
    admin_note = models.TextField(blank=True, verbose_name='Yönetici Notu')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hizmet ve Destek Talebi'
        verbose_name_plural = 'Hizmet ve Destek Talepleri'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.vendor.store_name} - {self.package.name}'
