import ipaddress
from django.conf import settings

def client_ip(request):
    """Opt-in single trusted proxy extractor; never enable on an exposed backend."""
    peer = request.META.get('REMOTE_ADDR')
    if getattr(settings, 'VERCEL_RUNTIME', False):
        candidate = request.META.get('HTTP_X_VERCEL_FORWARDED_FOR', peer)
        if candidate:
            candidate = candidate.split(',')[0].strip()
    else:
        candidate = request.META.get('HTTP_X_REAL_IP') if getattr(settings, 'TRUST_PROXY_HEADERS', False) else peer
    try:
        return str(ipaddress.ip_address(candidate))
    except (ValueError, TypeError):
        return peer
