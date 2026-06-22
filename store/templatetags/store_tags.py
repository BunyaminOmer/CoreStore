from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter(name='currency')
def currency(value) -> str:
    """
    Format a numeric value as Turkish Lira currency.

    Usage in templates:
        {{ product.price|currency }}  ->  ₺1.234,56
    """
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return '₺0,00'

    # Format with 2 decimal places, thousands separator
    # Turkish format: dot for thousands, comma for decimal
    formatted = f'{amount:,.2f}'
    # Swap separators: comma -> @ -> dot, dot -> comma, @ -> dot
    formatted = formatted.replace(',', '@').replace('.', ',').replace('@', '.')
    return f'₺{formatted}'


@register.filter(name='multiply')
def multiply(value, arg):
    """
    Multiply a value by an argument. Useful for template calculations
    like subtotals (price * quantity).

    Usage in templates:
        {{ item.price|multiply:item.quantity }}
    """
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (InvalidOperation, TypeError, ValueError):
        return 0
