import logging
import uuid
from urllib.parse import urljoin
from decimal import Decimal
from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from catalog.models import Product, Variant
from core.models import AuditEvent, StoreSettings
from .models import Cart, CartItem, Coupon, Order, OrderItem, OrderEmail, PaymentMethod, ShippingZone
from .payments import provider_for
from .delivery import normalize_mobile, validate_delivery

logger = logging.getLogger(__name__)
ZERO = Decimal('0.00')

def get_cart(request, create=True):
    guest = None
    key = request.session.get('cart_id')
    if key:
        try:
            guest = Cart.objects.filter(pk=key, user__isnull=True).first()
        except (ValidationError, ValueError):
            pass
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if not cart and (create or guest):
            cart, _ = Cart.objects.get_or_create(user=request.user)
        if cart and guest and guest.pk != cart.pk:
            with transaction.atomic():
                # Deterministic order avoids a deadlock between simultaneous merges.
                list(Cart.objects.select_for_update().filter(pk__in=[cart.pk, guest.pk]).order_by('pk'))
                for item in guest.items.select_related('variant'):
                    target, made = CartItem.objects.get_or_create(cart=cart, variant=item.variant, defaults={'quantity': min(item.quantity, 99)})
                    if not made:
                        target.quantity = min(99, target.quantity + item.quantity)
                        target.save(update_fields=['quantity'])
                guest.delete()
        if cart:
            request.session['cart_id'] = str(cart.pk)
        return cart
    if not guest and create:
        guest = Cart.objects.create()
        request.session['cart_id'] = str(guest.pk)
    return guest

def cart_lines(cart):
    return list(cart.items.select_related('variant__product').prefetch_related('variant__product__images')) if cart else []

def summarize(cart, strict_coupon=False):
    lines = cart_lines(cart)
    subtotal = sum((item.line_total for item in lines), ZERO)
    discount, error = ZERO, ''
    if cart and cart.coupon_code:
        try:
            coupon = Coupon.objects.get(code=cart.coupon_code)
            discount = coupon.discount_for(subtotal)
        except (Coupon.DoesNotExist, ValidationError) as exc:
            error = 'Coupon not found.' if isinstance(exc, Coupon.DoesNotExist) else exc.messages[0]
            if strict_coupon:
                raise ValidationError(error)
    return {'lines': lines, 'subtotal': subtotal, 'discount': discount, 'payable': subtotal - discount,
            'count': sum(x.quantity for x in lines), 'coupon_error': error}

@transaction.atomic
def change_cart(cart, variant_id, quantity, replace=False):
    Cart.objects.select_for_update().get(pk=cart.pk)
    try:
        variant = Variant.objects.select_related('product').get(pk=variant_id, is_active=True, product__status='published')
    except Variant.DoesNotExist:
        raise ValidationError('This watch is no longer available.')
    item = CartItem.objects.filter(cart=cart, variant=variant).first()
    quantity = quantity if replace or not item else item.quantity + quantity
    if quantity == 0 and replace:
        if item:
            item.delete()
        return
    if quantity < 1 or quantity > 99:
        raise ValidationError('Choose a quantity between 1 and 99.')
    if quantity > variant.stock:
        raise ValidationError(f'Only {variant.stock} available in this variant.')
    CartItem.objects.update_or_create(cart=cart, variant=variant, defaults={'quantity': quantity})

@transaction.atomic
def remove_cart_item(cart, item_id):
    Cart.objects.select_for_update().get(pk=cart.pk)
    cart.items.filter(pk=item_id).delete()

@transaction.atomic
def place_order(cart, checkout_key, user, data):
    # Every checkout for this cart serializes on this row, including double clicks.
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    existing = Order.objects.filter(checkout_key=checkout_key).first()
    if existing:
        if existing.source_cart != cart.pk:
            raise ValidationError('Checkout token does not belong to this cart.')
        return existing
    delivery_data = validate_delivery(data)
    normalized_phone = normalize_mobile(data.get('phone'))
    items = list(cart.items.order_by('variant_id'))
    if not items:
        raise ValidationError('Your bag is empty.')
    # Lock products too: inherited prices / publication may be changed by staff.
    product_ids = Variant.objects.filter(pk__in=[i.variant_id for i in items]).values_list('product_id', flat=True)
    list(Product.objects.select_for_update().filter(pk__in=product_ids).order_by('pk'))
    variants = {v.pk: v for v in Variant.objects.select_for_update(of=('self',)).select_related('product').filter(pk__in=[i.variant_id for i in items]).order_by('pk')}
    subtotal = ZERO
    for item in items:
        variant = variants.get(item.variant_id)
        if not variant or not variant.is_active or variant.product.status != 'published':
            raise ValidationError('A watch in your bag is no longer available. Please update your bag.')
        if item.quantity > variant.stock:
            raise ValidationError(f'{variant.product.name}: only {variant.stock} available. Please update your bag.')
        if variant.price <= 0 or variant.price > variant.base_price:
            raise ValidationError('A product price needs review. Please contact the store.')
        subtotal += variant.price * item.quantity
    try:
        zone = ShippingZone.objects.select_for_update().get(pk=data['shipping_zone'].pk, active=True)
        payment = PaymentMethod.objects.select_for_update().get(pk=data['payment_method'].pk, active=True)
    except (ShippingZone.DoesNotExist, PaymentMethod.DoesNotExist):
        raise ValidationError('The selected shipping or payment option is no longer available.')
    if not zone.covers(data['city']):
        raise ValidationError('The selected delivery zone does not cover your city.')
    if payment.code == 'bank' and not payment.instructions.strip():
        raise ValidationError('Bank transfer is not configured. Please choose another payment method.')
    discount, coupon = ZERO, None
    if cart.coupon_code:
        coupon = Coupon.objects.select_for_update().filter(code=cart.coupon_code).first()
        if not coupon:
            raise ValidationError('Coupon no longer exists. Remove it from your bag.')
        discount = coupon.discount_for(subtotal)
    shipping = zone.price_for(subtotal - discount)
    order = Order(
        number=f'KAI-{timezone.localdate():%y%m%d}-{uuid.uuid4().hex[:8].upper()}',
        checkout_key=checkout_key, source_cart=cart.pk,
        user=user if user.is_authenticated else None,
        **{k: data[k] for k in ['name', 'email', 'address', 'postal_code', 'notes']},
        phone=normalized_phone, **delivery_data, landmark=str(data.get('landmark', '')).strip(), map_link=str(data.get('map_link', '')).strip(),
        whatsapp_opt_in=bool(data.get('whatsapp_opt_in')),
        whatsapp_opt_in_at=timezone.now() if data.get('whatsapp_opt_in') else None,
        whatsapp_consent_version='order-updates-v1' if data.get('whatsapp_opt_in') else '',
        delivery_estimate=zone.delivery_estimate or 'Delivery time will be confirmed by the Kairos team.',
        subtotal=subtotal, discount=discount, shipping=shipping, total=subtotal - discount + shipping,
        coupon_code=coupon.code if coupon else '', shipping_name=zone.name,
        payment_method=payment.code, payment_instructions=payment.instructions,
    )
    order.payment_status = provider_for(payment.code).start(order).status
    order.save()
    for item in items:
        variant = variants[item.variant_id]
        changed = Variant.objects.filter(pk=variant.pk, stock__gte=item.quantity).update(stock=F('stock') - item.quantity)
        if changed != 1:
            raise ValidationError('Stock changed during checkout. Please try again.')
        OrderItem.objects.create(order=order, variant=variant, product_name=variant.product.name,
            variant_name=variant.name, sku=variant.sku, quantity=item.quantity,
            unit_price=variant.price, line_total=variant.price * item.quantity)
    if coupon:
        coupon.times_used = F('times_used') + 1
        coupon.save(update_fields=['times_used'])
    cart.items.all().delete()
    cart.coupon_code = ''
    cart.save()
    OrderEmail.objects.create(order=order)
    from .notifications import queue_order_notifications, dispatch_order_notifications
    queue_order_notifications(order)
    transaction.on_commit(lambda: dispatch_order_notifications(order.pk))
    return order

TRANSITIONS = {
    'pending': {'confirmed', 'cancelled'}, 'confirmed': {'processing', 'cancelled'},
    'processing': {'shipped', 'cancelled'}, 'shipped': {'delivered'}, 'delivered': set(), 'cancelled': set(),
}

@transaction.atomic
def transition_order(order_id, status, actor):
    if not actor.is_active or not actor.is_staff or not actor.has_perm('orders.change_order') or not getattr(actor, 'is_verified', lambda: False)():
        raise PermissionDenied
    order = Order.objects.select_for_update().get(pk=order_id)
    old = order.status
    if status == old:
        return order
    if status not in TRANSITIONS[old]:
        raise ValidationError(f'Cannot move an order from {old} to {status}.')
    if status != 'cancelled' and order.payment_method == 'bank' and order.payment_status != 'paid':
        raise ValidationError('An authorized staff member must verify the bank payment first.')
    if status == 'cancelled' and not order.stock_released:
        items = list(order.items.exclude(variant=None).order_by('variant_id'))
        list(Variant.objects.select_for_update().filter(pk__in=[x.variant_id for x in items]).order_by('pk'))
        for item in items:
            Variant.objects.filter(pk=item.variant_id).update(stock=F('stock') + item.quantity)
        order.stock_released = True
    order.status = status
    order.save(update_fields=['status', 'stock_released', 'updated_at'])
    AuditEvent.objects.create(actor=actor, action='order.status', object_label=order.number, details={'from': old, 'to': status})
    return order

@transaction.atomic
def verify_payment(order_id, actor):
    if not actor.is_active or not actor.is_staff or not actor.has_perm('orders.verify_payment') or not getattr(actor, 'is_verified', lambda: False)():
        raise PermissionDenied
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status == 'cancelled':
        raise ValidationError('A cancelled order cannot receive a payment verification.')
    if order.payment_status != 'paid':
        if order.payment_method == 'cod' and order.status != 'delivered':
            raise ValidationError('Mark COD payments received only after delivery.')
        order.payment_status = 'paid'
        order.payment_verified_by = actor
        order.payment_verified_at = timezone.now()
        order.save(update_fields=['payment_status', 'payment_verified_by', 'payment_verified_at', 'updated_at'])
        AuditEvent.objects.create(actor=actor, action='order.payment_verified', object_label=order.number)
    return order

def order_token(order):
    return signing.dumps(str(order.pk), salt='kairos.order-access')

def can_view_order(request, order):
    if request.user.is_authenticated and order.user_id == request.user.pk:
        return True
    # Guest access never expands to an account order.
    if order.user_id is None and str(order.pk) in request.session.get('guest_orders', []):
        return True
    token = request.GET.get('token', '')
    if token and order.user_id is None:
        try:
            return signing.loads(token, salt='kairos.order-access', max_age=7 * 86400) == str(order.pk)
        except signing.BadSignature:
            pass
    return False

def send_confirmation(order_id):
    # Durable outbox: network failures do not undo an already committed purchase.
    try:
        with transaction.atomic():
            delivery = OrderEmail.objects.select_for_update().select_related('order').get(order_id=order_id)
            if delivery.sent_at:
                return
            order = delivery.order
            url = settings.SITE_URL + reverse('orders:detail', args=[order.pk])
            if order.user_id is None:
                url += '?token=' + order_token(order)
            store = StoreSettings.load()
            context = {'order': order, 'store': store, 'order_url': url, 'site_url': settings.SITE_URL,
                       'logo_url': urljoin(settings.SITE_URL + '/', store.logo.url) if store.logo else ''}
            email = EmailMultiAlternatives(f'{order.number} · Your KAIROS order', render_to_string('orders/email.txt', context), settings.DEFAULT_FROM_EMAIL, [order.email])
            email.attach_alternative(render_to_string('orders/email.html', context), 'text/html')
            delivery.attempts += 1
            try:
                email.send(fail_silently=False)
                delivery.sent_at = timezone.now()
                delivery.last_error = ''
            except Exception as exc:
                delivery.last_error = type(exc).__name__
                logger.exception('Order confirmation could not be delivered for %s', order.number)
            delivery.save()
    except Exception:
        logger.exception('Order email outbox failed for %s', order_id)
