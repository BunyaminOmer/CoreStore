from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, EmailTwoFactorCode

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'first_name', 'last_name', 'email_2fa_enabled', 'is_vendor', 'is_staff']
    list_filter = ['email_2fa_enabled', 'is_vendor', 'is_staff', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Profil Bilgileri', {'fields': ('phone', 'address', 'city', 'avatar')}),
        ('Güvenlik', {'fields': ('email_2fa_enabled', 'email_verified_at')}),
        ('Satıcı Durumu', {'fields': ('is_vendor',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Ek Bilgiler', {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'phone', 'email_2fa_enabled', 'is_vendor')}
        ),
    )


@admin.register(EmailTwoFactorCode)
class EmailTwoFactorCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'purpose', 'sent_to', 'attempts', 'expires_at', 'used_at', 'created_at']
    list_filter = ['purpose', 'used_at', 'created_at']
    search_fields = ['user__username', 'user__email', 'sent_to']
    readonly_fields = ['user', 'purpose', 'code_hash', 'sent_to', 'expires_at', 'used_at', 'attempts', 'created_at']

admin.site.register(CustomUser, CustomUserAdmin)

# Customize Admin Dashboard Titles
admin.site.site_header = 'CoreLogic Store Yönetim Paneli'
admin.site.site_title = 'CoreLogic Store Admin'
admin.site.index_title = 'Yönetim Paneline Hoş Geldiniz'
