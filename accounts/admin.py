from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_vendor', 'is_staff']
    list_filter = ['is_vendor', 'is_staff', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Profil Bilgileri', {'fields': ('phone', 'address', 'city', 'avatar')}),
        ('Satıcı Durumu', {'fields': ('is_vendor',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Ek Bilgiler', {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'phone', 'is_vendor')}
        ),
    )

admin.site.register(CustomUser, CustomUserAdmin)

# Customize Admin Dashboard Titles
admin.site.site_header = 'CoreLogic Store Yönetim Paneli'
admin.site.site_title = 'CoreLogic Store Admin'
admin.site.index_title = 'Yönetim Paneline Hoş Geldiniz'
