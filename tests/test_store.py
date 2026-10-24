import io
import uuid
import re
from urllib.parse import urlsplit
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.oath import totp
from catalog.models import Collection, Category, Brand, Product, Variant, ProductImage
from core.models import AuditEvent, StoreSettings
from core.uploads import validate_image
from orders.models import Cart, CartItem, Coupon, Order, ShippingZone, PaymentMethod, OrderEmail
from orders.services import change_cart, place_order, summarize, transition_order, verify_payment, order_token, send_confirmation
from orders.admin import csv_safe

User = get_user_model()
PASSWORD = 'TestingOnly-Secure-2042!'

def photo(name='watch.png', size=(60, 80)):
    output = io.BytesIO()
    Image.new('RGB', size, '#cab68e').save(output, 'PNG')
    return SimpleUploadedFile(name, output.getvalue(), content_type='image/png')

def fixtures():
    men = Collection.objects.create(name='Men', slug='men')
    women = Collection.objects.create(name='Women', slug='women')
    category = Category.objects.create(name='Watches', slug='watches')
    brand = Brand.objects.create(name='Demo brand', slug='demo')
    product = Product.objects.create(name='Test Watch', slug='test-watch', sku='TEST', brand=brand, category=category, collection=men,
        description='Test-only demonstration watch.', regular_price='1000.00', status='published', strap_material='Leather', movement_type='Quartz')
    variant = Variant.objects.create(product=product, name='Black', sku='TEST-BLACK', stock=3)
    other = Variant.objects.create(product=product, name='Ivory', sku='TEST-IVORY', stock=2, regular_price='1250.25')
    shipping = ShippingZone.objects.create(name='Lahore', cities='Lahore', charge='250.00', free_above='5000.00')
    cod = PaymentMethod.objects.create(code='cod', name='Cash on delivery', active=True)
    bank = PaymentMethod.objects.create(code='bank', name='Bank transfer', active=True, instructions='TEST ONLY: do not transfer money.')
    coupon = Coupon.objects.create(code='TEN', value='10.00', minimum_order=1000, expires_at=timezone.now()+timedelta(days=1), usage_limit=1)
    return men, women, category, brand, product, variant, other, shipping, cod, bank, coupon

class StoreTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        (cls.men, cls.women, cls.category, cls.brand, cls.product, cls.variant, cls.other,
         cls.shipping, cls.cod, cls.bank, cls.coupon) = fixtures()
        cls.customer = User.objects.create_user(username='customer@example.test', email='customer@example.test', password=PASSWORD)
        cls.stranger = User.objects.create_user(username='other@example.test', email='other@example.test', password=PASSWORD)
        cls.owner = User.objects.create_superuser(username='owner@example.test', email='owner@example.test', password=PASSWORD)
        StoreSettings.load()

    def make_cart(self, variant=None, quantity=1, user=None):
        cart = Cart.objects.create(user=user)
        change_cart(cart, (variant or self.variant).pk, quantity)
        return cart

    def data(self, payment=None):
        return {'name': 'Test Customer', 'email': 'buyer@example.test', 'phone': '03000000000',
                'address': 'Test address for automated QA only', 'city': 'Lahore', 'area': 'Johar Town', 'postal_code': '54000',
                'notes': 'AUTOMATED TEST', 'shipping_zone': self.shipping, 'payment_method': payment or self.cod}

    def buy(self, cart=None, payment=None, user=None, key=None):
        return place_order(cart or self.make_cart(), key or uuid.uuid4(), user or AnonymousUser(), self.data(payment))

    def verified_owner(self):
        self.owner.is_verified = lambda: True
        return self.owner

    def admin_login(self):
        device = TOTPDevice.objects.create(user=self.owner, name='default', confirmed=True)
        self.client.force_login(self.owner, backend='django.contrib.auth.backends.ModelBackend')
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

    def test_home_shop_detail_and_filters_render(self):
        for url in ['/', '/shop/', '/watch/test-watch/', '/collections/men/', '/new-arrivals/', '/featured/', '/search/?q=Watch', '/wishlist/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_only_published_products_are_visible(self):
        self.product.status = 'draft'; self.product.save()
        self.assertNotContains(self.client.get('/shop/'), 'Test Watch')
        self.assertEqual(self.client.get('/watch/test-watch/').status_code, 404)

    def test_variant_prices_drive_price_filter(self):
        self.assertContains(self.client.get('/shop/?min_price=900&max_price=1100'), 'Test Watch')
        self.assertNotContains(self.client.get('/shop/?min_price=1100'), 'Test Watch')

    def test_invalid_price_range_has_explanatory_error(self):
        response = self.client.get('/shop/?min_price=2000&max_price=100')
        self.assertContains(response, 'Minimum price must be less')

    def test_price_sort_uses_override_not_parent_sale(self):
        # A variant with its own regular price does not inherit a parent sale.
        self.product.sale_price = '750.00'; self.product.save()
        self.variant.is_active = False; self.variant.save()
        self.assertContains(self.client.get('/shop/?min_price=1200'), 'Test Watch')

    def test_availability_filter_uses_active_variant_stock(self):
        Variant.objects.update(stock=0)
        self.assertNotContains(self.client.get('/shop/?availability=in_stock'), 'Test Watch')
        self.assertContains(self.client.get('/shop/?availability=out_of_stock'), 'Test Watch')

    def test_shared_filter_urls_are_preserved_in_pagination(self):
        for number in range(11):
            p = Product.objects.create(name=f'Example {number}', slug=f'example-{number}', sku=f'E{number}', category=self.category,
                collection=self.men, description='test', regular_price=1000, status='published', strap_material='Leather')
            Variant.objects.create(product=p, sku=f'EV{number}', stock=1)
        response = self.client.get('/shop/?strap=Leather&sort=price_asc')
        self.assertContains(response, 'strap=Leather&amp;sort=price_asc&amp;page=2')

    def test_add_cart_and_reject_more_than_stock(self):
        cart = self.make_cart(quantity=2)
        with self.assertRaises(ValidationError):
            change_cart(cart, self.variant.pk, 2)
        self.assertEqual(cart.items.get().quantity, 2)

    def test_cart_rejects_negative_and_excessive_quantity(self):
        cart = Cart.objects.create()
        for quantity in [-1, 0, 100]:
            with self.assertRaises(ValidationError):
                change_cart(cart, self.variant.pk, quantity)

    def test_guest_cart_persists_and_merges_at_login(self):
        self.client.post('/bag/change/', {'variant_id': self.variant.pk, 'quantity': 1})
        self.assertContains(self.client.get('/bag/'), 'Test Watch')
        cart = self.make_cart(quantity=1, user=self.customer)
        response = self.client.post('/accounts/login/', {'username': self.customer.email, 'password': PASSWORD})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(cart.items.get().quantity, 2)

    def test_cart_remove_cannot_remove_another_session_item(self):
        other = self.make_cart()
        self.client.post('/bag/change/', {'variant_id': self.other.pk, 'quantity': 1})
        self.client.post(f'/bag/remove/{other.items.get().pk}/')
        self.assertEqual(other.items.count(), 1)

    def test_cart_change_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/bag/change/', {'variant_id': self.variant.pk, 'quantity': 1}).status_code, 403)

    def test_valid_coupon_discount_is_decimal_and_capped(self):
        self.assertEqual(self.coupon.discount_for(Decimal('1250.25')), Decimal('125.03'))
        self.coupon.kind = 'fixed'; self.coupon.value = Decimal('5000')
        self.assertEqual(self.coupon.discount_for(Decimal('1000')), Decimal('1000.00'))

    def test_coupon_rejects_expiry_usage_and_minimum(self):
        for changes in [{'expires_at': timezone.now()-timedelta(seconds=1)}, {'times_used': 1}, {'minimum_order': 2000}, {'active': False}]:
            coupon = Coupon.objects.get(pk=self.coupon.pk)
            for key, value in changes.items(): setattr(coupon, key, value)
            with self.assertRaises(ValidationError): coupon.discount_for(Decimal('1000'))

    def test_invalid_coupon_not_applied(self):
        self.client.post('/bag/change/', {'variant_id': self.variant.pk, 'quantity': 1})
        self.client.post('/bag/coupon/', {'code': 'INVALID'})
        cart = Cart.objects.get(pk=self.client.session['cart_id'])
        self.assertEqual(cart.coupon_code, '')

    def test_server_totals_and_variant_order_snapshot(self):
        cart = self.make_cart(variant=self.other, quantity=2)
        cart.coupon_code = self.coupon.code; cart.save()
        order = self.buy(cart)
        self.assertEqual(order.subtotal, Decimal('2500.50'))
        self.assertEqual(order.discount, Decimal('250.05'))
        self.assertEqual(order.total, Decimal('2500.45'))
        item = order.items.get()
        self.assertEqual(item.sku, 'TEST-IVORY')
        self.other.regular_price = '9000.00'; self.other.save()
        self.product.name = 'Changed later'; self.product.save()
        item.refresh_from_db()
        self.assertEqual(item.product_name, 'Test Watch')
        self.assertEqual(item.unit_price, Decimal('1250.25'))

    def test_checkout_is_idempotent(self):
        cart = self.make_cart(); key = uuid.uuid4()
        first = self.buy(cart, key=key); second = self.buy(cart, key=key)
        self.assertEqual(first.pk, second.pk)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 2)
        self.assertEqual(Order.objects.count(), 1)

    def test_idempotency_key_cannot_be_reused_for_another_cart(self):
        key = uuid.uuid4(); self.buy(key=key)
        with self.assertRaises(ValidationError): self.buy(key=key)

    def test_stock_is_revalidated_and_rolls_back(self):
        cart = self.make_cart(quantity=2)
        self.variant.stock = 1; self.variant.save()
        with self.assertRaises(ValidationError): self.buy(cart)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(cart.items.get().quantity, 2)

    def test_inactive_payment_and_wrong_city_rejected(self):
        cart = self.make_cart(); self.cod.active = False; self.cod.save()
        with self.assertRaises(ValidationError): self.buy(cart)
        self.cod.active = True; self.cod.save()
        data = self.data(); data['city'] = 'Karachi'
        with self.assertRaises(ValidationError): place_order(cart, uuid.uuid4(), AnonymousUser(), data)

    def test_expired_coupon_blocks_checkout_without_consuming_stock(self):
        cart = self.make_cart(); cart.coupon_code = 'TEN'; cart.save()
        self.coupon.expires_at = timezone.now()-timedelta(days=1); self.coupon.save()
        with self.assertRaises(ValidationError): self.buy(cart)
        self.variant.refresh_from_db(); self.assertEqual(self.variant.stock, 3)

    def test_valid_coupon_usage_incremented_only_once(self):
        cart = self.make_cart(); cart.coupon_code = 'TEN'; cart.save(); key = uuid.uuid4()
        self.buy(cart, key=key); self.buy(cart, key=key)
        self.coupon.refresh_from_db(); self.assertEqual(self.coupon.times_used, 1)

    def test_full_guest_checkout_and_duplicate_post(self):
        self.client.post('/bag/change/', {'variant_id': self.other.pk, 'quantity': 1})
        response = self.client.get('/checkout/'); self.assertEqual(response.status_code, 200)
        data = {**self.data(), 'shipping_zone': self.shipping.pk, 'payment_method': self.cod.pk,
            'checkout_key': self.client.session['checkout_key'], 'agreement': 'on', 'total': '0.01', 'unit_price': '0.01'}
        response = self.client.post('/checkout/', data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.get().total, Decimal('1500.25'))
        self.assertEqual(self.client.get(response.url).status_code, 200)
        self.client.post('/checkout/', data)
        self.assertEqual(Order.objects.count(), 1)

    def test_client_cannot_change_checkout_token(self):
        self.client.post('/bag/change/', {'variant_id': self.variant.pk, 'quantity': 1}); self.client.get('/checkout/')
        data = {**self.data(), 'shipping_zone': self.shipping.pk, 'payment_method': self.cod.pk,
            'checkout_key': str(uuid.uuid4()), 'agreement': 'on'}
        response = self.client.post('/checkout/', data)
        self.assertContains(response, 'checkout session changed')
        self.assertFalse(Order.objects.exists())

    def test_bank_orders_stay_pending_until_authorized_verification(self):
        order = self.buy(payment=self.bank)
        self.assertEqual(order.payment_status, 'awaiting_verification')
        with self.assertRaises(ValidationError): transition_order(order.pk, 'confirmed', self.verified_owner())
        with self.assertRaises(PermissionDenied): verify_payment(order.pk, self.customer)
        verify_payment(order.pk, self.verified_owner())
        order = transition_order(order.pk, 'confirmed', self.verified_owner())
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.payment_status, 'paid')

    def test_cancellation_restocks_exactly_once(self):
        order = self.buy()
        transition_order(order.pk, 'cancelled', self.verified_owner())
        transition_order(order.pk, 'cancelled', self.verified_owner())
        self.variant.refresh_from_db(); self.assertEqual(self.variant.stock, 3)

    def test_invalid_status_transition_rejected(self):
        order = self.buy()
        with self.assertRaises(ValidationError): transition_order(order.pk, 'delivered', self.verified_owner())

    def test_cod_payment_cannot_be_marked_paid_before_delivery(self):
        order = self.buy()
        with self.assertRaises(ValidationError): verify_payment(order.pk, self.verified_owner())

    def test_customers_and_unverified_staff_cannot_change_orders(self):
        order = self.buy()
        with self.assertRaises(PermissionDenied): transition_order(order.pk, 'confirmed', self.customer)
        with self.assertRaises(PermissionDenied): transition_order(order.pk, 'confirmed', self.owner)

    def test_customer_order_ownership_and_receipt(self):
        order = self.buy(user=self.customer)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(reverse('orders:detail', args=[order.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('orders:receipt', args=[order.pk])).status_code, 404)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('orders:detail', args=[order.pk])).status_code, 200)

    def test_guest_order_uuid_is_not_enough_and_signed_token_is_scoped(self):
        order = self.buy(); url = reverse('orders:detail', args=[order.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(url, {'token': order_token(order)}).status_code, 200)
        self.assertEqual(self.client.get(url, {'token': 'forged'}).status_code, 404)
        other = self.buy()
        self.assertEqual(self.client.get(url, {'token': order_token(other)}).status_code, 404)

    def test_confirmation_email_is_branded_and_retry_is_idempotent(self):
        order = self.buy()
        send_confirmation(order.pk); send_confirmation(order.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(order.number, mail.outbox[0].subject)
        self.assertIn('KAIROS', mail.outbox[0].alternatives[0].content)
        self.assertIsNotNone(OrderEmail.objects.get(order=order).sent_at)

    def test_failed_email_does_not_undo_order_and_can_retry(self):
        order = self.buy()
        with patch('orders.services.EmailMultiAlternatives.send', side_effect=RuntimeError('test failure')):
            send_confirmation(order.pk)
        self.assertTrue(Order.objects.filter(pk=order.pk).exists())
        self.assertEqual(OrderEmail.objects.get(order=order).last_error, 'RuntimeError')
        send_confirmation(order.pk)
        self.assertIsNotNone(OrderEmail.objects.get(order=order).sent_at)

    def test_admin_requires_staff_and_verified_otp(self):
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get('/admin/catalog/product/add/').status_code, 302)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        self.admin_login()
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def test_real_two_factor_login_challenges_and_verifies_totp(self):
        device = TOTPDevice.objects.create(user=self.owner, name='default', confirmed=True)
        url = '/account/login/?next=/admin/'
        self.client.get(url)
        response = self.client.post(url, {'login_view-current_step': 'auth', 'auth-username': self.owner.username, 'auth-password': PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['wizard']['steps'].current, 'token')
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        token = str(totp(device.bin_key, step=device.step, t0=device.t0, digits=device.digits, drift=device.drift)).zfill(device.digits)
        response = self.client.post(url, {'login_view-current_step': 'token', 'token-otp_token': token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    def admin_product_data(self, sku='ADMIN-TEST'):
        return {'name': 'Admin Added Watch', 'slug': 'admin-added-watch', 'sku': sku,
            'brand': self.brand.pk, 'collection': self.men.pk, 'category': self.category.pk,
            'description': 'A product added using the admin form.', 'regular_price': '4500.00', 'sale_price': '',
            'status': 'published', 'featured': 'on', 'new_arrival': 'on',
            'variants-TOTAL_FORMS': '1', 'variants-INITIAL_FORMS': '0', 'variants-MIN_NUM_FORMS': '1', 'variants-MAX_NUM_FORMS': '1000',
            'variants-0-name': 'Signature', 'variants-0-sku': sku+'-V', 'variants-0-stock': '5', 'variants-0-is_active': 'on',
            'images-TOTAL_FORMS': '1', 'images-INITIAL_FORMS': '0', 'images-MIN_NUM_FORMS': '0', 'images-MAX_NUM_FORMS': '1000',
            'images-0-image': photo(), 'images-0-alt': 'Test uploaded photograph', 'images-0-position': '0',
            'specifications-TOTAL_FORMS': '0', 'specifications-INITIAL_FORMS': '0', 'specifications-MIN_NUM_FORMS': '0', 'specifications-MAX_NUM_FORMS': '1000', '_save': 'Save'}

    def test_add_product_with_image_via_admin_then_edit_collection_price_stock_and_image(self):
        self.admin_login()
        data = self.admin_product_data()
        response = self.client.post('/admin/catalog/product/add/', data)
        self.assertEqual(response.status_code, 302, str(getattr(response, 'context_data', ''))[:800])
        product = Product.objects.get(sku='ADMIN-TEST')
        self.assertContains(self.client.get('/collections/men/'), 'Admin Added Watch')
        image = product.images.get(); original = image.image.name
        self.assertTrue(image.thumbnail.name.endswith('.webp'))
        variant = product.variants.get()
        data = self.admin_product_data(); data.update(regular_price='5500.00', collection=self.women.pk,
            **{'variants-INITIAL_FORMS': '1', 'variants-0-id': variant.pk, 'variants-0-product': product.pk, 'variants-0-stock': '9', 'variants-0-original_stock': '5',
               'images-INITIAL_FORMS': '1', 'images-0-id': image.pk, 'images-0-product': product.pk, 'images-0-image': photo('replacement.png'), 'images-0-position': '2'})
        response = self.client.post(reverse('admin:catalog_product_change', args=[product.pk]), data)
        self.assertEqual(response.status_code, 302)
        product.refresh_from_db(); variant.refresh_from_db(); image.refresh_from_db()
        self.assertEqual(product.regular_price, Decimal('5500.00'))
        self.assertEqual(variant.stock, 9)
        self.assertNotEqual(image.image.name, original)
        self.assertContains(self.client.get('/collections/women/'), 'Admin Added Watch')
        self.assertNotContains(self.client.get('/collections/men/'), 'Admin Added Watch')
        self.assertTrue(AuditEvent.objects.filter(action='admin.related_change').exists())

    def test_publish_requires_an_active_variant(self):
        self.admin_login(); data = self.admin_product_data()
        data.pop('variants-0-is_active')
        response = self.client.post('/admin/catalog/product/add/', data)
        self.assertContains(response, 'at least one active variant')
        self.assertFalse(Product.objects.filter(sku='ADMIN-TEST').exists())

    def test_admin_stale_inventory_form_does_not_restore_sold_stock(self):
        from catalog.admin import VariantAdminForm
        # Staff opened a form showing three watches; one was sold before Save.
        Variant.objects.filter(pk=self.variant.pk).update(stock=2)
        current = Variant.objects.get(pk=self.variant.pk)
        form = VariantAdminForm({'product': self.product.pk, 'name': 'Black', 'sku': self.variant.sku,
            'stock': 3, 'original_stock': 3, 'is_active': 'on'}, instance=current)
        self.assertFalse(form.is_valid())
        self.assertIn('Stock changed', str(form.errors))
        current.refresh_from_db(); self.assertEqual(current.stock, 2)

    def test_unverified_admin_post_cannot_add_a_product(self):
        self.client.force_login(self.owner)
        response = self.client.post('/admin/catalog/product/add/', self.admin_product_data())
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Product.objects.filter(sku='ADMIN-TEST').exists())

    def test_staff_role_cannot_verify_payments_or_change_store_settings(self):
        call_command('setup_roles', verbosity=0)
        staff = User.objects.create_user(username='staff@example.test', password=PASSWORD, is_staff=True)
        staff.groups.add(Group.objects.get(name='Store Staff'))
        self.assertTrue(staff.has_perm('orders.change_order'))
        self.assertFalse(staff.has_perm('orders.verify_payment'))
        self.assertFalse(staff.has_perm('core.change_storesettings'))

    def test_admin_order_status_update_and_csv_export(self):
        order = self.buy(); self.admin_login()
        url = reverse('admin:orders_order_change', args=[order.pk])
        response = self.client.post(url, {'status': 'confirmed', 'tracking_reference': 'TEST-TRACK', 'staff_notes': 'Test note', '_save': 'Save',
            'items-TOTAL_FORMS': '1', 'items-INITIAL_FORMS': '1', 'items-MIN_NUM_FORMS': '0', 'items-MAX_NUM_FORMS': '0',
            'items-0-id': order.items.get().pk, 'items-0-order': order.pk})
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db(); self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.tracking_reference, 'TEST-TRACK')
        response = self.client.post('/admin/orders/order/', {'action': 'export_csv', '_selected_action': str(order.pk)})
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn(order.number, response.content.decode())

    def test_csv_formula_injection_is_neutralized(self):
        for value in ['=SUM(A1)', '+cmd', '-1+1', '@TEST', '\tvalue']:
            self.assertTrue(csv_safe(value).startswith("'"))

    def test_image_validation_rejects_svg_bad_magic_and_oversize(self):
        for file in [SimpleUploadedFile('unsafe.svg', b'<svg onload="alert(1)"/>'),
                     SimpleUploadedFile('fake.jpg', b'not an image'),
                     SimpleUploadedFile('large.png', b'x'*(5*1024*1024+1))]:
            with self.assertRaises(ValidationError): validate_image(file)

    def test_user_content_is_escaped_in_pages_and_structured_data(self):
        self.product.description = '<script>alert(1)</script>'; self.product.save()
        response = self.client.get('/watch/test-watch/')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '\\u003Cscript\\u003E')

    def test_login_is_rate_limited(self):
        for _ in range(5):
            response = self.client.post('/accounts/login/', {'username': 'noone@example.test', 'password': 'wrong'})
        self.assertEqual(response.status_code, 429)

    def test_registration_uses_email_login_and_hashes_password(self):
        response = self.client.post('/accounts/register/', {'first_name': 'Tester', 'email': 'NEW@EXAMPLE.TEST',
            'password1': PASSWORD, 'password2': PASSWORD})
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='new@example.test')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_password_reset_uses_branded_email_and_non_enumerating_response(self):
        for email in [self.customer.email, 'missing@example.test']:
            response = self.client.post('/accounts/password-reset/', {'email': email})
            self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('KAIROS STORE', mail.outbox[0].body)

    def test_password_reset_token_works_once(self):
        self.client.post('/accounts/password-reset/', {'email': self.customer.email})
        path = urlsplit(re.search(r'https?://\S+', mail.outbox[0].body).group()).path
        first = self.client.get(path)
        self.assertEqual(first.status_code, 302)
        response = self.client.post(first.url, {'new_password1': 'Fresh-Testing-Password-2099!', 'new_password2': 'Fresh-Testing-Password-2099!'})
        self.assertEqual(response.status_code, 302)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password('Fresh-Testing-Password-2099!'))
        self.assertContains(self.client.get(path), 'expired or has already been used')

    def test_hero_and_branding_are_editable_and_logo_keeps_proportions(self):
        store = StoreSettings.load()
        store.hero_title = 'A new collection'; store.hero_emphasis = 'awaits.'
        store.hero_primary_label = 'Explore men'; store.logo = photo('logo.png', (200, 80)); store.save()
        with Image.open(store.logo.path) as image:
            self.assertEqual(image.size, (200, 80))
            self.assertEqual(image.format, 'PNG')
        response = self.client.get('/')
        self.assertContains(response, 'A new collection')
        self.assertContains(response, 'Explore men')
        self.assertContains(response, store.logo.url)
        order = self.buy(); send_confirmation(order.pk)
        self.assertIn(store.logo.url, mail.outbox[0].alternatives[0].content)

    def test_security_headers_and_seo(self):
        response = self.client.get('/watch/test-watch/')
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertIn("object-src 'none'", response['Content-Security-Policy'])
        self.assertContains(response, 'application/ld+json')
        self.assertEqual(self.client.get('/sitemap.xml').status_code, 200)
        self.assertEqual(self.client.get('/robots.txt').status_code, 200)
