"""Server-side Lahore delivery and contact validation shared by forms/services."""
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from django.conf import settings
from django.core.exceptions import ValidationError


def normalize_mobile(value):
    digits = re.sub(r'[\s()+-]', '', str(value or ''))
    if digits.startswith('0092'):
        digits = digits[2:]
    if digits.startswith('03'):
        digits = '92' + digits[1:]
    if not re.fullmatch(r'923\d{9}', digits):
        raise ValidationError('Enter a Pakistani mobile number, for example 03XX1234567 or +923XX1234567.')
    return digits


def validate_map_url(value):
    if not value:
        return ''
    try:
        url = urlsplit(value)
        allowed = {'maps.google.com', 'www.google.com', 'google.com', 'maps.app.goo.gl', 'goo.gl'}
        if url.scheme != 'https' or url.hostname not in allowed or url.username or url.password or url.port not in (None, 443):
            raise ValueError
        if url.hostname in {'www.google.com', 'google.com'} and not url.path.startswith('/maps'):
            raise ValueError
        if url.hostname == 'goo.gl' and not url.path.startswith('/maps'):
            raise ValueError
    except (ValueError, TypeError):
        raise ValidationError('Paste an HTTPS Google Maps location/share link.')
    return value


def validate_delivery(data):
    if str(data.get('city', '')).strip().casefold() != 'lahore':
        raise ValidationError('KAIROS STORE currently delivers within Lahore only.')
    area = str(data.get('area', '')).strip()
    if not 2 <= len(area) <= 100:
        raise ValidationError('Enter your area or neighbourhood in Lahore.')
    latitude, longitude = data.get('latitude'), data.get('longitude')
    if (latitude in (None, '')) != (longitude in (None, '')):
        raise ValidationError('Share both location coordinates or leave both empty.')
    if latitude not in (None, ''):
        try:
            latitude, longitude = Decimal(str(latitude)), Decimal(str(longitude))
            min_lat, min_lng, max_lat, max_lng = map(Decimal, settings.LAHORE_SERVICE_BOUNDS.split(','))
            if not (latitude.is_finite() and longitude.is_finite() and min_lat <= latitude <= max_lat and min_lng <= longitude <= max_lng):
                raise ValueError
        except (ValueError, InvalidOperation):
            raise ValidationError('This location is outside our Lahore delivery service area. Check the pin or contact the store.')
    validate_map_url(str(data.get('map_link', '')).strip())
    return {'city': 'Lahore', 'area': area, 'latitude': latitude or None, 'longitude': longitude or None}
