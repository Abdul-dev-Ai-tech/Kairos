import time
import logging
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from orders.notifications import process_notifications

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Continuously process durable order notifications (run as a separate service).'

    def add_arguments(self, parser):
        parser.add_argument('--poll-seconds', type=int, default=5)
        parser.add_argument('--batch-size', type=int, default=25)

    def handle(self, *args, **options):
        self.stdout.write('Order-notification worker running. Ctrl+C to stop.')
        try:
            while True:
                close_old_connections()
                try:
                    process_notifications(max(1, min(options['batch_size'], 100)))
                except Exception as exc:
                    # Do not log payloads, tokens, phone numbers or addresses.
                    logger.error('Notification batch failed (%s).', type(exc).__name__)
                time.sleep(max(1, min(options['poll_seconds'], 60)))
        except KeyboardInterrupt:
            self.stdout.write('Worker stopped.')
