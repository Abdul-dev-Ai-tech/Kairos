from decimal import Decimal
from datetime import timedelta
from django.contrib import admin
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django_otp import devices_for_user
from two_factor.admin import AdminSiteOTPRequired

class KairosAdminSite(AdminSiteOTPRequired):
    site_header = 'KAIROS STORE'
    site_title = 'Kairos Store Manager'
    index_title = 'Overview'
    index_template = 'admin/kairos_index.html'
    enable_nav_sidebar = False

    def login(self, request, extra_context=None):
        if request.user.is_authenticated and request.user.is_active and request.user.is_staff:
            if not any(devices_for_user(request.user, confirmed=True)):
                return redirect('two_factor:setup')
        return redirect(reverse('two_factor:login') + '?next=' + reverse('admin:index'))

    def each_context(self, request):
        from .models import StoreSettings
        context = super().each_context(request)
        context['store'] = StoreSettings.load()
        models = {(app['app_label'], model['object_name'].lower()): model
                  for app in context['available_apps'] for model in app['models']}
        groups = [
            ('Workspace', [('catalog', 'product', 'Products', 'watch'), ('orders', 'order', 'Orders', 'bag'),
                ('catalog', 'collection', 'Collections', 'layers'), ('catalog', 'category', 'Categories', 'grid'), ('catalog', 'brand', 'Brands', 'tag')]),
            ('Business', [('orders', 'coupon', 'Discount codes', 'ticket'), ('orders', 'shippingzone', 'Shipping & delivery', 'truck'), ('orders', 'paymentmethod', 'Payment methods', 'card')]),
            ('Storefront', [('core', 'banner', 'Banners', 'image'), ('core', 'page', 'Pages & policies', 'file'), ('core', 'storesettings', 'Store settings', 'settings'), ('core', 'contactmessage', 'Customer enquiries', 'mail')]),
            ('Team & security', [('auth', 'user', 'Users', 'users'), ('auth', 'group', 'Staff roles', 'shield'), ('core', 'auditevent', 'Audit history', 'clock')]),
        ]
        navigation = []
        for label, entries in groups:
            links = []
            for app, model_name, name, icon in entries:
                model = models.pop((app, model_name), None)
                if model and model.get('admin_url'):
                    url = model['admin_url']
                    links.append({'name': name, 'url': url, 'icon': icon, 'active': request.path.startswith(url)})
            if links:
                navigation.append({'name': label, 'links': links})
        other = [{'name': model['name'], 'url': model['admin_url'], 'icon': 'tool', 'active': request.path.startswith(model['admin_url'])}
                 for model in models.values() if model.get('admin_url')]
        if other:
            navigation.append({'name': 'More tools', 'links': other})
        context['admin_navigation'] = navigation
        context['admin_overview_active'] = request.path == reverse('admin:index')
        return context

    def index(self, request, extra_context=None):
        from catalog.models import Product, Variant
        from orders.models import Order
        from .models import StoreSettings
        context = dict(extra_context or {})
        context['dashboard_today'] = timezone.localdate()
        if request.user.has_perm('orders.view_order'):
            orders = Order.objects.all()
            context['metrics'] = {
                'sales': orders.filter(status='delivered').aggregate(value=Sum('total'))['value'] or Decimal('0'),
                'orders': orders.count(), 'pending': orders.filter(status='pending').count(),
                'bank_pending': orders.filter(payment_status='awaiting_verification').exclude(status='cancelled').count(),
            }
            context['recent_orders'] = orders[:6]
            today = timezone.localdate()
            first_day = today - timedelta(days=6)
            counts = dict(orders.filter(created_at__date__gte=first_day, created_at__date__lte=today)
                          .annotate(day=TruncDate('created_at')).values('day')
                          .annotate(count=Count('pk')).values_list('day', 'count'))
            maximum = max(counts.values(), default=0) or 1
            context['order_activity'] = [{'day': first_day + timedelta(days=index),
                'count': counts.get(first_day + timedelta(days=index), 0),
                'height': round(counts.get(first_day + timedelta(days=index), 0) / maximum * 100)} for index in range(7)]
            context['week_order_count'] = sum(counts.values())
        if request.user.has_perm('catalog.view_product'):
            context['catalog_metrics'] = Product.objects.aggregate(total=Count('pk'),
                published=Count('pk', filter=Q(status='published')), drafts=Count('pk', filter=Q(status='draft')))
            context['recent_products'] = Product.objects.cards()[:4]
        if request.user.has_perm('catalog.view_variant'):
            stock = Variant.objects.select_related('product').prefetch_related('product__images').filter(
                stock__lte=StoreSettings.load().low_stock_threshold, is_active=True,
                product__status='published').order_by('stock', 'pk')
            context['low_stock_count'] = stock.count()
            context['low_stock'] = stock[:5]
        return super().index(request, context)
