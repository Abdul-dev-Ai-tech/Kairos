from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Create Store Staff and Payment Verifier roles with explicit limited permissions.'

    def handle(self, *args, **kwargs):
        staff, _ = Group.objects.get_or_create(name='Store Staff')
        codenames = {'view_product', 'add_product', 'change_product', 'view_variant', 'add_variant', 'change_variant', 'delete_variant',
            'view_productimage', 'add_productimage', 'change_productimage', 'delete_productimage',
            'view_specification', 'add_specification', 'change_specification', 'delete_specification',
            'view_collection', 'add_collection', 'change_collection', 'view_category', 'add_category', 'change_category',
            'view_brand', 'add_brand', 'change_brand', 'view_order', 'change_order', 'view_orderitem', 'view_whatsappnotification', 'view_ownerorderemail', 'export_order',
            'view_coupon', 'add_coupon', 'change_coupon', 'view_shippingzone', 'view_paymentmethod', 'view_contactmessage', 'change_contactmessage'}
        staff.permissions.set(Permission.objects.filter(content_type__app_label__in=['catalog', 'orders', 'core'], codename__in=codenames))
        verifier, _ = Group.objects.get_or_create(name='Payment Verifier')
        verifier.permissions.set(Permission.objects.filter(content_type__app_label='orders', codename__in=['view_order', 'view_orderitem', 'verify_payment']))
        self.stdout.write(self.style.SUCCESS('Roles ready. Set users as staff and assign a role. OTP enrollment is required for every administrator.'))
