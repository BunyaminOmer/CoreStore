from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    path('', views.vendor_portal_view, name='portal'),
    path('apply/', views.vendor_apply_view, name='apply'),
    path('pending/', views.vendor_pending_view, name='pending'),
    path('dashboard/', views.vendor_dashboard_view, name='dashboard'),
    path('business-profile/', views.vendor_business_profile_view, name='business_profile'),
    path('subscriptions/', views.vendor_subscription_view, name='subscriptions'),
    path('sponsorships/', views.vendor_sponsorships_view, name='sponsorships'),
    path('ads/', views.vendor_ads_view, name='ads'),
    path('services/', views.vendor_services_view, name='services'),
    path('products/', views.vendor_product_list_view, name='product_list'),
    path('products/add/', views.vendor_product_add_view, name='product_add'),
    path('products/edit/<int:pk>/', views.vendor_product_edit_view, name='product_edit'),
    path('products/delete/<int:pk>/', views.vendor_product_delete_view, name='product_delete'),
    path('orders/', views.vendor_orders_view, name='orders'),
    path('bulk-upload/', views.vendor_bulk_upload_view, name='bulk_upload'),
    path('bulk-upload/template/', views.vendor_bulk_upload_template_view, name='bulk_upload_template'),
]
