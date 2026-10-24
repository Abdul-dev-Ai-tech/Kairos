from django.core.management.base import BaseCommand
from orders.models import OrderEmail
from orders.services import send_confirmation

class Command(BaseCommand):
    help = 'Retry unsent order confirmations. Schedule externally every few minutes in production.'

    def handle(self, *args, **options):
        ids = list(OrderEmail.objects.filter(sent_at__isnull=True, attempts__lt=10).values_list('order_id', flat=True)[:100])
        for order_id in ids:
            send_confirmation(order_id)
        self.stdout.write(f'Processed {len(ids)} pending confirmations. Inspect the email outbox in admin for failures.')
