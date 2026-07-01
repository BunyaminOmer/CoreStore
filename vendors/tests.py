from io import BytesIO
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from openpyxl import Workbook

from store.models import Category, Product, ProductMedia
from vendors.forms import VendorProductForm
from vendors.models import (
    AdPlacementRequest,
    BusinessProfile,
    SponsoredProductCampaign,
    SupportServiceOrder,
    SupportServicePackage,
    Vendor,
    VendorApplication,
    VendorSubscription,
    VendorSubscriptionPlan,
)
from vendors.views import process_bulk_product_upload


class BulkProductUploadTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='vendor',
            email='vendor@example.com',
            password='testpass123',
            is_vendor=True,
        )
        self.vendor = Vendor.objects.create(
            user=self.user,
            store_name='Test Mağaza',
            slug='test-magaza',
            tax_number='1234567890',
            is_approved=True,
            product_limit=5,
        )
        self.category = Category.objects.create(
            name='Elektronik',
            slug='elektronik',
            is_active=True,
        )

    def make_workbook(self, rows):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['Ürün Adı', 'Kategori', 'Açıklama', 'Fiyat', 'İndirimli Fiyat', 'Stok', 'Aktif'])
        for row in rows:
            sheet.append(row)
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer

    def test_bulk_upload_creates_product(self):
        excel_file = self.make_workbook([
            ['Kablosuz Mouse', 'Elektronik', 'Sessiz mouse', '599,90', '499,90', 12, 'evet'],
        ])

        result = process_bulk_product_upload(self.vendor, excel_file, default_active=True)

        self.assertEqual(result['created'], 1)
        self.assertEqual(result['updated'], 0)
        self.assertEqual(result['errors'], [])

        product = Product.objects.get(name='Kablosuz Mouse')
        self.assertEqual(product.vendor, self.vendor)
        self.assertEqual(product.category, self.category)
        self.assertEqual(str(product.price), '599.90')
        self.assertEqual(str(product.discount_price), '499.90')
        self.assertEqual(product.stock, 12)

    def test_bulk_upload_reports_duplicate_without_update_flag(self):
        Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Kablosuz Mouse',
            slug='kablosuz-mouse',
            price='599.90',
            stock=5,
        )
        excel_file = self.make_workbook([
            ['Kablosuz Mouse', 'Elektronik', 'Yeni açıklama', '699.90', '', 20, 'evet'],
        ])

        result = process_bulk_product_upload(self.vendor, excel_file, update_existing=False)

        self.assertEqual(result['created'], 0)
        self.assertEqual(result['updated'], 0)
        self.assertEqual(len(result['errors']), 1)


class VendorProductMediaFormTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='media-vendor',
            email='media-vendor@example.com',
            password='testpass123',
            is_vendor=True,
        )
        self.vendor = Vendor.objects.create(
            user=self.user,
            store_name='Medya Mağaza',
            slug='medya-magaza',
            tax_number='1234567890',
            is_approved=True,
            product_limit=5,
        )
        self.category = Category.objects.create(
            name='Bilgisayar',
            slug='bilgisayar',
            is_active=True,
        )

    def test_vendor_product_form_saves_gallery_images_and_video(self):
        files = MultiValueDict({
            'gallery_images': [
                SimpleUploadedFile('urun-1.jpg', b'image-one', content_type='image/jpeg'),
                SimpleUploadedFile('urun-2.png', b'image-two', content_type='image/png'),
            ],
            'product_video': [
                SimpleUploadedFile('tanitim.mp4', b'video-content', content_type='video/mp4'),
            ],
        })
        form = VendorProductForm(
            data={
                'name': 'Oyuncu Laptop',
                'category': self.category.id,
                'description': 'RTX ekran kartlı laptop',
                'price': '45000',
                'discount_price': '',
                'stock': '8',
                'is_active': 'on',
            },
            files=files,
            vendor=self.vendor,
        )

        self.assertTrue(form.is_valid(), form.errors)
        product = form.save(commit=False)
        product.vendor = self.vendor
        product.save()
        form.save_media(product)

        self.assertEqual(product.media.count(), 3)
        self.assertEqual(product.media.filter(media_type=ProductMedia.MediaType.IMAGE).count(), 2)
        self.assertEqual(product.media.filter(media_type=ProductMedia.MediaType.VIDEO).count(), 1)


class VendorRevenueToolsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='revenue-vendor',
            email='revenue-vendor@example.com',
            password='testpass123',
            is_vendor=True,
        )
        self.vendor = Vendor.objects.create(
            user=self.user,
            store_name='Gelir Mağaza',
            slug='gelir-magaza',
            tax_number='9988776655',
            phone='05550000000',
            is_approved=True,
            product_limit=5,
        )
        self.category = Category.objects.create(
            name='Aksesuar',
            slug='aksesuar',
            is_active=True,
        )
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Sponsor Ürün',
            slug='sponsor-urun',
            description='Test ürünü',
            price='250.00',
            stock=10,
            is_active=True,
            is_approved=True,
        )
        self.client.login(username='revenue-vendor', password='testpass123')

    def create_business_profile(self):
        return BusinessProfile.objects.create(
            vendor=self.vendor,
            legal_name='Gelir Mağaza Ltd.',
            tax_office='Kadıköy',
            tax_number='9988776655',
            contact_person='Ömer Test',
            phone='05550000000',
            billing_email='billing@example.com',
            city='İstanbul',
            address='Test adresi',
        )

    def create_active_subscription(self, sponsored_product_quota=2):
        plan = VendorSubscriptionPlan.objects.create(
            name=f'Test Paket {sponsored_product_quota}',
            slug=f'test-paket-{sponsored_product_quota}',
            monthly_price='0.00',
            product_limit=42,
            sponsored_product_quota=sponsored_product_quota,
            ad_credit=100,
            is_active=True,
        )
        return VendorSubscription.objects.create(
            vendor=self.vendor,
            plan=plan,
            status=VendorSubscription.Status.ACTIVE,
            starts_at=timezone.now() - timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=30),
        )

    def test_subscription_page_requires_business_profile(self):
        response = self.client.get(reverse('vendors:subscriptions'))

        self.assertRedirects(response, reverse('vendors:business_profile'))

    def test_business_profile_enables_free_subscription(self):
        self.create_business_profile()
        plan = VendorSubscriptionPlan.objects.create(
            name='Test Ücretsiz',
            slug='test-ucretsiz',
            monthly_price='0.00',
            product_limit=42,
            is_active=True,
        )

        response = self.client.post(reverse('vendors:subscriptions'), {'plan_id': plan.id})

        self.assertRedirects(response, reverse('vendors:subscriptions'))
        subscription = VendorSubscription.objects.get(vendor=self.vendor, plan=plan)
        self.assertEqual(subscription.status, VendorSubscription.Status.ACTIVE)
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.product_limit, 42)

    def test_vendor_can_request_sponsored_product(self):
        self.create_business_profile()
        self.create_active_subscription()
        starts_at = timezone.now() + timedelta(days=1)
        ends_at = starts_at + timedelta(days=7)

        response = self.client.post(reverse('vendors:sponsorships'), {
            'product': self.product.id,
            'placement': SponsoredProductCampaign.Placement.HOME,
            'title': 'Haftanın ürünü',
            'daily_budget': '50.00',
            'starts_at': starts_at.strftime('%Y-%m-%dT%H:%M'),
            'ends_at': ends_at.strftime('%Y-%m-%dT%H:%M'),
        })

        self.assertRedirects(response, reverse('vendors:sponsorships'))
        campaign = SponsoredProductCampaign.objects.get(vendor=self.vendor)
        self.assertEqual(campaign.product, self.product)
        self.assertEqual(campaign.status, SponsoredProductCampaign.Status.PENDING)

    def test_vendor_can_request_ad_placement_and_support_service(self):
        self.create_business_profile()
        self.create_active_subscription()
        starts_at = timezone.now() + timedelta(days=1)
        ends_at = starts_at + timedelta(days=5)

        ad_response = self.client.post(reverse('vendors:ads'), {
            'placement': AdPlacementRequest.Placement.HOME_BOARD,
            'title': 'Yaz fırsatı',
            'description': 'Kısa kampanya',
            'target_url': '/urunler/',
            'starts_at': starts_at.strftime('%Y-%m-%dT%H:%M'),
            'ends_at': ends_at.strftime('%Y-%m-%dT%H:%M'),
        })

        self.assertRedirects(ad_response, reverse('vendors:ads'))
        self.assertEqual(AdPlacementRequest.objects.filter(vendor=self.vendor).count(), 1)

        package = SupportServicePackage.objects.create(
            name='Test Destek',
            slug='test-destek',
            service_type=SupportServicePackage.ServiceType.SETUP,
            description='Test destek paketi',
            price='100.00',
            is_active=True,
        )
        service_response = self.client.post(reverse('vendors:services'), {
            'package_id': package.id,
            'request_note': 'Kurulum desteği istiyorum.',
        })

        self.assertRedirects(service_response, reverse('vendors:services'))
        service_order = SupportServiceOrder.objects.get(vendor=self.vendor, package=package)
        self.assertEqual(service_order.status, SupportServiceOrder.Status.PENDING)


class VendorApplicationFlowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='applicant',
            email='applicant@example.com',
            password='testpass123',
        )

    def test_vendor_portal_routes_new_user_to_application_form(self):
        self.client.login(username='applicant', password='testpass123')

        response = self.client.get(reverse('vendors:portal'))

        self.assertRedirects(response, reverse('vendors:apply'))

    def test_vendor_portal_routes_pending_application_to_status_page(self):
        VendorApplication.objects.create(
            user=self.user,
            company_name='Başvuru Mağaza',
            tax_number='1112223334',
            phone='05551112233',
            description='Satıcı olmak istiyorum.',
            status=VendorApplication.Status.PENDING,
        )
        self.client.login(username='applicant', password='testpass123')

        response = self.client.get(reverse('vendors:portal'))

        self.assertRedirects(response, reverse('vendors:pending'))

    def test_rejected_application_can_open_new_application_form(self):
        VendorApplication.objects.create(
            user=self.user,
            company_name='Eski Başvuru',
            tax_number='1112223334',
            phone='05551112233',
            description='Eksik bilgi',
            status=VendorApplication.Status.REJECTED,
        )
        self.client.login(username='applicant', password='testpass123')

        response = self.client.get(reverse('vendors:apply'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Satıcı Başvurusu')

    def test_approved_vendor_portal_routes_to_dashboard(self):
        self.user.is_vendor = True
        self.user.save(update_fields=['is_vendor'])
        Vendor.objects.create(
            user=self.user,
            store_name='Onaylı Mağaza',
            slug='onayli-magaza',
            tax_number='5556667778',
            is_approved=True,
        )
        self.client.login(username='applicant', password='testpass123')

        response = self.client.get(reverse('vendors:portal'))

        self.assertRedirects(response, reverse('vendors:dashboard'))
