from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from store.models import (
    Cart,
    CartItem,
    CardBinPrefix,
    CardInstallmentGroup,
    Category,
    CategoryInstallmentRule,
    CompareProduct,
    CustomerAddress,
    FavoriteProduct,
    InstallmentRate,
    Order,
    OrderPhoneNotification,
    OrderServiceRequest,
    Product,
    ProductReview,
    Shipment,
    ShippingCompany,
    SiteFeedback,
)
from vendors.models import Vendor


@override_settings(
    DOMAIN='corelogic.store',
    CUSTOM_DOMAIN_HOSTS=['corelogic.store', 'www.corelogic.store'],
    PLATFORM_HOSTS=['.onrender.com'],
    ALLOWED_HOSTS=['corelogic.store', 'www.corelogic.store', '.onrender.com', 'testserver'],
)
class CanonicalHostRedirectTests(TestCase):
    def test_platform_host_redirects_to_public_domain(self):
        response = self.client.get(
            '/vendor/apply/?source=test',
            HTTP_HOST='corelogic-store.onrender.com',
            secure=True,
        )

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], 'https://corelogic.store/vendor/apply/?source=test')

    def test_public_domain_is_not_redirected_by_canonical_middleware(self):
        response = self.client.get(
            '/',
            HTTP_HOST='corelogic.store',
            secure=True,
        )

        self.assertNotEqual(response.status_code, 301)


class HealthCheckTests(TestCase):
    def test_health_check_is_lightweight(self):
        response = self.client.get(reverse('health_check'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')


class ShipmentTrackingTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='customer',
            email='customer@example.com',
            password='testpass123',
        )
        self.company, _ = ShippingCompany.objects.get_or_create(
            code='CJ',
            defaults={'name': 'CoreJet', 'support_phone': '0850 255 00 00'},
        )

    def test_shipment_generates_corejet_tracking_number(self):
        order = Order.objects.create(
            user=self.user,
            total_amount='100.00',
            shipping_address='Test adres',
            phone='05550000000',
        )
        shipment = Shipment.objects.create(order=order, company=self.company)

        self.assertTrue(shipment.tracking_number.startswith('CJ'))
        self.assertEqual(shipment.status, Shipment.Status.CREATED)

    def test_order_success_shows_tracking_info(self):
        order = Order.objects.create(
            user=self.user,
            total_amount='100.00',
            shipping_address='Test adres',
            phone='05550000000',
        )
        Shipment.objects.create(order=order, company=self.company, tracking_number='CJTEST123')

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('store:order_success', args=[order.id]),
            HTTP_HOST='127.0.0.1',
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CoreJet Kargo Takibi')
        self.assertContains(response, 'CJTEST123')


class CheckoutAddressBillingTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='testpass123',
            phone='05550000000',
        )
        vendor_user = user_model.objects.create_user(
            username='vendor',
            email='vendor@example.com',
            password='testpass123',
        )
        self.vendor = Vendor.objects.create(
            user=vendor_user,
            store_name='Test Store',
            slug='test-store',
            tax_number='1234567890',
            is_approved=True,
        )
        self.product = Product.objects.create(
            vendor=self.vendor,
            name='Test Ürün',
            slug='test-urun',
            price='100.00',
            stock=5,
            is_active=True,
            is_approved=True,
        )
        self.card_group = CardInstallmentGroup.objects.create(
            name='Test Kartları',
            slug='test-kartlari',
            default_max_installments=1,
            is_active=True,
        )

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        ADMIN_NOTIFICATION_EMAIL='admin@example.com',
        DEFAULT_FROM_EMAIL='CoreLogic Store <noreply@example.com>',
    )
    def test_checkout_saves_address_billing_and_phone_notification(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.client.force_login(self.user)

        response = self.client.post(reverse('store:checkout'), {
            'address_action': 'place_order',
            'save_address': 'on',
            'set_default_address': 'on',
            'address_title': 'Ev',
            'shipping_recipient_name': 'Test Buyer',
            'phone': '05551112233',
            'shipping_city': 'İstanbul',
            'shipping_district': 'Kadıköy',
            'shipping_postal_code': '34000',
            'shipping_address': 'Test Mahallesi No 1',
            'billing_type': Order.BillingType.CORPORATE,
            'billing_company_name': 'CoreLogic Ltd',
            'billing_tax_office': 'Kadıköy',
            'billing_tax_number': '1234567890',
            'billing_email': 'billing@example.com',
            'billing_phone': '05551112233',
            'billing_address': 'Fatura adresi',
            'note': 'Test notu',
            'payment_card_group': self.card_group.id,
            'installment_count': '1',
        }, HTTP_HOST='127.0.0.1')

        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse('store:order_success', args=[order.id]))
        self.assertEqual(order.billing_type, Order.BillingType.CORPORATE)
        self.assertEqual(order.phone, '05551112233')
        self.assertTrue(CustomerAddress.objects.filter(user=self.user, title='Ev', is_default=True).exists())
        self.assertTrue(OrderPhoneNotification.objects.filter(order=order, phone='05551112233').exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['admin@example.com'])
        self.assertIn('Yeni sipariş', mail.outbox[0].subject)
        self.assertIn('Test Ürün x1', mail.outbox[0].body)

    def test_checkout_renders_installment_options(self):
        CardBinPrefix.objects.create(
            card_group=self.card_group,
            bank_name='Demo Bank',
            prefix='45436012',
        )
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.client.force_login(self.user)

        response = self.client.get(reverse('store:checkout'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taksit Seçenekleri')
        self.assertContains(response, 'Kart numaranızı girin')
        self.assertContains(response, '45436012')
        self.assertContains(response, 'PayTR ile Öde')

    def test_checkout_handles_category_parent_cycle(self):
        category = Category.objects.create(name='Elektronik Test', slug='elektronik-test')
        Category.objects.filter(pk=category.pk).update(parent=category)
        self.product.category = category
        self.product.save()
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.client.force_login(self.user)

        response = self.client.get(reverse('store:checkout'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taksit Seçenekleri')

    def test_checkout_applies_category_installment_rule(self):
        category = Category.objects.create(name='Bilgisayar', slug='bilgisayar')
        self.product.category = category
        self.product.price = '1000.00'
        self.product.save()
        self.card_group.default_max_installments = 6
        self.card_group.save()
        rule = CategoryInstallmentRule.objects.create(
            category=category,
            card_group=self.card_group,
            max_installments=9,
            min_cart_amount='500.00',
            is_active=True,
        )
        InstallmentRate.objects.create(rule=rule, installment_count=9, interest_rate_percent='12.00')
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.client.force_login(self.user)

        response = self.client.post(reverse('store:checkout'), {
            'address_action': 'place_order',
            'shipping_recipient_name': 'Test Buyer',
            'phone': '05551112233',
            'shipping_city': 'İstanbul',
            'shipping_address': 'Test Mahallesi No 1',
            'billing_type': Order.BillingType.INDIVIDUAL,
            'billing_full_name': 'Test Buyer',
            'billing_email': 'buyer@example.com',
            'billing_phone': '05551112233',
            'billing_address': 'Fatura adresi',
            'payment_card_group': self.card_group.id,
            'installment_count': '9',
        }, HTTP_HOST='127.0.0.1')

        order = Order.objects.get(user=self.user)
        self.assertRedirects(response, reverse('store:order_success', args=[order.id]))
        self.assertEqual(order.installment_count, 9)
        self.assertEqual(order.installment_rate_percent, Decimal('12.00'))
        self.assertEqual(order.installment_base_amount, Decimal('1000.00'))
        self.assertEqual(order.total_amount, Decimal('1120.00'))
        self.assertEqual(order.installment_monthly_amount, Decimal('124.44'))


class ReviewAndFeedbackTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='reviewer',
            email='reviewer@example.com',
            password='testpass123',
        )
        vendor_user = user_model.objects.create_user(
            username='reviewvendor',
            email='reviewvendor@example.com',
            password='testpass123',
        )
        vendor = Vendor.objects.create(
            user=vendor_user,
            store_name='Review Store',
            slug='review-store',
            tax_number='9876543210',
            is_approved=True,
        )
        self.product = Product.objects.create(
            vendor=vendor,
            name='Yorumlu Ürün',
            slug='yorumlu-urun',
            price='50.00',
            stock=3,
            is_active=True,
            is_approved=True,
        )

    def test_product_review_is_displayed(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('store:product_detail', args=[self.product.slug]), {
            'rating': 5,
            'title': 'Başarılı',
            'comment': 'Ürün beklentimi karşıladı.',
        })

        self.assertRedirects(response, reverse('store:product_detail', args=[self.product.slug]))
        self.assertTrue(ProductReview.objects.filter(product=self.product, user=self.user).exists())

        response = self.client.get(reverse('store:product_detail', args=[self.product.slug]))
        self.assertContains(response, 'Ürün beklentimi karşıladı.')

    def test_feedback_form_creates_feedback(self):
        response = self.client.post(reverse('store:feedback'), {
            'name': 'Test User',
            'email': 'test@example.com',
            'topic': SiteFeedback.Topic.GENERAL,
            'message': 'Sistem gayet anlaşılır.',
        })

        self.assertRedirects(response, reverse('store:feedback'))
        self.assertTrue(SiteFeedback.objects.filter(email='test@example.com').exists())


class CustomerCommerceFeatureTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='featurebuyer',
            email='featurebuyer@example.com',
            password='testpass123',
        )
        vendor_user = user_model.objects.create_user(
            username='featurevendor',
            email='featurevendor@example.com',
            password='testpass123',
        )
        self.vendor = Vendor.objects.create(
            user=vendor_user,
            store_name='Feature Store',
            slug='feature-store',
            tax_number='1234567890',
            is_approved=True,
        )
        self.category = Category.objects.create(name='Telefon', slug='telefon', is_active=True)
        self.product = Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Test Telefon',
            slug='test-telefon',
            price='15000.00',
            discount_price='14000.00',
            stock=4,
            is_active=True,
            is_approved=True,
        )

    def test_customer_can_toggle_favorite_and_compare_product(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('store:toggle_favorite', args=[self.product.id]))
        self.assertRedirects(response, reverse('store:home'))
        self.assertTrue(FavoriteProduct.objects.filter(user=self.user, product=self.product).exists())

        response = self.client.post(reverse('store:add_compare', args=[self.product.id]))
        self.assertRedirects(response, reverse('store:home'))
        self.assertTrue(CompareProduct.objects.filter(user=self.user, product=self.product).exists())

        response = self.client.get(reverse('store:compare'))
        self.assertContains(response, 'Test Telefon')

    def test_category_filters_products(self):
        Product.objects.create(
            vendor=self.vendor,
            category=self.category,
            name='Pahalı Telefon',
            slug='pahali-telefon',
            price='50000.00',
            stock=0,
            is_active=True,
            is_approved=True,
        )

        response = self.client.get(reverse('store:category', args=[self.category.slug]), {
            'max_price': '20000',
            'in_stock': '1',
            'on_sale': '1',
        })

        self.assertContains(response, 'Test Telefon')
        self.assertNotContains(response, 'Pahalı Telefon')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        ADMIN_NOTIFICATION_EMAIL='admin@example.com',
    )
    def test_customer_can_create_order_return_request_and_download_pdf(self):
        order = Order.objects.create(
            user=self.user,
            total_amount='14000.00',
            status=Order.Status.DELIVERED,
            shipping_address='Test teslimat adresi',
            phone='05550000000',
            billing_full_name='Feature Buyer',
            billing_address='Test fatura adresi',
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('store:order_service_request', args=[order.id]), {
            'request_type': OrderServiceRequest.RequestType.RETURN,
            'reason': 'Ürün beklentimi karşılamadı',
            'description': 'İade süreci başlatılsın.',
        })

        self.assertRedirects(response, reverse('store:order_success', args=[order.id]))
        self.assertTrue(OrderServiceRequest.objects.filter(order=order, user=self.user).exists())
        self.assertEqual(len(mail.outbox), 1)

        response = self.client.get(reverse('store:order_receipt_pdf', args=[order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
