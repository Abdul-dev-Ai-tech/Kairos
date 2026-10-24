from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
from catalog.models import Brand, Category, Collection, Product, ProductImage, Specification, Variant
from orders.models import Coupon
from core.models import Banner

class Command(BaseCommand):
    help = 'Seed 12 clearly labelled demonstration watches. Never overwrites existing products.'

    def handle(self, *args, **options):
        call_command('bootstrap_store')
        brand, _ = Brand.objects.get_or_create(slug='studio-demo', defaults={'name': 'Studio demo (replace)'})
        category = Category.objects.get(slug='watches')
        names = {'men': ['Meridian Noir', 'Heritage Forest', 'Afterhours', 'The Weekender'],
                 'women': ['Petite Lumière', 'Midnight Muse', 'The Rose Edit', 'Luna Silver'],
                 'unisex': ['Everyday Classic', 'Golden Hour', 'The Minimalist', 'Evening Standard']}
        choices = {'men': [('black', 'Noir / Black bracelet', 'Black', 'Black'), ('men', 'Forest / Silver bracelet', 'Forest green', 'Silver')],
                   'women': [('women', 'Ivory / Rose mesh', 'Ivory', 'Rose gold'), ('blue', 'Midnight / Silver bracelet', 'Navy blue', 'Silver')],
                   'unisex': [('unisex', 'Ivory / Brown strap', 'Ivory', 'Brown'), ('gold', 'Charcoal / Black strap', 'Charcoal', 'Black')]}
        made = 0
        for group, products in names.items():
            collection = Collection.objects.get(slug=group)
            asset = settings.BASE_DIR / 'static' / 'demo' / f'{choices[group][0][0]}.webp'
            if not collection.image and asset.exists():
                with asset.open('rb') as file:
                    collection.image = File(file, name=asset.name)
                    collection.save()
            for index, name in enumerate(products):
                slug = f'demo-{group}-{index + 1}'
                price = Decimal(7900 + made * 550)
                product, created = Product.objects.get_or_create(slug=slug, defaults={
                    'name': name, 'sku': f'DEMO-{group.upper()}-{index + 1:02}', 'brand': brand, 'category': category,
                    'collection': collection, 'description': 'A considered silhouette for everyday moments. This is a demonstration listing with conceptual product photography. All specifications, prices and inventory are illustrative. Replace them with verified details for your real watch before offering it for sale.',
                    'regular_price': price, 'sale_price': price - 750 if index == 2 else None,
                    'strap_material': 'Leather (demo)' if group == 'unisex' else 'Metal bracelet (demo)',
                    'movement_type': 'Quartz (demo)', 'status': 'published', 'featured': index == 0 or (group == 'men' and index == 1),
                    'new_arrival': index == 1 or (group == 'women' and index == 2), 'is_demo': True,
                    'seo_description': f'{name}: demonstration watch listing at KAIROS STORE. Replace sample information before sale.',
                })
                if created:
                    variant_choices = choices[group] if index % 2 == 0 else list(reversed(choices[group]))
                    for vi, (filename, finish, dial, strap) in enumerate(variant_choices):
                        variant = Variant.objects.create(product=product, name=finish, sku=f'{product.sku}-{vi + 1}',
                            dial_colour=dial, strap_colour=strap, stock=0 if index == 3 else 7 + index,
                            regular_price=price + 500 if vi else None)
                        image = settings.BASE_DIR / 'static' / 'demo' / f'{filename}.webp'
                        if image.exists():
                            with image.open('rb') as file:
                                ProductImage.objects.create(product=product, variant=variant,
                                    image=File(file, name=image.name), alt=f'Concept photograph · {finish} · demonstration image', position=vi)
                    for pos, (label, value) in enumerate([('Listing type', 'Demonstration only'), ('Case size', 'Illustrative 40 mm — replace'), ('Water resistance', 'Not specified — verify before sale')]):
                        Specification.objects.create(product=product, label=label, value=value, position=pos)
                    made += 1
        # The coupon is explicitly a local demonstration and has a finite window.
        Coupon.objects.get_or_create(code='KAIROS10', defaults={'kind': 'percent', 'value': 10,
            'minimum_order': 5000, 'expires_at': timezone.now() + timedelta(days=30), 'usage_limit': 100})
        Banner.objects.get_or_create(title='A gift of good time.', defaults={
            'eyebrow': 'SOMETHING THEY WILL MAKE THEIR OWN', 'text': 'For a new chapter, a quiet thank you, or simply because.',
            'link_text': 'Find a thoughtful gift', 'link': '/shop/'})
        self.stdout.write(self.style.SUCCESS(f'{made} demo watches created. Demo coupon: KAIROS10 (10%, minimum PKR 5,000, 30 days).'))
