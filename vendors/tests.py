from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from openpyxl import Workbook

from store.models import Category, Product
from vendors.models import Vendor
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
