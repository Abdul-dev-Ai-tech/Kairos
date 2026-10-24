"""Only Meta-signed delivery receipts are accepted. No message bodies are retained."""
import hashlib
import hmac
import json
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import WhatsAppNotification


@csrf_exempt  # This machine endpoint authenticates every POST with Meta's HMAC.
@require_http_methods(['GET', 'POST'])
def whatsapp_webhook(request):
    if request.method == 'GET':
        token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        if token and request.GET.get('hub.mode') == 'subscribe' and constant_time_compare(request.GET.get('hub.verify_token', ''), token):
            return HttpResponse(request.GET.get('hub.challenge', ''), content_type='text/plain')
        return HttpResponse(status=403)
    if not settings.WHATSAPP_APP_SECRET:
        return HttpResponse(status=503)
    if len(request.body) > 512 * 1024:
        return HttpResponse(status=413)
    expected = 'sha256=' + hmac.new(settings.WHATSAPP_APP_SECRET.encode(), request.body, hashlib.sha256).hexdigest()
    if not constant_time_compare(request.headers.get('X-Hub-Signature-256', ''), expected):
        return HttpResponse(status=403)
    try:
        body = json.loads(request.body)
        if not isinstance(body, dict) or body.get('object') != 'whatsapp_business_account':
            return HttpResponse(status=400)
        for entry in body.get('entry', []):
            for change in entry.get('changes', []):
                if change.get('field') != 'messages':
                    continue
                value = change.get('value', {})
                if value.get('metadata', {}).get('phone_number_id') != settings.WHATSAPP_PHONE_NUMBER_ID:
                    continue
                for status in value.get('statuses', []):
                    apply_status(status)
    except (ValueError, TypeError, AttributeError):
        return HttpResponse(status=400)
    return JsonResponse({'received': True})


@transaction.atomic
def apply_status(status):
    message_id = status.get('id')
    if not isinstance(message_id, str) or not message_id:
        return
    row = WhatsAppNotification.objects.select_for_update().filter(provider_message_id=message_id).first()
    if not row or status.get('recipient_id') != row.recipient:
        return
    state = status.get('status')
    ranks = {'submitted': 0, 'sent': 1, 'delivered': 2, 'read': 3}
    if state == 'failed' and row.state not in {'delivered', 'read'}:
        row.state = 'failed'
        errors = status.get('errors', [])
        code = errors[0].get('code', 'unknown') if errors else 'unknown'
        row.last_error = ('delivery.' + str(code))[:100]
    elif state in ranks and ranks.get(state, -1) > ranks.get(row.state, -1):
        row.state = state
        row.last_error = ''
        if state in {'delivered', 'read'} and not row.delivered_at:
            row.delivered_at = timezone.now()
    row.save(update_fields=['state', 'last_error', 'delivered_at'])


@require_http_methods(['GET'])
def notification_cron(request):
    secret = settings.CRON_SECRET
    if not secret or not constant_time_compare(request.headers.get('Authorization', ''), 'Bearer ' + secret):
        return HttpResponse(status=403)
    from .notifications import process_notifications
    # Bounded work fits the function's duration. The outbox persists between calls.
    accepted = process_notifications(limit=2)
    return JsonResponse({'processed': True, 'whatsapp_submissions': accepted})
