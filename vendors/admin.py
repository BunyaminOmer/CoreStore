from django.contrib import admin
from django.utils.text import slugify

from .models import (
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


def build_unique_vendor_slug(company_name, vendor_id=None):
    base_slug = slugify(company_name)[:190] or 'satici'
    slug = base_slug
    counter = 2
    queryset = Vendor.objects.all()
    if vendor_id:
        queryset = queryset.exclude(id=vendor_id)
    while queryset.filter(slug=slug).exists():
        suffix = f'-{counter}'
        slug = f'{base_slug[:200 - len(suffix)]}{suffix}'
        counter += 1
    return slug


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
                
                vendor, created = Vendor.objects.get_or_create(
                    user=app.user,
                    defaults={
                        'store_name': app.company_name,
                        'slug': build_unique_vendor_slug(app.company_name),
                        'description': app.description,
                        'tax_number': app.tax_number,
                        'phone': app.phone,
                        'is_approved': True
                    }
                )
                if not created:
                    vendor.store_name = app.company_name
                    vendor.description = app.description
                    vendor.tax_number = app.tax_number
                    vendor.phone = app.phone
                    vendor.is_approved = True
                    if not vendor.slug:
                        vendor.slug = build_unique_vendor_slug(app.company_name, vendor_id=vendor.id)
                    vendor.save(update_fields=[
                        'store_name',
                        'description',
                        'tax_number',
                        'phone',
                        'is_approved',
                        'slug',
                        'updated_at',
                    ])
                
                app.user.is_vendor = True
                app.user.save()
                
        self.message_user(request, "Seçilen başvurular onaylandı ve satıcı hesapları oluşturuldu.")
    approve_applications.short_description = "Seçilen başvuruları onayla"

    def reject_applications(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, "Seçilen başvurular reddedildi.")
    reject_applications.short_description = "Seçilen başvuruları reddet"


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ['legal_name', 'vendor', 'tax_number', 'city', 'is_verified', 'updated_at']
    list_filter = ['is_verified', 'city']
    list_editable = ['is_verified']
    search_fields = ['legal_name', 'trade_name', 'tax_number', 'vendor__store_name', 'billing_email']


@admin.register(VendorSubscriptionPlan)
class VendorSubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'monthly_price', 'product_limit', 'sponsored_product_quota', 'ad_credit', 'is_featured', 'is_active', 'display_order']
    list_filter = ['is_active', 'is_featured']
    list_editable = ['is_active', 'is_featured', 'display_order']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description', 'support_level']


@admin.register(VendorSubscription)
class VendorSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'plan', 'status', 'starts_at', 'ends_at', 'auto_renew']
    list_filter = ['status', 'plan', 'auto_renew']
    list_editable = ['status']
    search_fields = ['vendor__store_name', 'vendor__user__email', 'plan__name']
    autocomplete_fields = ['vendor', 'plan']


@admin.register(SponsoredProductCampaign)
class SponsoredProductCampaignAdmin(admin.ModelAdmin):
    list_display = ['product', 'vendor', 'placement', 'daily_budget', 'status', 'starts_at', 'ends_at']
    list_filter = ['status', 'placement']
    list_editable = ['status']
    search_fields = ['title', 'product__name', 'vendor__store_name']
    autocomplete_fields = ['vendor', 'product']


@admin.register(AdPlacementRequest)
class AdPlacementRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'vendor', 'placement', 'price', 'status', 'starts_at', 'ends_at']
    list_filter = ['status', 'placement']
    list_editable = ['status', 'price']
    search_fields = ['title', 'description', 'vendor__store_name']
    autocomplete_fields = ['vendor']


@admin.register(SupportServicePackage)
class SupportServicePackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'service_type', 'price', 'delivery_days', 'is_featured', 'is_active', 'display_order']
    list_filter = ['service_type', 'is_active', 'is_featured']
    list_editable = ['price', 'delivery_days', 'is_featured', 'is_active', 'display_order']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']


@admin.register(SupportServiceOrder)
class SupportServiceOrderAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'package', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'package']
    list_editable = ['status']
    search_fields = ['vendor__store_name', 'package__name', 'request_note']
    autocomplete_fields = ['vendor', 'package']
