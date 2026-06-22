from django.contrib import admin
from .models import Vendor, VendorApplication
from django.utils.text import slugify

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['store_name', 'user', 'tax_number', 'is_approved', 'product_count', 'created_at']
    list_filter = ['is_approved']
    list_editable = ['is_approved']
    search_fields = ['store_name', 'tax_number', 'user__username', 'user__email']
    prepopulated_fields = {'slug': ('store_name',)}

@admin.register(VendorApplication)
class VendorApplicationAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'user', 'tax_number', 'status', 'created_at']
    list_filter = ['status']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['approve_applications', 'reject_applications']

    def approve_applications(self, request, queryset):
        for app in queryset:
            if app.status != 'approved':
                app.status = 'approved'
                app.save()
                
                # Create Vendor Profile
                Vendor.objects.get_or_create(
                    user=app.user,
                    defaults={
                        'store_name': app.company_name,
                        'store_slug': slugify(app.company_name),
                        'store_description': app.description,
                        'tax_number': app.tax_number,
                        'is_approved': True
                    }
                )
                
                # Update User
                app.user.is_vendor = True
                app.user.save()
                
        self.message_user(request, "Seçilen başvurular onaylandı ve satıcı hesapları oluşturuldu.")
    approve_applications.short_description = "Seçilen başvuruları onayla"

    def reject_applications(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, "Seçilen başvurular reddedildi.")
    reject_applications.short_description = "Seçilen başvuruları reddet"
