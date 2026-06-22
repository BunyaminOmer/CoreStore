from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
from .models import Vendor, VendorApplication
from .forms import VendorApplicationForm, VendorProductForm
from store.models import Product, OrderItem

def is_approved_vendor(user):
    return user.is_authenticated and user.is_vendor and hasattr(user, 'vendor_profile') and user.vendor_profile.is_approved

@login_required
def vendor_apply_view(request):
    if request.user.vendor_applications.exists():
        app = request.user.vendor_applications.first()
        if app.status == 'pending':
            return redirect('vendors:pending')
        elif app.status == 'approved':
            messages.success(request, 'Zaten onaylı bir satıcısınız.')
            return redirect('vendors:dashboard')
            
    if request.method == 'POST':
        form = VendorApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.save()
            return redirect('vendors:pending')
    else:
        form = VendorApplicationForm()
        
    return render(request, 'vendors/apply.html', {'form': form})

@login_required
def vendor_pending_view(request):
    if not request.user.vendor_applications.exists():
        return redirect('vendors:apply')
    app = request.user.vendor_applications.first()
    return render(request, 'vendors/pending.html', {'application': app})

@user_passes_test(is_approved_vendor, login_url='/accounts/login/')
def vendor_dashboard_view(request):
    from django.db.models import F
    import json
    from datetime import timedelta
    
    vendor = request.user.vendor_profile
    
    # Stats
    product_count = vendor.products.count()
    active_orders = OrderItem.objects.filter(product__vendor=vendor, order__status__in=['preparing', 'shipped'])
    active_orders_count = active_orders.values('order').distinct().count()
    
    # Total sales
    total_sales = OrderItem.objects.filter(product__vendor=vendor, order__status='delivered').aggregate(
        total=Sum(F('price') * F('quantity'))
    )['total'] or 0
    
    # Recent orders
    recent_orders = OrderItem.objects.filter(product__vendor=vendor).order_by('-order__created_at')[:5]
    
    # Low stock products
    low_stock_products = vendor.products.filter(stock__lt=5, is_active=True).order_by('stock')
    
    # Sales Chart Data (last 7 days)
    today = timezone.now().date()
    sales_labels = []
    sales_data = []
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_sales = OrderItem.objects.filter(
            product__vendor=vendor,
            order__status='delivered',
            order__created_at__date=day
        ).aggregate(total=Sum(F('price') * F('quantity')))['total'] or 0
        
        sales_labels.append(day.strftime("%d %b"))
        sales_data.append(float(day_sales))
    
    context = {
        'vendor': vendor,
        'product_count': product_count,
        'active_orders_count': active_orders_count,
        'total_sales': total_sales,
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
        'sales_labels': json.dumps(sales_labels),
        'sales_data': json.dumps(sales_data),
    }
    return render(request, 'vendors/dashboard.html', context)

@user_passes_test(is_approved_vendor)
def vendor_product_list_view(request):
    vendor = request.user.vendor_profile
    products = vendor.products.all().order_by('-created_at')
    return render(request, 'vendors/product_list.html', {'products': products, 'vendor': vendor})

@user_passes_test(is_approved_vendor)
def vendor_product_add_view(request):
    vendor = request.user.vendor_profile
    if not vendor.can_add_product:
        messages.error(request, 'Ürün ekleme limitinize ulaştınız.')
        return redirect('vendors:product_list')
        
    if request.method == 'POST':
        form = VendorProductForm(request.POST, request.FILES, vendor=vendor)
        if form.is_valid():
            product = form.save(commit=False)
            product.vendor = vendor
            product.save()
            messages.success(request, 'Ürün başarıyla eklendi.')
            return redirect('vendors:product_list')
    else:
        form = VendorProductForm(vendor=vendor)
        
    return render(request, 'vendors/product_form.html', {'form': form, 'title': 'Yeni Ürün Ekle'})

@user_passes_test(is_approved_vendor)
def vendor_product_edit_view(request, pk):
    vendor = request.user.vendor_profile
    product = get_object_or_404(Product, pk=pk, vendor=vendor)
    
    if request.method == 'POST':
        form = VendorProductForm(request.POST, request.FILES, instance=product, vendor=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ürün güncellendi.')
            return redirect('vendors:product_list')
    else:
        form = VendorProductForm(instance=product, vendor=vendor)
        
    return render(request, 'vendors/product_form.html', {'form': form, 'title': 'Ürün Düzenle', 'product': product})

@user_passes_test(is_approved_vendor)
def vendor_product_delete_view(request, pk):
    vendor = request.user.vendor_profile
    product = get_object_or_404(Product, pk=pk, vendor=vendor)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Ürün silindi.')
    return redirect('vendors:product_list')

@user_passes_test(is_approved_vendor)
def vendor_orders_view(request):
    vendor = request.user.vendor_profile
    status_filter = request.GET.get('status')
    
    order_items = OrderItem.objects.filter(product__vendor=vendor).select_related('order', 'product')
    if status_filter:
        order_items = order_items.filter(order__status=status_filter)
        
    order_items = order_items.order_by('-order__created_at')
    
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')
        # Note: In a real system, changing order status might affect other vendors in the same order.
        # For simplicity, we assume the vendor can update the status of their part, but actually the status is on the Order model.
        # It's better to update the whole order or handle split orders. We'll update the whole order for now.
        from store.models import Order
        order = get_object_or_404(Order, id=order_id)
        if order.items.filter(product__vendor=vendor).exists():
            order.status = new_status
            order.save()
            messages.success(request, f'Sipariş #{order.id} durumu güncellendi.')
            return redirect('vendors:orders')
            
    return render(request, 'vendors/orders.html', {'order_items': order_items})

@user_passes_test(is_approved_vendor)
def vendor_bulk_upload_view(request):
    # This will be implemented in the next phase
    return render(request, 'vendors/bulk_upload.html')
