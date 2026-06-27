import json
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import (
    Cart,
    CartItem,
    CardBinPrefix,
    CardInstallmentGroup,
    Category,
    CategoryInstallmentRule,
    Coupon,
    CustomerAddress,
    HeroCampaign,
    HomeFeaturedCategory,
    HomeFeaturedProduct,
    Order,
    OrderItem,
    OrderPhoneNotification,
    Product,
    ProductReview,
    Shipment,
    ShipmentEvent,
    ShippingCompany,
    SiteFeedback,
)
from .forms import CheckoutForm, ProductReviewForm, SiteFeedbackForm

MONEY_QUANT = Decimal('0.01')


def notify_admin(subject, message):
    recipient = getattr(settings, 'ADMIN_NOTIFICATION_EMAIL', '')
    if not recipient:
        return
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        fail_silently=True,
    )


def build_absolute_url(request, view_name, *args, **kwargs):
    return request.build_absolute_uri(reverse(view_name, args=args, kwargs=kwargs))


def create_order_notifications(request, order):
    info_link = build_absolute_url(request, 'store:order_info', token=order.public_token)
    message = (
        f'CoreLogic Store siparişiniz alındı. '
        f'Sipariş #{order.id} bilgilendirme linki: {info_link}'
    )
    OrderPhoneNotification.objects.create(
        order=order,
        phone=order.phone,
        message=message,
        tracking_link=info_link,
    )
    notify_admin(
        f'Yeni sipariş #{order.id}',
        (
            f'Yeni sipariş oluşturuldu.\n\n'
            f'Müşteri: {order.user.get_full_name() or order.user.username}\n'
            f'E-posta: {order.user.email}\n'
            f'Telefon: {order.phone}\n'
            f'Tutar: {order.total_amount} TL\n'
            f'Bilgilendirme linki: {info_link}\n\n'
            f'Teslimat adresi:\n{order.shipping_address}'
        ),
    )


def quantize_money(value):
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def get_category_lineage_ids(category):
    ids = []
    seen_ids = set()
    current = category
    while current:
        if current.id in seen_ids:
            break
        seen_ids.add(current.id)
        ids.append(current.id)
        current = current.parent
    return ids


def find_installment_rule(product, card_group, cart_total):
    if not product.category_id:
        return None

    category_ids = get_category_lineage_ids(product.category)
    rules = list(
        CategoryInstallmentRule.objects.filter(
            category_id__in=category_ids,
            card_group=card_group,
            is_active=True,
            min_cart_amount__lte=cart_total,
        ).prefetch_related('rates')
    )
    if not rules:
        return None

    rules.sort(key=lambda rule: (category_ids.index(rule.category_id), -rule.priority, -rule.min_cart_amount))
    return rules[0]


def rate_for_rule(rule, installment_count):
    if not rule or installment_count == 1:
        return Decimal('0')

    for rate in rule.rates.all():
        if rate.installment_count == installment_count:
            return rate.interest_rate_percent
    return Decimal('0')


def build_installment_options(cart, base_total, selected_group_id=None, selected_count=None):
    base_total = quantize_money(base_total)
    cart_items = list(cart.items.select_related('product', 'product__category', 'product__category__parent'))
    groups = list(CardInstallmentGroup.objects.filter(is_active=True).order_by('display_order', 'name'))
    group_options = []

    for group in groups:
        product_rules = []
        max_counts = []
        for item in cart_items:
            rule = find_installment_rule(item.product, group, base_total)
            product_rules.append(rule)
            max_counts.append(rule.max_installments if rule else group.default_max_installments)

        max_installments = max(1, min(max_counts) if max_counts else 1)
        options = []
        for count in range(1, max_installments + 1):
            applicable_rates = [rate_for_rule(rule, count) for rule in product_rules if rule]
            rate_percent = max(applicable_rates) if applicable_rates else Decimal('0')
            total_with_rate = quantize_money(base_total * (Decimal('1') + (rate_percent / Decimal('100'))))
            monthly_amount = quantize_money(total_with_rate / Decimal(count))
            options.append({
                'count': count,
                'rate_percent': rate_percent,
                'total': total_with_rate,
                'monthly': monthly_amount,
            })

        group_options.append({
            'id': group.id,
            'group': group,
            'name': group.name,
            'description': group.description,
            'max_installments': max_installments,
            'options': options,
        })

    selected_group = None
    if group_options:
        fallback_group = next(
            (item for item in group_options if item['group'].is_default_for_unknown_cards),
            group_options[-1],
        )
        selected_group = next(
            (item for item in group_options if str(item['id']) == str(selected_group_id)),
            fallback_group,
        )
        try:
            selected_count = int(selected_count)
        except (TypeError, ValueError):
            selected_count = 1
        selected_option = next(
            (option for option in selected_group['options'] if option['count'] == selected_count),
            selected_group['options'][0],
        )
    else:
        selected_option = {
            'count': 1,
            'rate_percent': Decimal('0'),
            'total': base_total,
            'monthly': base_total,
        }

    return {
        'groups': group_options,
        'selected_group': selected_group,
        'selected_option': selected_option,
        'base_total': base_total,
    }


def validate_installment_selection(cart, base_total, group_id, installment_count):
    plan = build_installment_options(cart, base_total, group_id, installment_count)
    if not plan['groups']:
        return {
            'base_amount': plan['base_total'],
            'total_amount': plan['selected_option']['total'],
            'monthly_amount': plan['selected_option']['monthly'],
            'count': 1,
            'rate_percent': Decimal('0'),
            'card_group': None,
            'card_group_name': 'Tek çekim',
        }

    if not group_id:
        raise ValueError('Kart taksit grubu seçmelisiniz.')

    selected_group = plan['selected_group']
    if str(selected_group['id']) != str(group_id):
        raise ValueError('Seçilen kart grubu geçerli değil.')

    try:
        installment_count = int(installment_count)
    except (TypeError, ValueError):
        raise ValueError('Taksit seçimi geçerli değil.')

    selected_option = next(
        (option for option in selected_group['options'] if option['count'] == installment_count),
        None,
    )
    if selected_option is None:
        raise ValueError('Bu ürünler için seçilen taksit sayısı geçerli değil.')

    return {
        'base_amount': plan['base_total'],
        'total_amount': selected_option['total'],
        'monthly_amount': selected_option['monthly'],
        'count': selected_option['count'],
        'rate_percent': selected_option['rate_percent'],
        'card_group': selected_group['group'],
        'card_group_name': selected_group['name'],
    }


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

@ensure_csrf_cookie
def home_view(request):
    now = timezone.now()
    campaigns = HeroCampaign.objects.filter(is_active=True).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(ends_at__isnull=True) | Q(ends_at__gte=now),
    )[:8]

    featured_slots = HomeFeaturedProduct.objects.filter(
        is_active=True,
        product__is_active=True,
        product__is_approved=True,
    ).select_related('product', 'product__vendor', 'product__category')[:12]
    featured_product_cards = [
        {
            'product': slot.product,
            'title': slot.title_override or slot.product.name,
        }
        for slot in featured_slots
    ]

    if not featured_product_cards:
        fallback_products = Product.objects.filter(
            is_active=True,
            is_approved=True,
        ).select_related('vendor', 'category')[:12]
        featured_product_cards = [
            {
                'product': product,
                'title': product.name,
            }
            for product in fallback_products
        ]

    category_slots = HomeFeaturedCategory.objects.filter(
        is_active=True,
        category__is_active=True,
    ).select_related('category')[:8]
    featured_category_cards = [
        {
            'category': slot.category,
            'label': slot.label_override or slot.category.name,
        }
        for slot in category_slots
    ]

    if not featured_category_cards:
        fallback_categories = Category.objects.filter(
            is_active=True,
            parent__isnull=True,
        )[:8]
        featured_category_cards = [
            {
                'category': category,
                'label': category.name,
            }
            for category in fallback_categories
        ]

    return render(request, 'store/home.html', {
        'campaigns': campaigns,
        'featured_product_cards': featured_product_cards,
        'featured_category_cards': featured_category_cards,
    })

@ensure_csrf_cookie
def product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True, is_approved=True)
    reviews = product.reviews.filter(is_approved=True).select_related('user')
    review_form = ProductReviewForm()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.warning(request, 'Yorum yazmak için giriş yapmalısınız.')
            return redirect(f"{reverse('accounts:login')}?next={request.path}")

        existing_review = ProductReview.objects.filter(product=product, user=request.user).first()
        review_form = ProductReviewForm(request.POST, instance=existing_review)
        if review_form.is_valid():
            review = review_form.save(commit=False)
            review.product = product
            review.user = request.user
            review.is_approved = True
            review.save()
            notify_admin(
                'Yeni ürün yorumu',
                (
                    f'Ürün: {product.name}\n'
                    f'Kullanıcı: {request.user.get_full_name() or request.user.username}\n'
                    f'Puan: {review.rating}/5\n\n'
                    f'{review.comment}'
                ),
            )
            messages.success(request, 'Yorumunuz yayınlandı. Teşekkür ederiz.')
            return redirect('store:product_detail', slug=product.slug)

    return render(request, 'store/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'review_form': review_form,
    })

@ensure_csrf_cookie
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

@ensure_csrf_cookie
def search_view(request):
    query = request.GET.get('q', '')
    products = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query),
        is_active=True, is_approved=True
    ) if query else []
    return render(request, 'store/search_results.html', {'query': query, 'products': products})

def payment_tracker_view(request):
    return render(request, 'store/payment_tracker.html')

@ensure_csrf_cookie
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
    final_total = quantize_money(final_total)

    def checkout_context(active_form):
        installment_plan = build_installment_options(
            cart,
            final_total,
            request.POST.get('payment_card_group') if request.method == 'POST' else None,
            request.POST.get('installment_count') if request.method == 'POST' else None,
        )
        bin_prefixes = [
            {
                'prefix': item.prefix,
                'bank_name': item.bank_name,
                'group_id': item.card_group_id,
                'group_name': item.card_group.name,
            }
            for item in CardBinPrefix.objects.filter(
                is_active=True,
                card_group__is_active=True,
            ).select_related('card_group').order_by('-prefix')
        ]
        return {
            'form': active_form,
            'cart': cart,
            'addresses': request.user.saved_addresses.all(),
            'discount_amount': discount_amount,
            'final_total': final_total,
            'installment_groups': installment_plan['groups'],
            'selected_installment_group': installment_plan['selected_group'],
            'selected_installment': installment_plan['selected_option'],
            'default_installment_group_id': installment_plan['selected_group']['id'] if installment_plan['selected_group'] else '',
            'card_bin_prefixes': bin_prefixes,
        }

    default_address = request.user.saved_addresses.first()
    initial = {
        'shipping_recipient_name': request.user.get_full_name() or request.user.username,
        'phone': request.user.phone,
        'shipping_city': request.user.city,
        'shipping_address': request.user.address,
        'billing_full_name': request.user.get_full_name() or request.user.username,
        'billing_email': request.user.email,
        'billing_phone': request.user.phone,
        'billing_address': request.user.address,
        'billing_type': Order.BillingType.INDIVIDUAL,
        'billing_same_as_shipping': True,
        'save_address': not request.user.saved_addresses.exists(),
    }
    if default_address:
        initial.update({
            'address_id': default_address.pk,
            'address_title': default_address.title,
            'shipping_recipient_name': default_address.recipient_name,
            'phone': default_address.phone,
            'shipping_city': default_address.city,
            'shipping_district': default_address.district,
            'shipping_postal_code': default_address.postal_code,
            'shipping_address': default_address.address_line,
        })

    if request.method == 'POST':
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            action = form.cleaned_data.get('address_action') or CheckoutForm.ADDRESS_ACTION_PLACE_ORDER
            if action != CheckoutForm.ADDRESS_ACTION_PLACE_ORDER:
                form.save_address_record(request.user)
                if action == CheckoutForm.ADDRESS_ACTION_DELETE:
                    messages.success(request, 'Adres silindi.')
                elif action == CheckoutForm.ADDRESS_ACTION_UPDATE:
                    messages.success(request, 'Adres güncellendi.')
                else:
                    messages.success(request, 'Adres kaydedildi.')
                return redirect('store:checkout')

            # Check stock one last time
            for item in cart.items.all():
                if item.product.stock < item.quantity:
                    form.add_error(None, f"{item.product.name} için yeterli stok yok (Mevcut: {item.product.stock}).")
                    return render(request, 'store/checkout.html', checkout_context(form))

            try:
                installment = validate_installment_selection(
                    cart,
                    final_total,
                    request.POST.get('payment_card_group'),
                    request.POST.get('installment_count'),
                )
            except ValueError as exc:
                form.add_error(None, str(exc))
                return render(request, 'store/checkout.html', checkout_context(form))
            
            order = form.build_order(request.user, installment['total_amount'], coupon, installment)
            if coupon:
                coupon.times_used += 1
                coupon.save()
            order.save()

            corejet, _ = ShippingCompany.objects.get_or_create(
                code='CJ',
                defaults={
                    'name': 'CoreJet',
                    'support_phone': '0850 255 00 00',
                    'tracking_url': '',
                    'is_active': True,
                },
            )
            shipment, shipment_created = Shipment.objects.get_or_create(
                order=order,
                defaults={
                    'company': corejet,
                    'status': Shipment.Status.CREATED,
                    'note': 'Sipariş kargo hazırlık sürecine alındı.',
                },
            )
            if shipment_created:
                ShipmentEvent.objects.create(
                    shipment=shipment,
                    status=Shipment.Status.CREATED,
                    description='CoreJet kargo kaydı oluşturuldu.',
                )
            
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

            create_order_notifications(request, order)
            return redirect('store:order_success', order_id=order.id)
    else:
        form = CheckoutForm(initial=initial, user=request.user)
        
    return render(request, 'store/checkout.html', checkout_context(form))

@login_required
def order_success_view(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('shipment', 'shipment__company', 'shipment__current_station').prefetch_related('items'),
        id=order_id,
        user=request.user,
    )
    return render(request, 'store/order_success.html', {'order': order})


def order_info_view(request, token):
    order = get_object_or_404(
        Order.objects.select_related(
            'user',
            'shipment',
            'shipment__company',
            'shipment__current_station',
        ).prefetch_related('items', 'shipment__events'),
        public_token=token,
    )
    return render(request, 'store/order_info.html', {'order': order})


def feedback_view(request):
    initial = {}
    if request.user.is_authenticated:
        initial = {
            'name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
        }

    if request.method == 'POST':
        form = SiteFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            if request.user.is_authenticated:
                feedback.user = request.user
            feedback.save()
            notify_admin(
                'Yeni geri bildirim',
                (
                    f'Konu: {feedback.get_topic_display()}\n'
                    f'Gönderen: {feedback.name} <{feedback.email}>\n\n'
                    f'{feedback.message}'
                ),
            )
            messages.success(request, 'Geri bildiriminiz bize ulaştı. Teşekkür ederiz.')
            return redirect('store:feedback')
    else:
        form = SiteFeedbackForm(initial=initial)

    return render(request, 'store/feedback.html', {'form': form})
