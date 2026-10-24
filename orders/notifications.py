"""Durable order alerts. Provider credentials never leave this server module."""
import json
import re
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ValidationError
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from core.models import StoreSettings
from .delivery import normalize_mobile
from .models import OrderEmail, OwnerOrderEmail, WhatsAppNotification


class WhatsAppError(Exception):
    def __init__(self, code, *, retryable=False, uncertain=False):
        self.code, self.retryable, self.uncertain = code, retryable, uncertain
        super().__init__(code)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

graph_opener = build_opener(NoRedirect)

def queue_order_notifications(order):
    store = StoreSettings.load()
    if store.order_notification_email:
        OwnerOrderEmail.objects.get_or_create(order=order, defaults={'recipient': store.order_notification_email})
    if store.order_notification_whatsapp:
        try:
            owner_phone = normalize_mobile(store.order_notification_whatsapp)
            defaults = {'recipient': owner_phone}
        except ValidationError:
            defaults = {'recipient': store.order_notification_whatsapp, 'state': 'failed', 'last_error': 'configuration.invalid_owner_recipient'}
        WhatsAppNotification.objects.get_or_create(order=order, kind='owner', defaults=defaults)
    if order.whatsapp_opt_in:
        WhatsAppNotification.objects.get_or_create(order=order, kind='customer', defaults={'recipient': normalize_mobile(order.phone)})


def text(value, limit):
    # Meta body variables should contain plain text without tabs/newlines.
    value = ' '.join(str(value or '').split())
    return value if len(value) <= limit else value[:limit-1] + '…'


def template_payload(notification):
    order = notification.order
    items = '; '.join(f'{i.quantity} x {i.product_name} ({i.variant_name})' for i in order.items.all())
    address = ', '.join(filter(None, [order.address, order.area, order.landmark, order.city, order.postal_code]))
    estimate = order.delivery_estimate or 'Delivery time will be confirmed by the Kairos team.'
    if notification.kind == 'customer':
        name = settings.WHATSAPP_CUSTOMER_TEMPLATE
        parameters = [text(order.name, 70), order.number, text(items, 250), f'{order.total:,.2f}', text(address, 220), text(estimate, 100)]
    else:
        name = settings.WHATSAPP_OWNER_TEMPLATE
        staff_url = settings.SITE_URL + reverse('admin:orders_order_change', args=[order.pk])
        # Full line items remain in the staff-only order view if the summary is long.
        parameters = [order.number, text(order.name, 70), order.phone, text(order.email, 100), text(items, 220),
                      text(address, 220), f'{order.total:,.2f}', text(order.delivery_map_url or 'No map pin supplied', 500), text(estimate, 100), staff_url]
    return {'messaging_product': 'whatsapp', 'recipient_type': 'individual', 'to': notification.recipient,
            'type': 'template', 'template': {'name': name, 'language': {'code': settings.WHATSAPP_TEMPLATE_LANGUAGE},
                'components': [{'type': 'body', 'parameters': [{'type': 'text', 'text': value} for value in parameters]}]}}


def send_whatsapp(payload):
    if not settings.WHATSAPP_ACCESS_TOKEN or not re.fullmatch(r'\d{3,40}', settings.WHATSAPP_PHONE_NUMBER_ID):
        raise WhatsAppError('configuration.missing_credentials')
    if not re.fullmatch(r'v\d{1,3}\.\d+', settings.WHATSAPP_GRAPH_VERSION):
        raise WhatsAppError('configuration.invalid_graph_version')
    sender = getattr(settings, 'WHATSAPP_SENDER_NUMBER', '')
    if sender and normalize_mobile(sender) == payload.get('to'):
        raise WhatsAppError('configuration.sender_equals_recipient')
    endpoint = f'https://graph.facebook.com/{settings.WHATSAPP_GRAPH_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages'
    request = Request(endpoint, data=json.dumps(payload).encode(), method='POST', headers={
        'Authorization': 'Bearer ' + settings.WHATSAPP_ACCESS_TOKEN, 'Content-Type': 'application/json'})
    try:
        with graph_opener.open(request, timeout=settings.WHATSAPP_TIMEOUT) as response:
            result = json.loads(response.read(128 * 1024))
    except HTTPError as exc:
        try:
            error = json.loads(exc.read(64 * 1024)).get('error', {})
            code = int(error.get('code', exc.code))
        except (ValueError, TypeError):
            code, error = exc.code, {}
        raise WhatsAppError(f'meta.{code}', retryable=exc.code in {429, 500, 502, 503, 504} or bool(error.get('is_transient'))) from None
    except (URLError, TimeoutError, OSError):
        # A request may have reached Meta before the timeout. Never blindly resend.
        raise WhatsAppError('transport.outcome_unknown', uncertain=True) from None
    except (ValueError, TypeError):
        raise WhatsAppError('response.outcome_unknown', uncertain=True) from None
    messages = result.get('messages', []) if isinstance(result, dict) else []
    message_id = messages[0].get('id') if messages and isinstance(messages[0], dict) else None
    if not isinstance(message_id, str) or not message_id or len(message_id) > 250:
        raise WhatsAppError('response.missing_message_id', uncertain=True)
    return message_id


def process_whatsapp(notification_id):
    if not settings.WHATSAPP_ENABLED:
        return False
    with transaction.atomic():
        row = WhatsAppNotification.objects.select_for_update().select_related('order').get(pk=notification_id)
        if row.state != 'queued' or row.next_attempt_at > timezone.now():
            return False
        if row.kind == 'customer' and not row.order.whatsapp_opt_in:
            row.state, row.last_error = 'skipped', 'customer.no_opt_in'
            row.save(update_fields=['state', 'last_error'])
            return False
        row.state, row.claimed_at = 'sending', timezone.now()
        row.attempts += 1
        row.save(update_fields=['state', 'claimed_at', 'attempts'])
    try:
        message_id = send_whatsapp(template_payload(row))
    except WhatsAppError as exc:
        state = 'uncertain' if exc.uncertain else 'queued' if exc.retryable and row.attempts < 5 else 'failed'
        WhatsAppNotification.objects.filter(pk=row.pk, state='sending').update(state=state, last_error=exc.code,
            next_attempt_at=timezone.now() + timedelta(seconds=min(3600, 30 * 2 ** row.attempts)))
        return False
    except Exception:
        WhatsAppNotification.objects.filter(pk=row.pk, state='sending').update(state='uncertain', last_error='worker.outcome_unknown')
        return False
    WhatsAppNotification.objects.filter(pk=row.pk, state='sending').update(state='submitted', provider_message_id=message_id,
        submitted_at=timezone.now(), last_error='')
    return True


def recover_interrupted_claims():
    # A worker killed after submitting may already have sent the message.
    return WhatsAppNotification.objects.filter(state='sending', claimed_at__lt=timezone.now()-timedelta(minutes=5)).update(
        state='uncertain', last_error='worker.interrupted_check_provider_before_retry')


def send_owner_email(delivery_id):
    with transaction.atomic():
        delivery = OwnerOrderEmail.objects.select_for_update().select_related('order').get(pk=delivery_id)
        if delivery.sent_at:
            return False
        order = delivery.order
        staff_url = settings.SITE_URL + reverse('admin:orders_order_change', args=[order.pk])
        context = {'order': order, 'store': StoreSettings.load(), 'staff_url': staff_url}
        email = EmailMultiAlternatives(f'New Kairos order {order.number}', render_to_string('orders/owner_email.txt', context),
                                      settings.DEFAULT_FROM_EMAIL, [delivery.recipient])
        delivery.attempts += 1
        try:
            email.send(fail_silently=False)
            delivery.sent_at, delivery.last_error = timezone.now(), ''
        except Exception as exc:
            delivery.last_error = type(exc).__name__[:100]
        delivery.save()
        return bool(delivery.sent_at)


def process_notifications(limit=25):
    from .services import send_confirmation
    recover_interrupted_claims()
    for row in OrderEmail.objects.filter(sent_at=None, attempts__lt=5).order_by('pk')[:limit]:
        send_confirmation(row.order_id)
    for row in OwnerOrderEmail.objects.filter(sent_at=None, attempts__lt=5).order_by('pk')[:limit]:
        send_owner_email(row.pk)
    sent = 0
    if settings.WHATSAPP_ENABLED:
        ids = WhatsAppNotification.objects.filter(state='queued', next_attempt_at__lte=timezone.now()).values_list('pk', flat=True)[:limit]
        for pk in list(ids):
            sent += bool(process_whatsapp(pk))
    return sent


def dispatch_order_notifications(order_id):
    """Vercel uses bounded synchronous sends; a container uses its worker."""
    from .services import send_confirmation
    send_confirmation(order_id)
    if settings.ORDER_NOTIFICATION_DISPATCH != 'inline':
        return
    # A provider failure cannot undo the committed order or block its redirect.
    try:
        email = OwnerOrderEmail.objects.filter(order_id=order_id, sent_at=None).first()
        if email:
            send_owner_email(email.pk)
        for pk in WhatsAppNotification.objects.filter(order_id=order_id, state='queued').values_list('pk', flat=True):
            process_whatsapp(pk)
    except Exception:
        # Durable rows remain for the protected cron/worker to revisit.
        return
