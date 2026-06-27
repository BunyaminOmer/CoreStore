import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_2FA_SHOW_DEBUG_CODE=False,
)
class EmailTwoFactorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='customer',
            email='customer@example.com',
            password='StrongPass123!',
        )

    def extract_code(self):
        self.assertEqual(len(mail.outbox), 1)
        match = re.search(r'(\d{6})', mail.outbox[0].body)
        self.assertIsNotNone(match)
        return match.group(1)

    def test_login_requires_email_code(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'customer',
            'password': 'StrongPass123!',
            'next': reverse('accounts:profile'),
        })

        self.assertRedirects(response, reverse('accounts:verify_email_2fa'))
        self.assertNotIn('_auth_user_id', self.client.session)

        code = self.extract_code()
        response = self.client.post(reverse('accounts:verify_email_2fa'), {'code': code})

        self.assertRedirects(response, reverse('accounts:profile'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_register_requires_email_code(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newcustomer',
            'email': 'newcustomer@example.com',
            'first_name': 'New',
            'last_name': 'Customer',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })

        self.assertRedirects(response, reverse('accounts:verify_email_2fa'))
        self.assertNotIn('_auth_user_id', self.client.session)

        code = self.extract_code()
        response = self.client.post(reverse('accounts:verify_email_2fa'), {'code': code})
        self.assertRedirects(response, reverse('store:home'))

        new_user = get_user_model().objects.get(username='newcustomer')
        self.assertEqual(int(self.client.session['_auth_user_id']), new_user.pk)
        self.assertIsNotNone(new_user.email_verified_at)
