from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('odeme-takip/', views.payment_tracker_view, name='payment_tracker'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('product/<int:product_id>/favori/', views.toggle_favorite_view, name='toggle_favorite'),
    path('product/<int:product_id>/karsilastir-ekle/', views.add_compare_view, name='add_compare'),
    path('product/<int:product_id>/karsilastir-cikar/', views.remove_compare_view, name='remove_compare'),
    path('karsilastir/', views.compare_view, name='compare'),
    path('category/<slug:slug>/', views.category_products_view, name='category'),
    path('satici/<slug:slug>/', views.vendor_detail_view, name='vendor_detail'),
    path('search/', views.search_view, name='search'),
    path('geri-bildirim/', views.feedback_view, name='feedback'),
    path('gizlilik-politikasi/', views.privacy_policy_view, name='privacy_policy'),
    path('sss/', views.faq_view, name='faq'),
    path('iade-iptal-kosullari/', views.cancellation_policy_view, name='cancellation_policy'),
    path('mesafeli-satis-sozlesmesi/', views.distance_sales_view, name='distance_sales'),
    
    # Cart AJAX Endpoints
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/apply-coupon/', views.apply_coupon, name='apply_coupon'),
    
    # Checkout
    path('checkout/', views.checkout_view, name='checkout'),
    path('order-success/<int:order_id>/', views.order_success_view, name='order_success'),
    path('order-success/<int:order_id>/talep/', views.order_service_request_view, name='order_service_request'),
    path('order-success/<int:order_id>/pdf/', views.order_receipt_pdf_view, name='order_receipt_pdf'),
    path('siparis-bilgi/<str:token>/', views.order_info_view, name='order_info'),
]
