from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models
from django.utils import timezone


class EmailTwoFactorCode(models.Model):
    """Short-lived email verification code for login and registration flows."""

    PURPOSE_LOGIN = 'login'
    PURPOSE_REGISTER = 'register'
    PURPOSE_CHOICES = (
        (PURPOSE_LOGIN, 'Giriş doğrulama'),
        (PURPOSE_REGISTER, 'Kayıt doğrulama'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_2fa_codes',
        verbose_name='Kullanıcı',
    )
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, verbose_name='Amaç')
    code_hash = models.CharField(max_length=128, verbose_name='Kod özeti')
    sent_to = models.EmailField(verbose_name='Gönderilen e-posta')
    expires_at = models.DateTimeField(verbose_name='Son geçerlilik')
    used_at = models.DateTimeField(blank=True, null=True, verbose_name='Kullanım zamanı')
    attempts = models.PositiveSmallIntegerField(default=0, verbose_name='Deneme sayısı')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma zamanı')

    class Meta:
        verbose_name = 'E-posta 2FA Kodu'
        verbose_name_plural = 'E-posta 2FA Kodları'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.user} - {self.get_purpose_display()}'

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and not self.is_expired and self.attempts < 5


class CustomUser(AbstractUser):
    """Extended user model with profile and vendor flag fields."""

    phone = models.CharField(max_length=15, blank=True, verbose_name='Telefon')
    address = models.TextField(blank=True, verbose_name='Adres')
    city = models.CharField(max_length=100, blank=True, verbose_name='Şehir')
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Profil Fotoğrafı',
    )
    is_vendor = models.BooleanField(default=False, verbose_name='Satıcı mı?')
    email_2fa_enabled = models.BooleanField(default=True, verbose_name='E-posta 2FA aktif')
    email_verified_at = models.DateTimeField(blank=True, null=True, verbose_name='E-posta doğrulama zamanı')

    class Meta:
        verbose_name = 'Kullanıcı'
        verbose_name_plural = 'Kullanıcılar'

    def __str__(self) -> str:
        return self.username
