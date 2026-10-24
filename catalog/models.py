from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from core.uploads import OptimizedImageMixin, upload_path, validate_image, optimized

class NamedSlug(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self):
        return self.name

class Brand(NamedSlug):
    pass

class Category(NamedSlug):
    class Meta(NamedSlug.Meta):
        verbose_name_plural = 'Categories'

class Collection(OptimizedImageMixin, NamedSlug):
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=upload_path, validators=[validate_image], blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    image_fields = ('image',)

    class Meta:
        ordering = ['position', 'pk']

    def get_absolute_url(self):
        return reverse('catalog:collection', args=[self.slug])

class ProductQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status='published', variants__is_active=True).distinct()

    def cards(self):
        return self.select_related('brand', 'collection').prefetch_related('images', 'variants')

class Product(models.Model):
    STATUS = [('draft', 'Draft'), ('published', 'Published'), ('archived', 'Archived')]
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, max_length=180)
    sku = models.CharField(max_length=80, unique=True)
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    collection = models.ForeignKey(Collection, on_delete=models.PROTECT)
    description = models.TextField()
    regular_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))])
    strap_material = models.CharField(max_length=80, blank=True)
    movement_type = models.CharField(max_length=80, blank=True)
    warranty_info = models.TextField(blank=True, help_text='Only enter verified warranty terms; otherwise leave empty.')
    status = models.CharField(max_length=12, choices=STATUS, default='draft', db_index=True)
    featured = models.BooleanField(default=False)
    new_arrival = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False)
    seo_title = models.CharField(max_length=160, blank=True)
    seo_description = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at', '-pk']
        constraints = [
            models.CheckConstraint(condition=Q(regular_price__gt=0), name='product_price_positive'),
            models.CheckConstraint(condition=Q(sale_price__isnull=True) | (Q(sale_price__gt=0) & Q(sale_price__lt=models.F('regular_price'))), name='product_sale_valid'),
        ]

    def clean(self):
        if self.sale_price is not None and self.regular_price is not None and self.sale_price >= self.regular_price:
            raise ValidationError({'sale_price': 'Sale price must be less than the regular price.'})

    @property
    def active_variants(self):
        return [v for v in self.variants.all() if v.is_active]

    @property
    def price(self):
        return min((v.price for v in self.active_variants), default=self.sale_price or self.regular_price)

    @property
    def stock(self):
        return sum(v.stock for v in self.active_variants)

    @property
    def cover(self):
        return next(iter(self.images.all()), None)

    @property
    def on_sale(self):
        return self.sale_price is not None or any(v.sale_price for v in self.active_variants)

    def get_absolute_url(self):
        return reverse('catalog:detail', args=[self.slug])

    def __str__(self):
        return self.name

class Variant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, default='Signature')
    sku = models.CharField(max_length=80, unique=True)
    dial_colour = models.CharField(max_length=60, blank=True)
    strap_colour = models.CharField(max_length=60, blank=True)
    regular_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))], help_text='Leave empty to inherit product price.')
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.01'))])
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['pk']
        constraints = [models.CheckConstraint(condition=Q(stock__gte=0), name='variant_stock_nonnegative'),
                       models.CheckConstraint(condition=Q(regular_price__isnull=True) | Q(regular_price__gt=0), name='variant_price_positive'),
                       models.CheckConstraint(condition=Q(sale_price__isnull=True) | Q(sale_price__gt=0), name='variant_sale_positive')]

    @property
    def base_price(self):
        return self.regular_price if self.regular_price is not None else self.product.regular_price

    @property
    def price(self):
        if self.sale_price is not None:
            return self.sale_price
        if self.regular_price is None and self.product.sale_price is not None:
            return self.product.sale_price
        return self.base_price

    def clean(self):
        if self.sale_price is not None and self.product_id and self.sale_price >= self.base_price:
            raise ValidationError({'sale_price': 'Sale price must be below the effective regular price.'})

    def __str__(self):
        return f'{self.product.name} · {self.name}'

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, null=True, blank=True, on_delete=models.SET_NULL, related_name='images')
    image = models.ImageField(upload_to=upload_path, validators=[validate_image])
    thumbnail = models.ImageField(upload_to=upload_path, editable=False, blank=True)
    medium = models.ImageField(upload_to=upload_path, editable=False, blank=True)
    alt = models.CharField(max_length=200)
    position = models.PositiveSmallIntegerField(default=0, help_text='Lower numbers appear first. Change these values to reorder.')

    class Meta:
        ordering = ['position', 'pk']

    def clean(self):
        if self.variant_id and self.variant.product_id != self.product_id:
            raise ValidationError({'variant': 'Image variant must belong to this product.'})

    def save(self, *args, **kwargs):
        if self.image and not self.image._committed:
            self.thumbnail = optimized(self.image, 480)
            self.medium = optimized(self.image, 960)
            self.image = optimized(self.image, 1600)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.alt

class Specification(models.Model):
    product = models.ForeignKey(Product, related_name='specifications', on_delete=models.CASCADE)
    label = models.CharField(max_length=80)
    value = models.CharField(max_length=250)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['position', 'pk']

    def __str__(self):
        return f'{self.label}: {self.value}'

class Wishlist(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'product'], name='unique_wishlist_product')]
