from django.contrib import admin
from .models import Category, Product, Cart, CartItem, Order, OrderItem, Coupon

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ['is_active']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'vendor', 'category', 'price', 'discount_price', 'stock', 'is_active', 'is_approved', 'created_at']
    list_filter = ['is_active', 'is_approved', 'category', 'vendor']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active', 'is_approved', 'stock']

class CartItemInline(admin.TabularInline):
    model = CartItem
    raw_id_fields = ['product']
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'total_items', 'total_price', 'created_at']
    inlines = [CartItemInline]

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    list_editable = ['status']
    readonly_fields = ['created_at']
    inlines = [OrderItemInline]

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percent', 'is_active', 'valid_from', 'valid_until', 'times_used', 'usage_limit']
    list_filter = ['is_active']
    list_editable = ['is_active']
