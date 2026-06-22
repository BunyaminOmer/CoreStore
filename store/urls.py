from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('category/<slug:slug>/', views.category_products_view, name='category'),
    path('search/', views.search_view, name='search'),
    
    # Cart AJAX Endpoints
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/apply-coupon/', views.apply_coupon, name='apply_coupon'),
    
    # Checkout
    path('checkout/', views.checkout_view, name='checkout'),
    path('order-success/<int:order_id>/', views.order_success_view, name='order_success'),
]
