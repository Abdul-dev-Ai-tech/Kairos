from django.conf import settings
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from .uploads import OptimizedImageMixin, upload_path, validate_image

class StoreSettings(OptimizedImageMixin, models.Model):
    name = models.CharField(max_length=100, default='KAIROS STORE')
    tagline = models.CharField(max_length=160, default='Every Second, Your Style.')
    logo = models.ImageField(upload_to=upload_path, validators=[validate_image], blank=True)
    favicon = models.ImageField(upload_to=upload_path, validators=[validate_image], blank=True)
    announcement = models.CharField(max_length=200, default='A considered collection. A lasting impression.')
    hero_eyebrow = models.CharField(max_length=100, default='The art of everyday time')
    hero_title = models.CharField(max_length=160, default='Some moments\ndeserve', help_text='A line break in this field creates a line break in the hero heading.')
    hero_emphasis = models.CharField(max_length=80, default='more.', blank=True, help_text='Optional italic ending for the heading.')
    hero_text = models.TextField(default='A little confidence. A quiet statement.\nFind a timepiece that feels like you.')
    hero_image = models.ImageField(upload_to=upload_path, validators=[validate_image], blank=True)
    hero_primary_label = models.CharField(max_length=50, default="Shop men's")
    hero_primary_link = models.CharField(max_length=200, default='/collections/men/', validators=[RegexValidator(r'^/(?!/)', 'Use a local URL starting with one slash.')])
    hero_secondary_label = models.CharField(max_length=50, default="Shop women's")
    hero_secondary_link = models.CharField(max_length=200, default='/collections/women/', validators=[RegexValidator(r'^/(?!/)', 'Use a local URL starting with one slash.')])
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True, default='03157292819')
    address = models.TextField(blank=True)
    whatsapp = models.CharField(max_length=16, blank=True, default='923157292819', help_text='International digits only, e.g. 923001234567', validators=[RegexValidator(r'^\d{8,16}$', 'Use 8–16 digits, without + or spaces.')])
    instagram = models.URLField(blank=True, default='https://www.instagram.com/2.kairos.store/')
    order_notification_whatsapp = models.CharField(max_length=16, default='923157292819', blank=True, validators=[RegexValidator(r'^\d{8,16}$', 'Use international digits only.')], help_text='Owner alert recipient. Must differ from the Meta API sender number.')
    order_notification_email = models.EmailField(blank=True, help_text='Private owner inbox for new-order alerts. Not shown on the storefront.')
    facebook = models.URLField(blank=True)
    delivery_info = models.TextField(default='Delivery time and charges are shown at checkout for your selected zone.')
    returns_info = models.TextField(default='Please contact the store to confirm the return policy before ordering.')
    warranty_info = models.TextField(default='Warranty terms vary by product. Refer to the specifications or contact the store.')
    low_stock_threshold = models.PositiveIntegerField(default=3)
    demo_mode = models.BooleanField(default=True, help_text='Displays a demonstration-content notice. Turn off only after replacing demo content.')
    image_fields = ('logo', 'favicon', 'hero_image')

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def __str__(self):
        return 'Store identity & contact details'

    class Meta:
        verbose_name_plural = 'Store settings'

class Banner(OptimizedImageMixin, models.Model):
    eyebrow = models.CharField(max_length=80, default='THE KAIROS EDIT')
    title = models.CharField(max_length=120)
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to=upload_path, validators=[validate_image], blank=True)
    link_text = models.CharField(max_length=60, default='Discover the collection')
    link = models.CharField(max_length=200, default='/shop/', validators=[RegexValidator(r'^/(?!/)', 'Use a local URL starting with one slash.')])
    active = models.BooleanField(default=True)
    position = models.PositiveSmallIntegerField(default=0)
    image_fields = ('image',)

    class Meta:
        ordering = ['position', 'pk']

    def __str__(self):
        return self.title

class Page(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=150)
    intro = models.CharField(max_length=250, blank=True)
    body = models.TextField(help_text='Plain text; blank lines separate paragraphs. HTML is escaped for safety.')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.name} · {self.created_at:%d %b %Y}'

class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    object_label = models.CharField(max_length=250)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        default_permissions = ('view',)

    def __str__(self):
        return f'{self.action}: {self.object_label}'
