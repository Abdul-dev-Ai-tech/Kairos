"""Real PostgreSQL regression tests. SQLite deliberately skips these locking tests."""
import threading
import uuid
from unittest import skipUnless
from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import connection, connections
from django.test import TransactionTestCase
from catalog.models import Variant
from orders.models import Cart, CartItem, Coupon, Order
from orders.services import place_order
from .test_store import fixtures

@skipUnless(connection.vendor == 'postgresql', 'Requires real PostgreSQL row locks; do not infer concurrency safety from SQLite.')
class CheckoutRaceTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        _, _, _, _, _, self.variant, _, self.shipping, self.cod, _, self.coupon = fixtures()

    def race(self, coupon=False):
        carts = [Cart.objects.create(coupon_code=self.coupon.code if coupon else '') for _ in range(2)]
        for cart in carts: CartItem.objects.create(cart=cart, variant=self.variant, quantity=1)
        barrier, results = threading.Barrier(2), []
        def worker(cart_id):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                data = {'name': 'Race test', 'email': 'race@example.test', 'phone': '03000000000',
                        'address': 'QA only test address', 'city': 'Lahore', 'area': 'Johar Town', 'postal_code': '', 'notes': '',
                        'shipping_zone': self.shipping, 'payment_method': self.cod}
                place_order(Cart.objects.get(pk=cart_id), uuid.uuid4(), AnonymousUser(), data)
                results.append('ordered')
            except ValidationError:
                results.append('rejected')
            except Exception as exc:
                results.append(type(exc).__name__)
            finally:
                connections.close_all()
        with patch('orders.services.send_confirmation'):
            threads = [threading.Thread(target=worker, args=(cart.pk,)) for cart in carts]
            for thread in threads: thread.start()
            for thread in threads: thread.join(timeout=20)
        self.assertEqual(sorted(results), ['ordered', 'rejected'])
        self.assertEqual(Order.objects.count(), 1)

    def test_last_watch_cannot_be_sold_twice(self):
        Variant.objects.filter(pk=self.variant.pk).update(stock=1)
        self.race()
        self.variant.refresh_from_db(); self.assertEqual(self.variant.stock, 0)

    def test_coupon_usage_limit_serializes_across_carts(self):
        self.race(coupon=True)
        self.coupon.refresh_from_db(); self.assertEqual(self.coupon.times_used, 1)
