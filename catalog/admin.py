from django.contrib import admin, messages
from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from core.admin import AuditedAdmin
from core.models import AuditEvent
from .models import Brand, Category, Collection, Product, ProductImage, Specification, Variant
from .templatetags.store_tags import money

class VariantAdminForm(forms.ModelForm):
    original_stock = forms.IntegerField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Variant
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['original_stock'] = self.instance.stock

    def clean(self):
        data = super().clean()
        if self.instance.pk:
            current = Variant.objects.get(pk=self.instance.pk)
            if data.get('original_stock') != current.stock:
                raise ValidationError('Stock changed while this page was open. Reload the product and review the latest inventory before saving.')
        return data

class VariantFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        active = [f for f in self.forms if f.cleaned_data and not f.cleaned_data.get('DELETE') and f.cleaned_data.get('is_active')]
        if self.instance.status == 'published' and not active:
            raise ValidationError('A published product needs at least one active variant with its SKU and stock.')
        for form in active:
            sale = form.cleaned_data.get('sale_price')
            base = form.cleaned_data.get('regular_price') or self.instance.regular_price
            if sale is not None and sale >= base:
                raise ValidationError('Variant sale prices must be below the effective regular price.')

class VariantInline(admin.TabularInline):
    model = Variant
    form = VariantAdminForm
    formset = VariantFormSet
    can_delete = False
    extra = 1
    min_num = 1
    fields = ['name', 'sku', 'dial_colour', 'strap_colour', 'regular_price', 'sale_price', 'stock', 'original_stock', 'is_active']

class ImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['preview', 'image', 'alt', 'variant', 'position']
    readonly_fields = ['preview']

    def preview(self, obj):
        return format_html('<img src="{}" width="70" height="70" style="object-fit:contain">', obj.thumbnail.url) if obj.thumbnail else 'Upload an image'

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['variant'].queryset = Variant.objects.filter(product=obj) if obj else Variant.objects.none()
        return formset

class SpecInline(admin.TabularInline):
    model = Specification
    extra = 1

@admin.register(Product)
class ProductAdmin(AuditedAdmin):
    change_list_template = 'admin/catalog/product/change_list.html'
    change_form_template = 'admin/catalog/product/change_form.html'
    list_display = ['watch', 'collection', 'display_price', 'inventory', 'publication', 'row_actions']
    list_display_links = ['watch']
    list_per_page = 20
    list_filter = ['status', 'collection', 'category', 'brand', 'featured', 'new_arrival', 'is_demo']
    search_fields = ['name', 'sku', 'variants__sku']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [VariantInline, ImageInline, SpecInline]
    save_on_top = True
    actions = ['publish', 'unpublish', 'archive']
    fieldsets = [
        ('Watch identity', {'fields': ['name', 'slug', 'sku', 'brand', 'category', 'collection', 'description']}),
        ('Prices (PKR)', {'fields': ['regular_price', 'sale_price']}),
        ('Verified details', {'fields': ['strap_material', 'movement_type', 'warranty_info']}),
        ('Merchandising', {'fields': ['status', 'featured', 'new_arrival', 'is_demo']}),
        ('Search appearance', {'classes': ['collapse'], 'fields': ['seo_title', 'seo_description']}),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('collection').prefetch_related('variants', 'images')

    @admin.display(description='Product', ordering='name')
    def watch(self, obj):
        cover = obj.cover
        image_url = (cover.thumbnail.url if cover.thumbnail else cover.image.url) if cover else static('images/product-placeholder.svg')
        return format_html('<span class="km-product-cell"><img src="{}" alt="" width="52" height="60" loading="lazy"><span><strong>{}</strong><small>{}</small>{}</span></span>', image_url, obj.name, obj.sku, self.highlights(obj))

    @admin.display(description='Price', ordering='regular_price')
    def display_price(self, obj):
        return format_html('<strong class="km-price">{}</strong>', money(obj.price))

    @admin.display(description='Status', ordering='status')
    def publication(self, obj):
        return format_html('<span class="km-badge km-badge-{}">{}</span>', obj.status, obj.get_status_display())

    @admin.display(description='Merchandising')
    def highlights(self, obj):
        flags = [label for enabled, label in [(obj.featured, 'Featured'), (obj.new_arrival, 'New'), (obj.is_demo, 'Demo')] if enabled]
        return format_html('<span class="km-flags">{}</span>', ' · '.join(flags) or '—')

    @admin.display(description='Actions')
    def row_actions(self, obj):
        return format_html('<a class="km-row-edit" href="{}" aria-label="Edit {}">Edit <span aria-hidden="true">↗</span></a>',
                           reverse('admin:catalog_product_change', args=[obj.pk]), obj.name)

    def get_object(self, request, object_id, from_field=None):
        if request.method == 'POST' and from_field is None:
            # Django wraps change-form POSTs in a transaction. Match checkout's
            # product-before-variant lock order while validating inline stock.
            try:
                return self.get_queryset(request).select_for_update(of=('self',)).get(pk=object_id)
            except (Product.DoesNotExist, ValidationError, ValueError):
                return None
        return super().get_object(request, object_id, from_field)

    @admin.display(description='Inventory')
    def inventory(self, obj):
        return format_html('<span class="km-stock {}"><i aria-hidden="true"></i>{} {}</span>',
                           'km-stock-empty' if not obj.stock else '', obj.stock, 'units' if obj.stock != 1 else 'unit')

    def _status(self, request, queryset, status):
        done = 0
        for product in queryset:
            if status == 'published' and not product.variants.filter(is_active=True).exists():
                self.message_user(request, f'{product.name} needs an active variant before publishing.', messages.ERROR)
                continue
            product.status = status
            product.save(update_fields=['status', 'updated_at'])
            AuditEvent.objects.create(actor=request.user, action='product.' + status, object_label=product.name)
            done += 1
        self.message_user(request, f'{done} product(s) updated.')

    @admin.action(description='Publish selected products', permissions=['change'])
    def publish(self, request, queryset):
        self._status(request, queryset, 'published')

    @admin.action(description='Unpublish selected products', permissions=['change'])
    def unpublish(self, request, queryset):
        self._status(request, queryset, 'draft')

    @admin.action(description='Archive selected products', permissions=['change'])
    def archive(self, request, queryset):
        self._status(request, queryset, 'archived')

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        if obj and obj.variants.filter(orderitem__isnull=False).exists():
            return False
        return super().has_delete_permission(request, obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

@admin.register(Collection)
class CollectionAdmin(AuditedAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ['name', 'position']
    list_editable = ['position']

@admin.register(Category, Brand)
class TaxonomyAdmin(AuditedAdmin):
    prepopulated_fields = {'slug': ('name',)}
