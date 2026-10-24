"""Permission and data checks for the Store Manager dashboard."""
from datetime import timedelta
from decimal import Decimal
import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_totp.models import TOTPDevice
from orders.models import Order
from tests.test_store import fixtures, PASSWORD


class AdminDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures()
        cls.owner = get_user_model().objects.create_superuser('dashboard-owner@example.test', password=PASSWORD)
        cls.reader = get_user_model().objects.create_user('catalog-reader@example.test', password=PASSWORD, is_staff=True)
        cls.reader.user_permissions.add(Permission.objects.get(content_type__app_label='catalog', codename='view_product'))

    def login_verified(self, user):
        device = TOTPDevice.objects.create(user=user, name='dashboard test', confirmed=True)
        self.client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
        session = self.client.session
        session[DEVICE_ID_SESSION_KEY] = device.persistent_id
        session.save()

    def make_order(self, status, amount, days_ago=0):
        order = Order.objects.create(number='QA-'+uuid.uuid4().hex[:10], checkout_key=uuid.uuid4(), source_cart=uuid.uuid4(),
            name='Private QA customer', email='private@example.test', phone='923000000000', address='Test address', city='Lahore',
            subtotal=amount, total=amount, shipping_name='Test shipping', payment_method='cod', payment_status='pending', status=status)
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now()-timedelta(days=days_ago))
        return order

    def test_chart_uses_real_seven_day_counts_and_delivered_sales(self):
        self.make_order('delivered', '100.00')
        self.make_order('confirmed', '80.00', 1)
        self.make_order('cancelled', '40.00', 2)
        self.make_order('pending', '25.00', 8)
        self.login_verified(self.owner)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['metrics']['sales'], Decimal('100.00'))
        self.assertEqual(response.context['metrics']['orders'], 4)
        self.assertEqual(response.context['metrics']['pending'], 1)
        self.assertEqual(response.context['week_order_count'], 3)
        activity = response.context['order_activity']
        self.assertEqual(len(activity), 7)
        self.assertEqual(activity[-1]['day'], timezone.localdate())
        self.assertEqual(sum(day['count'] for day in activity), 3)

    def test_catalog_only_staff_cannot_see_order_data_or_settings_navigation(self):
        self.make_order('pending', '25.00')
        self.login_verified(self.reader)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Private QA customer')
        self.assertNotContains(response, 'Delivered sales')
        self.assertNotContains(response, 'Add product')
        self.assertNotContains(response, 'Low-stock variants')
        links = [link['url'] for section in response.context['admin_navigation'] for link in section['links']]
        self.assertIn('/admin/catalog/product/', links)
        self.assertNotIn('/admin/orders/order/', links)
        self.assertNotIn('/admin/core/storesettings/', links)
        self.assertEqual(self.client.get('/admin/orders/order/').status_code, 403)
        self.assertEqual(self.client.post('/admin/catalog/product/add/', {}).status_code, 403)

    def test_owner_product_list_and_editor_keep_native_forms(self):
        self.login_verified(self.owner)
        response = self.client.get('/admin/catalog/product/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST')
        self.assertContains(response, 'km-product-cell')
        self.assertContains(response, '/admin/catalog/product/add/')
        self.assertContains(response, 'name="action"')
        response = self.client.get('/admin/catalog/product/add/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Variants &amp; stock')
        self.assertContains(response, 'variants-TOTAL_FORMS')
        self.assertContains(response, 'images-TOTAL_FORMS')
        self.assertContains(response, 'csrfmiddlewaretoken')
