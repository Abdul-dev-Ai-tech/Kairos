import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST, require_GET
from core.utils import safe_redirect
from .forms import CartForm, CheckoutForm, CouponForm, ShippingQuoteForm
from .models import Coupon, Order, PaymentMethod, ShippingZone
from .services import get_cart, summarize, change_cart, remove_cart_item, place_order, can_view_order

def cart(request):
    bag = get_cart(request, create=False)
    return render(request, 'orders/cart.html', {'cart': bag, **summarize(bag)})

@require_GET
def cart_summary(request):
    bag = get_cart(request, create=False)
    summary = summarize(bag)
    return JsonResponse({'count': summary['count'], 'html': render_to_string('orders/drawer.html', {'cart': bag, **summary}, request)})

@require_POST
def cart_change(request):
    form = CartForm(request.POST)
    error = ''
    if form.is_valid():
        try:
            bag = get_cart(request)
            change_cart(bag, form.cleaned_data['variant_id'], form.cleaned_data['quantity'], replace=request.POST.get('replace') == '1')
        except ValidationError as exc:
            error = exc.messages[0]
    else:
        error = 'Choose a valid variant and quantity.'
    if request.headers.get('Accept') == 'application/json':
        if error:
            return JsonResponse({'error': error}, status=400)
        return JsonResponse({'message': 'Your bag has been updated.', 'count': summarize(bag)['count']})
    if error:
        messages.error(request, error)
    else:
        messages.success(request, 'Your bag has been updated.')
        if request.POST.get('buy_now'):
            return redirect('orders:checkout')
    return safe_redirect(request, '/bag/')

@require_POST
def cart_remove(request, item_id):
    bag = get_cart(request, create=False)
    if bag:
        remove_cart_item(bag, item_id)
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'message': 'Item removed.', 'count': summarize(bag)['count']})
    return redirect('orders:cart')

@require_POST
def coupon_apply(request):
    bag = get_cart(request)
    form = CouponForm(request.POST)
    if request.POST.get('remove') == '1':
        bag.coupon_code = ''
        bag.save()
        messages.success(request, 'Coupon removed.')
    elif form.is_valid():
        try:
            coupon = Coupon.objects.get(code=form.cleaned_data['code'].upper())
            coupon.discount_for(summarize(bag)['subtotal'])
            bag.coupon_code = coupon.code
            bag.save()
            messages.success(request, 'Coupon applied.')
        except (Coupon.DoesNotExist, ValidationError) as exc:
            messages.error(request, 'Coupon not found.' if isinstance(exc, Coupon.DoesNotExist) else exc.messages[0])
    else:
        messages.error(request, 'Enter a valid coupon code.')
    return redirect('orders:cart')

def checkout(request):
    bag = get_cart(request)
    key = request.session.get('checkout_key')
    if not key:
        key = str(uuid.uuid4())
        request.session['checkout_key'] = key
    initial = {'checkout_key': key}
    if request.user.is_authenticated:
        initial.update(name=request.user.get_full_name(), email=request.user.email)
    form = CheckoutForm(request.POST or None, initial=initial)
    # A repeated successful POST is allowed even after the cart was emptied.
    existing = Order.objects.filter(checkout_key=key, source_cart=bag.pk).first()
    if request.method == 'POST' and form.is_valid():
        if str(form.cleaned_data['checkout_key']) != key:
            form.add_error(None, 'Your checkout session changed. Refresh this page and try again.')
        else:
            try:
                order = place_order(bag, form.cleaned_data['checkout_key'], request.user, form.cleaned_data)
            except ValidationError as exc:
                form.add_error(None, exc.messages[0])
            else:
                if not order.user_id:
                    request.session['guest_orders'] = list(dict.fromkeys(request.session.get('guest_orders', []) + [str(order.pk)]))[-30:]
                return redirect('orders:detail', order_id=order.pk)
    elif request.method == 'GET' and not bag.items.exists():
        if existing:
            return redirect('orders:detail', order_id=existing.pk)
        messages.info(request, 'Add a watch to your bag to begin checkout.')
        return redirect('orders:cart')
    elif request.method == 'GET' and existing:
        # A fresh bag after a purchase gets a fresh idempotency token.
        key = str(uuid.uuid4())
        request.session['checkout_key'] = key
        form = CheckoutForm(initial={**initial, 'checkout_key': key})
    return render(request, 'orders/checkout.html', {'form': form, 'cart': bag, **summarize(bag),
        'payment_methods': PaymentMethod.objects.filter(active=True), 'shipping_zones': ShippingZone.objects.filter(active=True)})

@require_POST
def quote(request):
    form = ShippingQuoteForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': 'Choose a delivery zone that covers your city.'}, status=400)
    bag = get_cart(request, create=False)
    try:
        summary = summarize(bag, strict_coupon=True)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)
    shipping = form.cleaned_data['shipping_zone'].price_for(summary['payable'])
    return JsonResponse({'shipping': str(shipping), 'total': str(summary['payable'] + shipping),
                         'estimate': form.cleaned_data['shipping_zone'].delivery_estimate})

def detail(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items'), pk=order_id)
    if not can_view_order(request, order):
        raise Http404
    return render(request, 'orders/detail.html', {'order': order})

def receipt(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items'), pk=order_id)
    if not can_view_order(request, order):
        raise Http404
    return render(request, 'orders/receipt.html', {'order': order})

@login_required
def history(request):
    page = Paginator(Order.objects.filter(user=request.user), 10).get_page(request.GET.get('page'))
    return render(request, 'orders/history.html', {'page_obj': page})
