from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Cart,
    CartItem,
    CardBinPrefix,
    CardInstallmentGroup,
    CargoStation,
    Category,
    CategoryInstallmentRule,
    CompareProduct,
    Coupon,
    CustomerAddress,
    FavoriteProduct,
    HeroCampaign,
    HomeFeaturedCategory,
    HomeFeaturedProduct,
    InstallmentRate,
    Order,
    OrderItem,
    OrderPhoneNotification,
    OrderServiceRequest,
    Product,
    ProductMedia,
    ProductQuestion,
    ProductReview,
    ProductVariant,
    Shipment,
    ShipmentEvent,
    ShippingCompany,
    SiteFeedback,
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ['is_active']
    search_fields = ['name']

class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ['media_type', 'file', 'media_preview', 'title', 'display_order', 'is_active']
    readonly_fields = ['media_preview']

    @admin.display(description='Önizleme')
    def media_preview(self, obj):
        if not obj or not obj.file:
            return 'Dosya eklenmedi.'
        if obj.is_video:
            return format_html(
                '<video src="{}" style="width:140px;height:84px;object-fit:cover;border-radius:8px;border:1px solid #ddd;" controls muted></video>',
                obj.file.url,
            )
        return format_html(
            '<img src="{}" style="width:84px;height:84px;object-fit:cover;border-radius:8px;border:1px solid #ddd;" />',
            obj.file.url,
        )


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['option_name', 'option_value', 'sku', 'price_delta', 'stock', 'display_order', 'is_active']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'vendor', 'category', 'price', 'discount_price', 'stock', 'is_active', 'is_approved', 'created_at']
    list_filter = ['is_active', 'is_approved', 'category', 'vendor']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'is_approved', 'stock']
    inlines = [ProductVariantInline, ProductMediaInline]


@admin.register(ProductMedia)
class ProductMediaAdmin(admin.ModelAdmin):
    list_display = ['product', 'media_type', 'title', 'display_order', 'is_active', 'created_at']
    list_filter = ['media_type', 'is_active', 'product__category']
    search_fields = ['product__name', 'title']
    autocomplete_fields = ['product']
    list_editable = ['display_order', 'is_active']


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'option_name', 'option_value', 'sku', 'price_delta', 'stock', 'display_order', 'is_active']
    list_filter = ['is_active', 'option_name', 'product__category']
    search_fields = ['product__name', 'option_name', 'option_value', 'sku']
    autocomplete_fields = ['product']
    list_editable = ['stock', 'display_order', 'is_active']


@admin.register(FavoriteProduct)
class FavoriteProductAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__username', 'user__email', 'product__name']
    autocomplete_fields = ['user', 'product']


@admin.register(CompareProduct)
class CompareProductAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__username', 'user__email', 'product__name']
    autocomplete_fields = ['user', 'product']


@admin.register(HeroCampaign)
class HeroCampaignAdmin(admin.ModelAdmin):
    list_display = ['title', 'badge_text', 'display_order', 'live_status', 'starts_at', 'ends_at', 'updated_at']
    list_filter = ['is_active', 'starts_at', 'ends_at']
    search_fields = ['title', 'subtitle', 'badge_text']
    list_editable = ['display_order']
    readonly_fields = ['image_preview', 'created_at', 'updated_at']
    fieldsets = (
        ('Kampanya İçeriği', {
            'fields': ('title', 'subtitle', 'badge_text', 'image', 'image_preview')
        }),
        ('Bağlantı ve Yayın', {
            'fields': ('link_text', 'link_url', 'display_order', 'is_active', 'starts_at', 'ends_at')
        }),
        ('Kayıt Bilgisi', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )

    @admin.display(description='Görsel Önizleme')
    def image_preview(self, obj):
        if obj and obj.image:
            return format_html(
                '<img src="{}" style="width:220px;height:96px;object-fit:cover;border-radius:8px;border:1px solid #ddd;" />',
                obj.image.url,
            )
        return 'Görsel eklenmedi.'

    @admin.display(description='Yayın')
    def live_status(self, obj):
        if obj.is_live:
            return format_html('<span style="color:#059669;font-weight:700;">Yayında</span>')
        return format_html('<span style="color:#64748b;font-weight:700;">Pasif</span>')


@admin.register(HomeFeaturedProduct)
class HomeFeaturedProductAdmin(admin.ModelAdmin):
    list_display = ['product', 'vendor_name', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'product__category', 'product__vendor']
    search_fields = ['product__name', 'product__vendor__store_name', 'title_override']
    list_editable = ['display_order', 'is_active']
    autocomplete_fields = ['product']

    @admin.display(description='Satıcı')
    def vendor_name(self, obj):
        return obj.product.vendor.store_name


@admin.register(HomeFeaturedCategory)
class HomeFeaturedCategoryAdmin(admin.ModelAdmin):
    list_display = ['category', 'label_override', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'category__parent']
    search_fields = ['category__name', 'label_override']
    list_editable = ['display_order', 'is_active']
    autocomplete_fields = ['category']

class CartItemInline(admin.TabularInline):
    model = CartItem
    raw_id_fields = ['product']
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'total_items', 'total_price', 'created_at']
    inlines = [CartItemInline]


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'recipient_name', 'phone', 'city', 'is_default', 'updated_at']
    list_filter = ['city', 'is_default']
    search_fields = ['title', 'recipient_name', 'phone', 'city', 'address_line', 'user__username', 'user__email']


class InstallmentRateInline(admin.TabularInline):
    model = InstallmentRate
    extra = 3
    fields = ['installment_count', 'interest_rate_percent']


class CardBinPrefixInline(admin.TabularInline):
    model = CardBinPrefix
    extra = 2
    fields = ['bank_name', 'prefix', 'is_active']


@admin.register(CardInstallmentGroup)
class CardInstallmentGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'default_max_installments', 'is_default_for_unknown_cards', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_default_for_unknown_cards']
    search_fields = ['name', 'slug', 'description', 'bin_prefixes__bank_name', 'bin_prefixes__prefix']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['default_max_installments', 'is_default_for_unknown_cards', 'display_order', 'is_active']
    inlines = [CardBinPrefixInline]


@admin.register(CardBinPrefix)
class CardBinPrefixAdmin(admin.ModelAdmin):
    list_display = ['bank_name', 'prefix', 'card_group', 'is_active', 'created_at']
    list_filter = ['card_group', 'is_active']
    search_fields = ['bank_name', 'prefix', 'card_group__name']
    autocomplete_fields = ['card_group']
    list_editable = ['is_active']


@admin.register(CategoryInstallmentRule)
class CategoryInstallmentRuleAdmin(admin.ModelAdmin):
    list_display = ['category', 'card_group', 'max_installments', 'min_cart_amount', 'priority', 'is_active']
    list_filter = ['card_group', 'category', 'is_active']
    search_fields = ['category__name', 'card_group__name']
    autocomplete_fields = ['category', 'card_group']
    list_editable = ['max_installments', 'min_cart_amount', 'priority', 'is_active']
    inlines = [InstallmentRateInline]


@admin.register(ShippingCompany)
class ShippingCompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'support_phone', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code', 'support_phone']
    list_editable = ['is_active']


@admin.register(CargoStation)
class CargoStationAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'city', 'code', 'display_order', 'is_active']
    list_filter = ['company', 'city', 'is_active']
    search_fields = ['name', 'city', 'code', 'address']
    list_editable = ['display_order', 'is_active']


class ShipmentEventInline(admin.TabularInline):
    model = ShipmentEvent
    extra = 0
    autocomplete_fields = ['station']
    fields = ['status', 'station', 'description', 'happened_at']


class ShipmentInline(admin.StackedInline):
    model = Shipment
    extra = 0
    max_num = 1
    autocomplete_fields = ['company', 'current_station']
    fields = ['company', 'tracking_number', 'status', 'current_station', 'estimated_delivery', 'note']


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ['tracking_number', 'order', 'company', 'status', 'current_station', 'estimated_delivery', 'updated_at']
    list_filter = ['company', 'status', 'current_station']
    search_fields = ['tracking_number', 'order__id', 'order__user__username', 'order__user__email']
    autocomplete_fields = ['order', 'company', 'current_station']
    inlines = [ShipmentEventInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_amount', 'installment_summary', 'status', 'phone', 'billing_type', 'shipment_tracking', 'created_at']
    list_filter = ['status', 'billing_type', 'installment_count', 'created_at']
    list_editable = ['status']
    search_fields = ['id', 'user__username', 'user__email', 'phone', 'shipping_recipient_name', 'billing_tax_number', 'installment_card_group_name']
    readonly_fields = ['created_at', 'public_token']
    inlines = [OrderItemInline, ShipmentInline]

    @admin.display(description='Kargo Takip')
    def shipment_tracking(self, obj):
        shipment = getattr(obj, 'shipment', None)
        if shipment:
            return shipment.tracking_number
        return 'Henüz yok'

    @admin.display(description='Taksit')
    def installment_summary(self, obj):
        if obj.installment_count <= 1:
            return 'Tek çekim'
        return f'{obj.installment_card_group_name or "Kart"} / {obj.installment_count} x {obj.installment_monthly_amount} TL'


@admin.register(OrderPhoneNotification)
class OrderPhoneNotificationAdmin(admin.ModelAdmin):
    list_display = ['order', 'phone', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__id', 'phone', 'message', 'tracking_link']
    readonly_fields = ['order', 'phone', 'message', 'tracking_link', 'provider_response', 'created_at']


@admin.register(OrderServiceRequest)
class OrderServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['order', 'user', 'request_type', 'reason', 'status', 'created_at']
    list_filter = ['request_type', 'status', 'created_at']
    search_fields = ['order__id', 'user__username', 'user__email', 'reason', 'description']
    autocomplete_fields = ['order', 'user']
    list_editable = ['status']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percent', 'is_active', 'valid_from', 'valid_until', 'times_used', 'usage_limit']
    list_filter = ['is_active']
    list_editable = ['is_active']


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved', 'created_at']
    search_fields = ['product__name', 'user__username', 'title', 'comment']
    list_editable = ['is_approved']


@admin.register(ProductQuestion)
class ProductQuestionAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'short_question', 'has_answer', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at', 'answered_at']
    search_fields = ['product__name', 'user__username', 'user__email', 'question', 'answer']
    autocomplete_fields = ['product', 'user', 'answered_by']
    list_editable = ['is_public']

    @admin.display(description='Soru')
    def short_question(self, obj):
        return obj.question[:80]

    @admin.display(description='Cevaplandı', boolean=True)
    def has_answer(self, obj):
        return bool(obj.answer)


@admin.register(SiteFeedback)
class SiteFeedbackAdmin(admin.ModelAdmin):
    list_display = ['topic', 'name', 'email', 'is_resolved', 'created_at']
    list_filter = ['topic', 'is_resolved', 'created_at']
    search_fields = ['name', 'email', 'message']
    list_editable = ['is_resolved']
