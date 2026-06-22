import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from .models import Category, Product, Cart, CartItem, Order, OrderItem, Coupon
from .forms import CheckoutForm

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        # Merge session cart if exists
        session_key = request.session.session_key
        if session_key:
            session_carts = Cart.objects.filter(session_key=session_key, user__isnull=True)
            for s_cart in session_carts:
                for item in s_cart.items.all():
                    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=item.product)
                    if not item_created:
                        cart_item.quantity += item.quantity
                        cart_item.save()
                s_cart.delete()
        return cart
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key, user__isnull=True)
        return cart

def home_view(request):
    products = Product.objects.filter(is_active=True, is_approved=True).select_related('vendor', 'category')[:12]
    return render(request, 'store/home.html', {'products': products})

def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True, is_approved=True)
    return render(request, 'store/product_detail.html', {'product': product})

def category_products_view(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # Include products from this category and its active subcategories
    categories = [category]
    categories.extend(category.children.filter(is_active=True))
    
    products = Product.objects.filter(
        category__in=categories, 
        is_active=True, 
        is_approved=True
    ).select_related('vendor', 'category')
    
    return render(request, 'store/category.html', {'category': category, 'products': products})

def search_view(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query),
        is_active=True, is_approved=True
    ) if query else []
    return render(request, 'store/search_results.html', {'query': query, 'products': products})

def cart_view(request):
    cart = get_or_create_cart(request)
    return render(request, 'store/cart.html', {'cart': cart})

def add_to_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        if product.stock < quantity:
            return JsonResponse({'status': 'error', 'message': 'Yeterli stok yok.'}, status=400)
            
        cart = get_or_create_cart(request)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
            
        cart_item.save()
        return JsonResponse({
            'status': 'success', 
            'cart_count': cart.total_items,
            'message': 'Ürün sepete eklendi.'
        })
    return JsonResponse({'status': 'error'}, status=400)

def update_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        if quantity > 0:
            if cart_item.product.stock < quantity:
                return JsonResponse({'status': 'error', 'message': 'Yeterli stok yok.'}, status=400)
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
            
        return JsonResponse({
            'status': 'success',
            'cart_count': cart.total_items,
            'cart_total': cart.total_price,
            'item_subtotal': cart_item.line_total if quantity > 0 else 0
        })
    return JsonResponse({'status': 'error'}, status=400)

def remove_from_cart(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        cart = get_or_create_cart(request)
        CartItem.objects.filter(id=item_id, cart=cart).delete()
        
        return JsonResponse({
            'status': 'success',
            'cart_count': cart.total_items,
            'cart_total': cart.total_price
        })
    return JsonResponse({'status': 'error'}, status=400)

def apply_coupon(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        code = data.get('code')
        cart = get_or_create_cart(request)
        
        try:
            coupon = Coupon.objects.get(code__iexact=code)
            if not coupon.is_valid:
                return JsonResponse({'status': 'error', 'message': 'Geçersiz veya süresi dolmuş kupon.'}, status=400)
                
            discount_amount = (cart.total_price * coupon.discount_percent) / 100
            final_total = cart.total_price - discount_amount
            
            # Save coupon to session for checkout
            request.session['coupon_id'] = coupon.id
            
            return JsonResponse({
                'status': 'success',
                'discount_amount': discount_amount,
                'final_total': final_total,
                'message': f'%{coupon.discount_percent} indirim uygulandı!'
            })
        except Coupon.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Kupon bulunamadı.'}, status=404)
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def checkout_view(request):
    cart = get_or_create_cart(request)
    if cart.total_items == 0:
        return redirect('store:cart')
        
    coupon_id = request.session.get('coupon_id')
    coupon = None
    discount_amount = 0
    final_total = cart.total_price
    
    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            if coupon.is_valid:
                discount_amount = (cart.total_price * coupon.discount_percent) / 100
                final_total = cart.total_price - discount_amount
        except Coupon.DoesNotExist:
            pass

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Check stock one last time
            for item in cart.items.all():
                if item.product.stock < item.quantity:
                    form.add_error(None, f"{item.product.name} için yeterli stok yok (Mevcut: {item.product.stock}).")
                    return render(request, 'store/checkout.html', {'form': form, 'cart': cart})
            
            order = form.save(commit=False)
            order.user = request.user
            order.total_amount = final_total
            if coupon:
                order.coupon = coupon
                coupon.times_used += 1
                coupon.save()
            order.save()
            
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    price=item.product.effective_price
                )
                # Deduct stock
                item.product.stock -= item.quantity
                item.product.save()
                
            # Clear cart and session
            cart.delete()
            if 'coupon_id' in request.session:
                del request.session['coupon_id']
                
            return redirect('store:order_success', order_id=order.id)
    else:
        form = CheckoutForm(initial={
            'shipping_address': request.user.address,
            'phone': request.user.phone
        })
        
    return render(request, 'store/checkout.html', {
        'form': form,
        'cart': cart,
        'discount_amount': discount_amount,
        'final_total': final_total
    })

@login_required
def order_success_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_success.html', {'order': order})
