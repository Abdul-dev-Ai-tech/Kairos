from django.db import migrations


def configure(apps, schema_editor):
    Store = apps.get_model('core', 'StoreSettings')
    Store.objects.filter(pk=1).update(phone='03157292819', whatsapp='923157292819', instagram='https://www.instagram.com/2.kairos.store/')
    Zone = apps.get_model('orders', 'ShippingZone')
    Zone.objects.filter(name='Pakistan — demo shipping').update(name='Lahore — store delivery', cities='Lahore',
        delivery_estimate='Delivery time will be confirmed by the Kairos team.')
    Page = apps.get_model('core', 'Page')
    for page in Page.objects.filter(slug__in=['shipping', 'privacy']):
        if page.slug == 'shipping':
            page.body = page.body.replace('We currently support delivery within Pakistan using the delivery zones enabled at checkout.',
                'We deliver within Lahore only. Enter your area, complete delivery address, mobile number and email. A map pin is optional.')
        elif 'WhatsApp' not in page.body:
            page.body += '\n\nIf you opt in, order updates are sent through Meta’s WhatsApp Business Platform. Optional map pins help our team deliver your order. The store owner receives the details needed for fulfilment.'
        page.save(update_fields=['body'])


class Migration(migrations.Migration):
    dependencies = [('core', '0003_storesettings_order_notification_email_and_more'),
                    ('orders', '0002_order_area_order_delivery_estimate_order_landmark_and_more')]
    operations = [migrations.RunPython(configure, migrations.RunPython.noop)]
