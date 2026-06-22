from django.contrib.auth.models import AbstractUser
from django.db import models


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

    class Meta:
        verbose_name = 'Kullanıcı'
        verbose_name_plural = 'Kullanıcılar'

    def __str__(self) -> str:
        return self.username
