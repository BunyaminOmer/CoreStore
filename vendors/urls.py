from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    path('apply/', views.vendor_apply_view, name='apply'),
    path('pending/', views.vendor_pending_view, name='pending'),
    path('dashboard/', views.vendor_dashboard_view, name='dashboard'),
    path('products/', views.vendor_product_list_view, name='product_list'),
    path('products/add/', views.vendor_product_add_view, name='product_add'),
    path('products/edit/<int:pk>/', views.vendor_product_edit_view, name='product_edit'),
    path('products/delete/<int:pk>/', views.vendor_product_delete_view, name='product_delete'),
    path('orders/', views.vendor_orders_view, name='orders'),
    path('bulk-upload/', views.vendor_bulk_upload_view, name='bulk_upload'),
    path('bulk-upload/template/', views.vendor_bulk_upload_template_view, name='bulk_upload_template'),
]
