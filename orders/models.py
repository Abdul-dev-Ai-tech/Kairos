import uuid
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)
    coupon_code = models.CharField(max_length=40, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey('catalog.Variant', on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(99)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cart', 'variant'], name='unique_cart_variant'),
                       models.CheckConstraint(condition=Q(quantity__gte=1) & Q(quantity__lte=99), name='cart_quantity_range')]

    @property
    def line_total(self):
        return self.variant.price * self.quantity

class ShippingZone(models.Model):
    name = models.CharField(max_length=100)
    cities = models.TextField(blank=True, help_text='One city per line. Empty means all cities within Pakistan.')
    charge = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    free_above = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    delivery_estimate = models.CharField(max_length=150, blank=True)
    active = models.BooleanField(default=True)

    def covers(self, city):
        return not self.cities.strip() or city.strip().casefold() in {c.strip().casefold() for c in self.cities.splitlines() if c.strip()}

    def price_for(self, subtotal):
        return Decimal('0.00') if self.free_above is not None and subtotal >= self.free_above else self.charge

    def __str__(self):
        return self.name

class PaymentMethod(models.Model):
    code = models.CharField(max_length=20, unique=True, choices=[('cod', 'Cash on delivery'), ('bank', 'Manual bank transfer')])
    name = models.CharField(max_length=100)
    instructions = models.TextField(blank=True, help_text='For bank transfer: account title, IBAN, bank name and payment-reference instructions.')
    active = models.BooleanField(default=False)

    def clean(self):
        if self.code == 'bank' and self.active and not self.instructions.strip():
            raise ValidationError({'instructions': 'Enter real bank-transfer instructions before enabling this payment method.'})

    def __str__(self):
        return self.name

class Coupon(models.Model):
    code = models.CharField(max_length=40, unique=True)
    kind = models.CharField(max_length=10, choices=[('percent', 'Percentage'), ('fixed', 'Fixed PKR')], default='percent')
    value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    minimum_order = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0, editable=False)
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def clean(self):
        self.code = self.code.strip().upper()
        if self.kind == 'percent' and self.value and self.value > 100:
            raise ValidationError({'value': 'Percentage must be at most 100.'})
        if self.starts_at and self.expires_at and self.expires_at <= self.starts_at:
            raise ValidationError({'expires_at': 'Expiry must be after the start date.'})

    def discount_for(self, subtotal):
        now = timezone.now()
        if not self.active or not self.starts_at <= now < self.expires_at:
            raise ValidationError('This coupon is inactive or expired.')
        if self.usage_limit is not None and self.times_used >= self.usage_limit:
            raise ValidationError('This coupon has reached its usage limit.')
        if subtotal < self.minimum_order:
            raise ValidationError(f'Minimum order for this coupon is PKR {self.minimum_order:,.2f}.')
        value = Decimal(str(self.value))
        discount = subtotal * value / 100 if self.kind == 'percent' else value
        return min(subtotal, discount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def __str__(self):
        return self.code

class Order(models.Model):
    STATUSES = [(s, s.replace('_', ' ').title()) for s in ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']]
    PAYMENT_STATUSES = [('pending', 'Payment due on delivery'), ('awaiting_verification', 'Awaiting bank verification'), ('paid', 'Paid')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.CharField(max_length=24, unique=True, editable=False)
    checkout_key = models.UUIDField(unique=True, editable=False)
    source_cart = models.UUIDField(editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.TextField(max_length=500)
    city = models.CharField(max_length=100)
    area = models.CharField(max_length=100, blank=True)
    landmark = models.CharField(max_length=180, blank=True)
    map_link = models.URLField(max_length=500, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=7, null=True, blank=True)
    whatsapp_opt_in = models.BooleanField(default=False)
    whatsapp_opt_in_at = models.DateTimeField(null=True, blank=True)
    whatsapp_consent_version = models.CharField(max_length=40, blank=True)
    delivery_estimate = models.CharField(max_length=150, blank=True)
    postal_code = models.CharField(max_length=15, blank=True)
    country = models.CharField(max_length=2, default='PK', editable=False)
    notes = models.TextField(blank=True, max_length=2000)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    coupon_code = models.CharField(max_length=40, blank=True)
    shipping_name = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=20)
    payment_instructions = models.TextField(blank=True)
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUSES)
    payment_verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='verified_payments')
    payment_verified_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUSES, default='pending', db_index=True)
    tracking_reference = models.CharField(max_length=150, blank=True)
    staff_notes = models.TextField(blank=True)
    stock_released = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [('verify_payment', 'Can verify received order payments'), ('export_order', 'Can export orders as CSV')]

    @property
    def delivery_map_url(self):
        if self.latitude is not None and self.longitude is not None:
            return f'https://www.google.com/maps?q={self.latitude},{self.longitude}'
        return self.map_link

    def __str__(self):
        return self.number

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey('catalog.Variant', on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=150)
    variant_name = models.CharField(max_length=100)
    sku = models.CharField(max_length=80)
    quantity = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    def __str__(self):
        return f'{self.quantity} × {self.product_name}'

class OrderEmail(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='confirmation_email')
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)


class OwnerOrderEmail(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='owner_email')
    recipient = models.EmailField()
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=100, blank=True)


class WhatsAppNotification(models.Model):
    KINDS = [('owner', 'New-order alert to owner'), ('customer', 'Order receipt to customer')]
    STATES = [(x, x.replace('_', ' ').title()) for x in ['queued', 'sending', 'submitted', 'sent', 'delivered', 'read', 'failed', 'uncertain', 'skipped']]
    order = models.ForeignKey(Order, related_name='whatsapp_notifications', on_delete=models.CASCADE)
    kind = models.CharField(max_length=10, choices=KINDS)
    recipient = models.CharField(max_length=16)
    state = models.CharField(max_length=16, choices=STATES, default='queued', db_index=True)
    provider_message_id = models.CharField(max_length=250, unique=True, null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_error = models.CharField(max_length=100, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['order', 'kind'], name='unique_order_whatsapp_kind')]
        ordering = ['created_at']
        default_permissions = ('view',)
        permissions = [('retry_whatsappnotification', 'Can retry reviewed WhatsApp notifications')]

    def __str__(self):
        return f'{self.order.number} · {self.kind} · {self.state}'
