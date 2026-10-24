from django.core.management.base import BaseCommand
from orders.notifications import process_notifications

class Command(BaseCommand):
    help = 'Send queued owner/customer email and enabled WhatsApp notifications once.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=25)

    def handle(self, *args, **options):
        sent = process_notifications(limit=max(1, min(options['limit'], 100)))
        self.stdout.write(f'Notification batch processed. WhatsApp submissions accepted: {sent}.')
