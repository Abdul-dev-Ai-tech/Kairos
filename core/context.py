from django.conf import settings
from catalog.models import Collection, Wishlist
from orders.models import Cart
from django.db.models import Sum
from .models import StoreSettings

def store_context(request):
    # No cart creation on read-only navigation.
    if request.user.is_authenticated:
        count = Cart.objects.filter(user=request.user).aggregate(n=Sum('items__quantity'))['n'] or 0
        saved = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
    else:
        cart_key = request.session.get('cart_id')
        count = Cart.objects.filter(pk=cart_key, user=None).aggregate(n=Sum('items__quantity'))['n'] or 0 if cart_key else 0
        saved = request.session.get('wishlist', [])
    return {'store': StoreSettings.load(), 'nav_collections': Collection.objects.all(),
            'cart_count': count, 'wishlist_ids': saved, 'site_url': settings.SITE_URL,
            'canonical_url': settings.SITE_URL + request.path}
