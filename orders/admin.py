import csv
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import format_html
from core.admin import AuditedAdmin
from core.models import AuditEvent
from .models import Coupon, Order, OrderEmail, OrderItem, PaymentMethod, ShippingZone, OwnerOrderEmail, WhatsAppNotification
from .services import TRANSITIONS, transition_order, verify_payment

def csv_safe(value):
    value = str(value)
    return "'" + value if value[:1] in {'=', '+', '-', '@', '\t', '\r', '\n'} else value

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and 'status' in self.fields:
            allowed = TRANSITIONS.get(self.instance.status, set()) | {self.instance.status}
            self.fields['status'].choices = [x for x in Order.STATUSES if x[0] in allowed]

    def clean_status(self):
        status = self.cleaned_data['status']
        if self.instance.payment_method == 'bank' and self.instance.payment_status != 'paid' and status not in {'pending', 'cancelled'}:
            raise forms.ValidationError('Verify the bank payment using the authorized action before confirming.')
        return status

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ['product_name', 'variant_name', 'sku', 'quantity', 'unit_price', 'line_total']
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(Order)
class OrderAdmin(AuditedAdmin):
    form = OrderForm
    list_display = ['number', 'name', 'total', 'status', 'payment_method', 'payment_status', 'created_at']
    list_filter = ['status', 'payment_status', 'payment_method', 'created_at']
    search_fields = ['number', 'email', 'name', 'phone']
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    actions = ['export_csv', 'mark_payment_received']
    readonly_fields = [f.name for f in Order._meta.fields if f.name not in {'status', 'tracking_reference', 'staff_notes'}] + ['receipt_link']
    fieldsets = [
        ('Order', {'fields': ['number', 'status', 'created_at', 'user', 'receipt_link']}),
        ('Customer & delivery snapshot', {'fields': ['name', 'email', 'phone', 'address', 'city', 'postal_code', 'area', 'landmark', 'map_link', 'latitude', 'longitude', 'notes', 'shipping_name', 'delivery_estimate', 'whatsapp_opt_in', 'whatsapp_opt_in_at', 'whatsapp_consent_version']}),
        ('Amounts (PKR)', {'fields': ['subtotal', 'discount', 'coupon_code', 'shipping', 'total']}),
        ('Payment', {'fields': ['payment_method', 'payment_status', 'payment_instructions', 'payment_verified_by', 'payment_verified_at']}),
        ('Fulfilment', {'fields': ['tracking_reference', 'staff_notes', 'stock_released']}),
    ]

    def get_urls(self):
        return [path('<uuid:order_id>/receipt/', self.admin_site.admin_view(self.receipt), name='orders_order_receipt')] + super().get_urls()

    def receipt(self, request, order_id):
        obj = get_object_or_404(Order, pk=order_id)
        if not self.has_view_permission(request, obj):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return render(request, 'orders/receipt.html', {'order': obj})

    def receipt_link(self, obj):
        return format_html('<a href="{}">View / print order document</a>', reverse('admin:orders_order_receipt', args=[obj.pk]))

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # The admin change view is itself atomic. Apply state and restock once,
        # through the same service used by any future order-management interface.
        requested = obj.status
        updated = transition_order(obj.pk, requested, request.user)
        obj.stock_released = updated.stock_released
        # Do not write stale copies of payment/price/customer snapshots back over
        # another administrator's concurrent payment verification.
        Order.objects.filter(pk=obj.pk).update(tracking_reference=obj.tracking_reference, staff_notes=obj.staff_notes)
        AuditEvent.objects.create(actor=request.user, action='admin.change', object_label=f'orders.Order #{obj.pk}',
                                  details={'fields': list(form.changed_data)})

    def has_verify_payment_permission(self, request):
        return request.user.has_perm('orders.verify_payment')

    def has_export_order_permission(self, request):
        return request.user.has_perm('orders.export_order')

    @admin.action(description='Verify received payments (authorized staff only)', permissions=['verify_payment'])
    def mark_payment_received(self, request, queryset):
        for obj in queryset:
            try:
                verify_payment(obj.pk, request.user)
                self.message_user(request, f'{obj.number}: payment marked received.')
            except ValidationError as exc:
                self.message_user(request, exc.messages[0], messages.ERROR)

    @admin.action(description='Export selected orders as CSV', permissions=['export_order'])
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="kairos-orders.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        fields = ['number', 'created_at', 'name', 'email', 'phone', 'address', 'area', 'landmark', 'map_link', 'latitude', 'longitude', 'city', 'delivery_estimate', 'subtotal', 'discount', 'shipping', 'total', 'status', 'payment_method', 'payment_status']
        writer.writerow(fields)
        for obj in queryset:
            writer.writerow([csv_safe(getattr(obj, f)) for f in fields])
        AuditEvent.objects.create(actor=request.user, action='order.export', object_label='CSV export', details={'count': queryset.count()})
        return response

@admin.register(ShippingZone)
class ShippingAdmin(AuditedAdmin):
    list_display = ['name', 'charge', 'free_above', 'active']

@admin.register(PaymentMethod)
class PaymentAdmin(AuditedAdmin):
    list_display = ['name', 'code', 'active']

@admin.register(Coupon)
class CouponAdmin(AuditedAdmin):
    list_display = ['code', 'kind', 'value', 'times_used', 'usage_limit', 'expires_at', 'active']
    list_filter = ['active', 'kind']
    readonly_fields = ['times_used']

    def save_model(self, request, obj, form, change):
        if change:
            # changeform_view is atomic: preserve the redemption counter if a
            # checkout completed after this form was opened.
            obj.times_used = Coupon.objects.select_for_update().get(pk=obj.pk).times_used
        super().save_model(request, obj, form, change)

@admin.register(OrderEmail)
class EmailAdmin(admin.ModelAdmin):
    list_display = ['order', 'sent_at', 'attempts', 'last_error']
    readonly_fields = ['order', 'sent_at', 'attempts', 'last_error']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OwnerOrderEmail)
class OwnerEmailAdmin(EmailAdmin):
    list_display = ['order', 'recipient', 'sent_at', 'attempts', 'last_error']
    readonly_fields = ['order', 'recipient', 'sent_at', 'attempts', 'last_error']


@admin.register(WhatsAppNotification)
class WhatsAppAdmin(admin.ModelAdmin):
    list_display = ['order', 'kind', 'state', 'attempts', 'submitted_at', 'delivered_at', 'last_error']
    list_filter = ['state', 'kind']
    search_fields = ['order__number']
    readonly_fields = [f.name for f in WhatsAppNotification._meta.fields]
    actions = ['requeue_reviewed']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_retry_permission(self, request):
        return request.user.is_superuser and request.user.is_active and getattr(request.user, 'is_verified', lambda: False)()

    @admin.action(description='Requeue FAILED/UNCERTAIN after provider review (may send again)', permissions=['retry'])
    def requeue_reviewed(self, request, queryset):
        if not self.has_retry_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        from django.utils import timezone
        count = queryset.filter(state__in=['failed', 'uncertain']).update(state='queued', next_attempt_at=timezone.now(), last_error='')
        AuditEvent.objects.create(actor=request.user, action='whatsapp.manual_retry', object_label='Reviewed notification retries', details={'count': count})
        self.message_user(request, f'{count} reviewed notifications requeued. Worker must be running.')
