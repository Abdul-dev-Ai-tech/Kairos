from django.core.management.base import BaseCommand
from core.models import StoreSettings, Page
from catalog.models import Collection, Category
from orders.models import ShippingZone, PaymentMethod

PAGES = {
    'about': ('Our story', 'Every Second, Your Style.', 'A watch is a small detail with a lasting impression. KAIROS STORE brings together timepieces for men, women and everyone who wears their own point of view.\n\nOur approach is simple: a considered selection, clear details and personal support. Find a piece for the everyday, a new chapter or someone special.\n\nStore owner: personalise this story with your real business details before launch.'),
    'shipping': ('Shipping & delivery', 'A little care, from our store to your door.', 'Draft policy — confirm these details with KAIROS STORE before ordering.\n\nWe deliver within Lahore only. Enter your Lahore area, complete address, mobile number and email at checkout. A map pin can help our team locate your address. The available methods and charges are calculated from your selected city and order value.\n\nThe delivery estimate shown for your zone is an estimate, not a guarantee. Orders require confirmation; bank transfers also require payment verification.\n\nStore owner: enter your courier, dispatch times, service areas, delivery estimates, holiday handling and failed-delivery terms. Replace all demonstration shipping charges before accepting orders.'),
    'returns': ('Returns & exchanges', 'We are here to help you find the right next step.', 'Draft policy — ask KAIROS STORE to confirm eligibility before ordering.\n\nContact the store with your order number, the issue and photographs where relevant. Do not send a return until the team confirms the return address and process.\n\nStore owner: specify your return window, product-condition requirements, exclusions, damaged-item process, shipping responsibility and refund timelines in accordance with applicable requirements. No return window or warranty is promised by this demonstration text.'),
    'privacy': ('Privacy policy', 'Your details deserve care.', 'Draft privacy notice — complete the business details before launch.\n\nKAIROS STORE processes the name, email, telephone, delivery address and order information you provide to handle orders and enquiries. Account passwords are stored as secure hashes. We do not collect card details in this application.\n\nEssential session and CSRF cookies support your account, bag and form security. The application does not include advertising trackers. Browser session storage remembers whether you have seen the welcome animation.\n\nOrder emails are sent through the email provider configured by the store. If you choose WhatsApp order updates, the store shares the required message and mobile number with Meta’s WhatsApp Business Platform. Optional map pins and coordinates are used to help deliver your order. A private owner alert contains the details needed to fulfil your order. A courier may receive the details necessary to deliver an order.\n\nStore owner: enter your legal entity, contact details, retention periods, data-request process, processors, applicable rights and any additional uses of customer data.'),
    'faqs': ('A few good questions', 'The details, made simple.', 'How do I choose a finish?\nOpen a product and choose a variant. Its price, stock, images and SKU update to match your selection.\n\nCan I order without an account?\nYes. Guest checkout is supported. Keep your confirmation link private; guest email links last seven days.\n\nHow do I pay?\nChoose one of the methods enabled at checkout. Bank-transfer orders remain pending until a staff member verifies payment. Never send a transfer to demonstration bank details.\n\nCan I change an order?\nContact the team with your order number before dispatch. Changes depend on order status and availability.\n\nWhat warranty is included?\nUse the verified terms on each product page or ask the store. A demonstration listing makes no authenticity or warranty promise.\n\nIs this a real product collection?\nListings marked Demo are examples to show the store layout. Their photos and details must be replaced before sale.'),
}

class Command(BaseCommand):
    help = 'Create essential editable store configuration. Does not overwrite existing data.'

    def handle(self, *args, **options):
        StoreSettings.load()
        for index, (slug, name, description) in enumerate([
            ('men', "Men’s Watches", 'A confident point of view. Explore timepieces for your everyday and beyond.'),
            ('women', "Women’s Watches", 'Refined details, endless possibilities. Find the piece that feels like you.'),
            ('unisex', 'Unisex Watches', 'Style without boundaries. A considered collection for every wrist.'),
        ]):
            Collection.objects.get_or_create(slug=slug, defaults={'name': name, 'description': description, 'position': index})
        Category.objects.get_or_create(slug='watches', defaults={'name': 'Watches'})
        Category.objects.get_or_create(slug='accessories', defaults={'name': 'Watch accessories'})
        for slug, (title, intro, body) in PAGES.items():
            Page.objects.get_or_create(slug=slug, defaults={'title': title, 'intro': intro, 'body': body})
        ShippingZone.objects.get_or_create(name='Lahore — store delivery', defaults={
            'cities': 'Lahore', 'charge': '250.00', 'free_above': '15000.00', 'delivery_estimate': 'Delivery time will be confirmed by the Kairos team.', 'active': True})
        PaymentMethod.objects.get_or_create(code='cod', defaults={'name': 'Cash on delivery', 'active': True, 'instructions': 'Pay the courier when your order arrives.'})
        PaymentMethod.objects.get_or_create(code='bank', defaults={'name': 'Bank transfer', 'active': False, 'instructions': ''})
        self.stdout.write(self.style.SUCCESS('Store configuration ready. Review all policies and shipping charges before launch.'))
