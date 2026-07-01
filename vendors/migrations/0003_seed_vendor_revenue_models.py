from decimal import Decimal

from django.db import migrations


def seed_vendor_revenue_models(apps, schema_editor):
    VendorSubscriptionPlan = apps.get_model('vendors', 'VendorSubscriptionPlan')
    SupportServicePackage = apps.get_model('vendors', 'SupportServicePackage')

    plans = [
        {
            'slug': 'ucretsiz-baslangic',
            'name': 'Ücretsiz Başlangıç',
            'description': 'Yeni satıcılar için düşük limitli başlangıç paketi.',
            'monthly_price': Decimal('0.00'),
            'product_limit': 20,
            'sponsored_product_quota': 0,
            'ad_credit': 0,
            'support_level': 'Standart destek',
            'is_featured': False,
            'display_order': 1,
        },
        {
            'slug': 'buyume',
            'name': 'Büyüme',
            'description': 'Daha fazla ürün ve temel reklam denemeleri için.',
            'monthly_price': Decimal('199.00'),
            'product_limit': 200,
            'sponsored_product_quota': 1,
            'ad_credit': 100,
            'support_level': 'Öncelikli e-posta desteği',
            'is_featured': False,
            'display_order': 2,
        },
        {
            'slug': 'pro-satici',
            'name': 'Pro Satıcı',
            'description': 'Vitrinde büyümek isteyen aktif mağazalar için.',
            'monthly_price': Decimal('499.00'),
            'product_limit': 1000,
            'sponsored_product_quota': 4,
            'ad_credit': 500,
            'support_level': 'Öncelikli destek ve vitrin yönlendirmesi',
            'is_featured': True,
            'display_order': 3,
        },
        {
            'slug': 'kurumsal',
            'name': 'Kurumsal',
            'description': 'Geniş katalog, reklam ve özel destek ihtiyacı olan satıcılar için.',
            'monthly_price': Decimal('999.00'),
            'product_limit': 5000,
            'sponsored_product_quota': 10,
            'ad_credit': 1500,
            'support_level': 'Özel destek ve kampanya planlama',
            'is_featured': False,
            'display_order': 4,
        },
    ]

    for plan in plans:
        VendorSubscriptionPlan.objects.update_or_create(
            slug=plan['slug'],
            defaults={**plan, 'is_active': True},
        )

    packages = [
        {
            'slug': 'magaza-kurulum-paketi',
            'name': 'Mağaza Kurulum Paketi',
            'service_type': 'setup',
            'description': 'Mağaza bilgileri, kategori düzeni ve ilk vitrin kontrolü beraber hazırlanır.',
            'price': Decimal('499.00'),
            'delivery_days': 2,
            'is_featured': False,
            'display_order': 1,
        },
        {
            'slug': 'toplu-urun-yukleme-destegi',
            'name': 'Toplu Ürün Yükleme Desteği',
            'service_type': 'product_upload',
            'description': 'Excel dosyanız kontrol edilir, kolonlar temizlenir ve ürün aktarımı güvenli şekilde yapılır.',
            'price': Decimal('799.00'),
            'delivery_days': 3,
            'is_featured': True,
            'display_order': 2,
        },
        {
            'slug': 'vitrin-gorsel-tasarim-paketi',
            'name': 'Vitrin Görsel Tasarım Paketi',
            'service_type': 'design',
            'description': 'Ana görsel, kampanya dili ve ürün sunumu daha profesyonel bir vitrin için düzenlenir.',
            'price': Decimal('599.00'),
            'delivery_days': 4,
            'is_featured': False,
            'display_order': 3,
        },
        {
            'slug': 'satis-danismanligi-seansi',
            'name': 'Satış Danışmanlığı Seansı',
            'service_type': 'consulting',
            'description': 'Fiyat, kategori, kampanya ve stok yaklaşımı için kısa aksiyon planı hazırlanır.',
            'price': Decimal('999.00'),
            'delivery_days': 5,
            'is_featured': False,
            'display_order': 4,
        },
        {
            'slug': 'oncelikli-teknik-destek',
            'name': 'Öncelikli Teknik Destek',
            'service_type': 'priority_support',
            'description': 'Satıcı paneli, ürün yükleme ve sipariş süreçlerinde öncelikli destek talebi açılır.',
            'price': Decimal('299.00'),
            'delivery_days': 1,
            'is_featured': False,
            'display_order': 5,
        },
    ]

    for package in packages:
        SupportServicePackage.objects.update_or_create(
            slug=package['slug'],
            defaults={**package, 'is_active': True},
        )


def unseed_vendor_revenue_models(apps, schema_editor):
    VendorSubscriptionPlan = apps.get_model('vendors', 'VendorSubscriptionPlan')
    SupportServicePackage = apps.get_model('vendors', 'SupportServicePackage')
    VendorSubscriptionPlan.objects.filter(slug__in=[
        'ucretsiz-baslangic',
        'buyume',
        'pro-satici',
        'kurumsal',
    ]).delete()
    SupportServicePackage.objects.filter(slug__in=[
        'magaza-kurulum-paketi',
        'toplu-urun-yukleme-destegi',
        'vitrin-gorsel-tasarim-paketi',
        'satis-danismanligi-seansi',
        'oncelikli-teknik-destek',
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0002_supportservicepackage_vendorsubscriptionplan_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_vendor_revenue_models, unseed_vendor_revenue_models),
    ]
