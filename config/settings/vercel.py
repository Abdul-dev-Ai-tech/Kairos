"""Production Django settings for Vercel's native Python/Django runtime."""
from .production import *

if os.getenv('MEDIA_STORAGE') != 's3':
    raise ImproperlyConfigured('Vercel uploads require permanent MEDIA_STORAGE=s3 (S3/R2-compatible bucket).')
if not os.getenv('AWS_STORAGE_BUCKET_NAME') or not os.getenv('AWS_ACCESS_KEY_ID') or not os.getenv('AWS_SECRET_ACCESS_KEY'):
    raise ImproperlyConfigured('Configure persistent cloud-media bucket credentials before Vercel deployment.')
if len(os.getenv('CRON_SECRET', '')) < 32:
    raise ImproperlyConfigured('Set a random CRON_SECRET of at least 32 characters.')
VERCEL_RUNTIME = True
DATABASES['default']['CONN_MAX_AGE'] = 0
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
DATABASES['default']['OPTIONS'].setdefault('sslmode', 'require')
FILE_UPLOAD_TEMP_DIR = '/tmp'
MAX_IMAGE_UPLOAD_BYTES = 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 4 * 1024 * 1024
ORDER_NOTIFICATION_DISPATCH = 'inline'
# Vercel terminates HTTPS in front of the WSGI function.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
