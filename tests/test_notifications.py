import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.error import URLError
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from core.models import StoreSettings
from orders.delivery import normalize_mobile, validate_delivery, validate_map_url
from orders.forms import CheckoutForm
from orders.models import Cart, Order, OwnerOrderEmail, WhatsAppNotification, ShippingZone
from orders.notifications import process_whatsapp, send_whatsapp, template_payload, WhatsAppError, send_owner_email, recover_interrupted_claims
from orders.services import change_cart, place_order
from tests.test_store import fixtures


class NotificationTests(TestCase):
    def setUp(self):
        (_, _, _, _, self.product, self.variant, _, self.zone, self.cod, _, _) = fixtures()
        self.zone.delivery_estimate = '2–3 working days'
        self.zone.save()
        self.store = StoreSettings.load()
        self.store.order_notification_email = 'owner@example.test'
        self.store.save()

    def data(self, **overrides):
        data = {'name': 'Demo Buyer', 'email': 'buyer@example.test', 'phone': '03001234567',
            'address': 'House 12, Test Street', 'city': 'Lahore', 'area': 'Johar Town', 'landmark': 'Test Park',
            'map_link': '', 'latitude': Decimal('31.4700'), 'longitude': Decimal('74.3000'),
            'postal_code': '54000', 'notes': '', 'shipping_zone': self.zone, 'payment_method': self.cod,
            'whatsapp_opt_in': True}
        data.update(overrides)
        return data

    def buy(self, **overrides):
        cart = Cart.objects.create()
        change_cart(cart, self.variant.pk, 1)
        return place_order(cart, uuid.uuid4(), AnonymousUser(), self.data(**overrides))

    def form(self, **overrides):
        data = self.data(checkout_key=str(uuid.uuid4()), agreement=True)
        data.update(overrides)
        data['shipping_zone'], data['payment_method'] = self.zone.pk, self.cod.pk
        return CheckoutForm(data)

    def test_phone_is_normalized_and_invalid_phone_rejected(self):
        for number in ['03001234567', '+92 300 1234567', '00923001234567']:
            self.assertEqual(normalize_mobile(number), '923001234567')
        for number in ['', '1234567', '+15551234567', '92300123456<script>']:
            with self.assertRaises(ValidationError): normalize_mobile(number)

    def test_city_cannot_be_forged_even_with_national_zone(self):
        self.zone.cities = ''; self.zone.save()
        form = self.form(city='Karachi')
        self.assertFalse(form.is_valid())
        with self.assertRaises(ValidationError): self.buy(city='Karachi')
        self.assertEqual(Order.objects.count(), 0)

    def test_area_email_and_address_are_required(self):
        for invalid in [{'area': ''}, {'email': ''}, {'address': 'short'}]:
            self.assertFalse(self.form(**invalid).is_valid())

    def test_coordinate_pair_and_lahore_bounds(self):
        for invalid in [{'longitude': None}, {'latitude': Decimal('24.86'), 'longitude': Decimal('67.01')}]:
            self.assertFalse(self.form(**invalid).is_valid())
            with self.assertRaises(ValidationError): validate_delivery(self.data(**invalid))
        self.assertTrue(self.form().is_valid())
        self.assertTrue(self.form(latitude='', longitude='').is_valid())

    def test_only_safe_map_links_accepted(self):
        self.assertEqual(validate_map_url('https://maps.app.goo.gl/Example'), 'https://maps.app.goo.gl/Example')
        for url in ['javascript:alert(1)', 'http://maps.google.com/maps', 'https://evil.test/a', 'https://google.com.evil.test/maps', 'https://google.com/search?q=x']:
            with self.assertRaises(ValidationError): validate_map_url(url)

    def test_order_snapshots_contact_location_estimate_and_consent(self):
        order = self.buy()
        self.assertEqual(order.phone, '923001234567')
        self.assertEqual(order.area, 'Johar Town')
        self.assertIn('31.4700', order.delivery_map_url)
        self.assertEqual(order.delivery_estimate, '2–3 working days')
        self.assertIsNotNone(order.whatsapp_opt_in_at)
        self.assertEqual(order.whatsapp_consent_version, 'order-updates-v1')
        self.assertEqual(order.whatsapp_notifications.count(), 2)
        self.assertEqual(order.whatsapp_notifications.get(kind='owner').recipient, '923157292819')
        self.assertEqual(order.owner_email.recipient, 'owner@example.test')
        self.zone.delivery_estimate = 'changed'; self.zone.save()
        order.refresh_from_db()
        self.assertEqual(order.delivery_estimate, '2–3 working days')

    def test_no_customer_whatsapp_without_consent(self):
        order = self.buy(whatsapp_opt_in=False)
        self.assertIsNone(order.whatsapp_opt_in_at)
        self.assertFalse(order.whatsapp_notifications.filter(kind='customer').exists())
        self.assertEqual(order.whatsapp_notifications.count(), 1)

    def test_duplicate_checkout_has_one_order_and_one_alert_per_recipient(self):
        cart = Cart.objects.create(); change_cart(cart, self.variant.pk, 1); key = uuid.uuid4()
        first = place_order(cart, key, AnonymousUser(), self.data())
        second = place_order(cart, key, AnonymousUser(), self.data())
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(WhatsAppNotification.objects.count(), 2)
        self.assertEqual(OwnerOrderEmail.objects.count(), 1)

    def test_template_uses_real_snapshots_and_staff_only_link(self):
        order = self.buy(); row = order.whatsapp_notifications.get(kind='owner')
        payload = template_payload(row)
        text = json.dumps(payload)
        self.assertIn('Johar Town', text); self.assertIn('buyer@example.test', text)
        self.assertIn('/admin/orders/order/', text)
        self.assertNotIn('?token=', text)
        self.assertEqual(payload['type'], 'template')
        self.assertEqual(len(payload['template']['components'][0]['parameters']), 10)

    @override_settings(WHATSAPP_ENABLED=True)
    def test_worker_submission_is_not_repeated(self):
        row = self.buy().whatsapp_notifications.get(kind='customer')
        with patch('orders.notifications.send_whatsapp', return_value='wamid.test') as send:
            self.assertTrue(process_whatsapp(row.pk)); self.assertFalse(process_whatsapp(row.pk))
            send.assert_called_once()
        row.refresh_from_db(); self.assertEqual(row.state, 'submitted'); self.assertIsNone(row.delivered_at)

    def test_disabled_provider_makes_no_network_call(self):
        row = self.buy().whatsapp_notifications.first()
        with patch('orders.notifications.send_whatsapp') as send:
            self.assertFalse(process_whatsapp(row.pk)); send.assert_not_called()
        row.refresh_from_db(); self.assertEqual(row.attempts, 0)

    @override_settings(WHATSAPP_ENABLED=True)
    def test_uncertain_outcome_is_not_automatically_retried(self):
        row = self.buy().whatsapp_notifications.first()
        with patch('orders.notifications.send_whatsapp', side_effect=WhatsAppError('transport.outcome_unknown', uncertain=True)) as send:
            self.assertFalse(process_whatsapp(row.pk)); self.assertFalse(process_whatsapp(row.pk)); send.assert_called_once()
        row.refresh_from_db(); self.assertEqual(row.state, 'uncertain')

    @override_settings(WHATSAPP_ENABLED=True)
    def test_retryable_provider_error_preserves_outbox_and_backoff(self):
        row = self.buy().whatsapp_notifications.first()
        with patch('orders.notifications.send_whatsapp', side_effect=WhatsAppError('meta.130429', retryable=True)):
            self.assertFalse(process_whatsapp(row.pk))
        row.refresh_from_db(); self.assertEqual(row.state, 'queued'); self.assertGreater(row.next_attempt_at, timezone.now())
        self.assertEqual(Order.objects.count(), 1)

    @override_settings(WHATSAPP_ACCESS_TOKEN='test-secret', WHATSAPP_PHONE_NUMBER_ID='123456789', WHATSAPP_GRAPH_VERSION='v26.0')
    def test_provider_request_has_authorized_fixed_https_endpoint(self):
        response = MagicMock(); response.read.return_value = b'{"messages":[{"id":"wamid.example"}]}'
        response.__enter__.return_value = response
        with patch('orders.notifications.graph_opener.open', return_value=response) as call:
            self.assertEqual(send_whatsapp({'type': 'template'}), 'wamid.example')
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, 'https://graph.facebook.com/v26.0/123456789/messages')
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-secret')
        with patch('orders.notifications.graph_opener.open', side_effect=URLError('timeout secret must not be stored')):
            with self.assertRaises(WhatsAppError) as exc: send_whatsapp({})
        self.assertEqual(exc.exception.code, 'transport.outcome_unknown')

    def test_owner_email_contains_delivery_details_once(self):
        row = self.buy().owner_email
        self.assertTrue(send_owner_email(row.pk)); self.assertFalse(send_owner_email(row.pk))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Johar Town', mail.outbox[0].body)
        self.assertIn('Test Park', mail.outbox[0].body)

    def test_interrupted_worker_requires_review(self):
        row = self.buy().whatsapp_notifications.first()
        row.state = 'sending'; row.claimed_at = timezone.now()-timedelta(minutes=6); row.save()
        self.assertEqual(recover_interrupted_claims(), 1)
        row.refresh_from_db(); self.assertEqual(row.state, 'uncertain')

    @override_settings(WHATSAPP_APP_SECRET='test-app-secret', WHATSAPP_PHONE_NUMBER_ID='123456789', WHATSAPP_WEBHOOK_VERIFY_TOKEN='test-verify')
    def test_signed_webhook_updates_delivery_and_ignores_older_status(self):
        row = self.buy().whatsapp_notifications.get(kind='customer')
        row.provider_message_id = 'wamid.webhook'; row.state = 'submitted'; row.save()
        def post(state, signed=True):
            body = json.dumps({'object': 'whatsapp_business_account', 'entry': [{'changes': [{'field': 'messages',
                'value': {'metadata': {'phone_number_id': '123456789'}, 'statuses': [{'id': 'wamid.webhook', 'recipient_id': row.recipient, 'status': state}]}}]}]}).encode()
            signature = 'sha256='+hmac.new(b'test-app-secret', body, hashlib.sha256).hexdigest() if signed else 'bad'
            return self.client.post('/webhooks/whatsapp/', body, content_type='application/json', HTTP_X_HUB_SIGNATURE_256=signature)
        self.assertEqual(post('delivered', False).status_code, 403)
        self.assertEqual(post('delivered').status_code, 200)
        row.refresh_from_db(); self.assertEqual(row.state, 'delivered'); self.assertIsNotNone(row.delivered_at)
        self.assertEqual(post('sent').status_code, 200); row.refresh_from_db(); self.assertEqual(row.state, 'delivered')
        self.assertEqual(self.client.get('/webhooks/whatsapp/', {'hub.mode':'subscribe','hub.verify_token':'test-verify','hub.challenge':'123'}).content, b'123')

    @override_settings(CRON_SECRET='a-test-cron-secret')
    def test_cron_rejects_unauthorized_access(self):
        self.assertEqual(self.client.get('/internal/notifications/run/').status_code, 403)
        with patch('orders.notifications.process_notifications', return_value=0) as process:
            response = self.client.get('/internal/notifications/run/', HTTP_AUTHORIZATION='Bearer a-test-cron-secret')
        self.assertEqual(response.status_code, 200); process.assert_called_once_with(limit=2)


    def test_geolocation_policy_only_allows_checkout_and_private_cron_is_not_cached(self):
        self.assertIn('geolocation=()', self.client.get('/').headers['Permissions-Policy'])
        cart = Cart.objects.create(); change_cart(cart, self.variant.pk, 1)
        session = self.client.session; session['cart_id'] = str(cart.pk); session.save()
        response = self.client.get('/checkout/')
        self.assertIn('geolocation=(self)', response.headers['Permissions-Policy'])
        self.assertIn('no-store', self.client.get('/internal/notifications/run/').headers['Cache-Control'])

    @override_settings(VERCEL_RUNTIME=True)
    def test_vercel_ip_extractor_uses_platform_header(self):
        from django.test import RequestFactory
        from core.security import client_ip
        request = RequestFactory().get('/', HTTP_X_VERCEL_FORWARDED_FOR='203.0.113.7', HTTP_X_REAL_IP='203.0.113.8', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(client_ip(request), '203.0.113.7')

    @override_settings(ORDER_NOTIFICATION_DISPATCH='inline', WHATSAPP_ENABLED=True)
    def test_inline_dispatch_submits_both_notifications_after_commit(self):
        with patch('orders.notifications.send_whatsapp', side_effect=['wamid.owner', 'wamid.customer']) as send:
            with self.captureOnCommitCallbacks(execute=True):
                order = self.buy()
        self.assertEqual(send.call_count, 2)
        self.assertEqual(order.whatsapp_notifications.filter(state='submitted').count(), 2)
        self.assertEqual(len(mail.outbox), 2)


    def test_owner_contact_misconfiguration_does_not_lose_order(self):
        self.store.order_notification_whatsapp = '12345678'; self.store.save()
        order = self.buy()
        row = order.whatsapp_notifications.get(kind='owner')
        self.assertEqual(row.state, 'failed')
        self.assertEqual(row.last_error, 'configuration.invalid_owner_recipient')
        self.assertEqual(order.whatsapp_notifications.get(kind='customer').state, 'queued')
