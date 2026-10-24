from django import template
from decimal import Decimal
import json
from django.utils.safestring import mark_safe
register = template.Library()

@register.filter
def money(value):
    try:
        return f'PKR {Decimal(value):,.0f}' if Decimal(value) % 1 == 0 else f'PKR {Decimal(value):,.2f}'
    except (ValueError, TypeError, ArithmeticError):
        return 'PKR —'

@register.simple_tag(takes_context=True)
def query_string(context, **kwargs):
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return '?' + query.urlencode()

@register.filter
def saved(product, ids):
    return product.pk in ids

@register.filter
def jsonld(value):
    return mark_safe(json.dumps(value).replace('<', '\\u003C').replace('>', '\\u003E').replace('&', '\\u0026'))
