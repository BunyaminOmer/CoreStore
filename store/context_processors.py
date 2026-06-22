from __future__ import annotations

from django.http import HttpRequest

from store.models import Cart, Category


def cart_context(request: HttpRequest) -> dict:
    """
    Inject the current user's cart and item count into every template context.
    Works for both authenticated users (lookup by user) and anonymous visitors
    (lookup by session key).
    """
    cart = None

    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user, is_active=True).first()
        else:
            session_key = request.session.session_key
            if session_key:
                cart = Cart.objects.filter(
                    session_key=session_key, is_active=True
                ).first()
    except Exception:
        # Models may not be migrated yet or table doesn't exist
        pass

    if cart:
        return {
            'cart_count': cart.total_items,
            'cart': cart,
        }

    return {
        'cart_count': 0,
        'cart': None,
    }


def categories_context(request: HttpRequest) -> dict:
    """
    Inject all active root categories into every template context so they are
    available for navigation menus, sidebars, etc.
    """
    try:
        categories = Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related('children')
    except Exception:
        # Models may not be migrated yet or table doesn't exist
        categories = []

    return {
        'categories': categories,
    }
