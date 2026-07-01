from __future__ import annotations

from django.core.cache import cache
from django.http import HttpRequest
from django.db.models import Sum

from store.models import Cart, Category, Notification


CATEGORIES_CACHE_KEY = 'navigation:root-categories:v1'
CATEGORIES_CACHE_TIMEOUT = 10 * 60


def cart_context(request: HttpRequest) -> dict:
    """
    Inject the current user's cart and item count into every template context.
    Works for both authenticated users (lookup by user) and anonymous visitors
    (lookup by session key).
    """
    cart = None
    cart_count = 0

    try:
        if request.user.is_authenticated:
            cart = (
                Cart.objects.filter(user=request.user)
                .annotate(total_quantity=Sum('items__quantity'))
                .order_by('-updated_at')
                .first()
            )
        else:
            session_key = request.session.session_key
            if session_key:
                cart = (
                    Cart.objects.filter(session_key=session_key)
                    .annotate(total_quantity=Sum('items__quantity'))
                    .order_by('-updated_at')
                    .first()
                )
        if cart:
            cart_count = cart.total_quantity or 0
    except Exception:
        # Models may not be migrated yet or table doesn't exist
        pass

    return {
        'cart_count': cart_count,
        'cart': cart,
    }


def categories_context(request: HttpRequest) -> dict:
    """
    Inject all active root categories into every template context so they are
    available for navigation menus, sidebars, etc.
    """
    try:
        categories = cache.get(CATEGORIES_CACHE_KEY)
        if categories is None:
            categories = list(
                Category.objects.filter(is_active=True, parent__isnull=True)
                .prefetch_related('children__children')
                .order_by('name')
            )
            cache.set(CATEGORIES_CACHE_KEY, categories, CATEGORIES_CACHE_TIMEOUT)
    except Exception:
        # Models may not be migrated yet or table doesn't exist
        categories = []

    return {
        'categories': categories,
    }


def notifications_context(request: HttpRequest) -> dict:
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'unread_notification_count': 0}
    try:
        count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
    except Exception:
        count = 0
    return {'unread_notification_count': count}
