from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, F, DecimalField, OuterRef, Subquery, Exists
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from core.utils import safe_redirect
from .forms import BrowseForm
from .models import Product, Variant, Collection, Wishlist

def listing(request, collection_slug=None, edit=None):
    selected = get_object_or_404(Collection, slug=collection_slug) if collection_slug else None
    data = request.GET.copy()
    if selected:
        data['collection'] = selected.slug
    data.setdefault('sort', 'newest')
    form = BrowseForm(data)
    watches = Product.objects.published().cards()
    money = DecimalField(max_digits=12, decimal_places=2)
    price = Variant.objects.filter(product=OuterRef('pk'), is_active=True).annotate(effective_price=Coalesce(
        'sale_price', 'regular_price', 'product__sale_price', 'product__regular_price', output_field=money)).order_by('effective_price')
    watches = watches.annotate(display_price=Subquery(price.values('effective_price')[:1]),
        available=Exists(Variant.objects.filter(product=OuterRef('pk'), is_active=True, stock__gt=0)))
    title = selected.name if selected else 'All timepieces'
    if edit == 'new':
        watches = watches.filter(new_arrival=True)
        title = 'New arrivals'
    if edit == 'featured':
        watches = watches.filter(featured=True)
        title = 'The Kairos edit'
    if form.is_valid():
        filters = form.cleaned_data
        q = filters.get('q')
        if q:
            watches = watches.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(sku__icontains=q) | Q(brand__name__icontains=q) | Q(variants__sku__icontains=q)).distinct()
            title = f'Results for “{q}”'
        for field in ['collection', 'brand']:
            if filters.get(field):
                watches = watches.filter(**{field: filters[field]})
        if filters.get('strap'):
            watches = watches.filter(strap_material__iexact=filters['strap'])
        if filters.get('movement'):
            watches = watches.filter(movement_type__iexact=filters['movement'])
        if filters.get('min_price') is not None:
            watches = watches.filter(display_price__gte=filters['min_price'])
        if filters.get('max_price') is not None:
            watches = watches.filter(display_price__lte=filters['max_price'])
        if filters.get('availability'):
            watches = watches.filter(available=filters['availability'] == 'in_stock')
        watches = watches.order_by({'newest': '-created_at', 'price_asc': 'display_price', 'price_desc': '-display_price', 'name': 'name'}.get(filters['sort'], '-created_at'), 'pk')
    else:
        watches = watches.none()
    page = Paginator(watches, 9).get_page(request.GET.get('page'))
    return render(request, 'catalog/list.html', {
        'title': title, 'page_obj': page, 'filter_form': form, 'selected_collection': selected,
        'straps': Product.objects.published().exclude(strap_material='').values_list('strap_material', flat=True).distinct().order_by('strap_material'),
        'movements': Product.objects.published().exclude(movement_type='').values_list('movement_type', flat=True).distinct().order_by('movement_type'),
    })

def detail(request, slug):
    product = get_object_or_404(Product.objects.published().cards().prefetch_related('specifications'), slug=slug)
    variants = product.active_variants
    selected = next((v for v in variants if str(v.pk) == request.GET.get('variant')), None) or next((v for v in variants if v.stock), variants[0])
    images = list(product.images.all())
    gallery = [i for i in images if i.variant_id is None or i.variant_id == selected.pk]
    variant_data = [{
        'id': v.pk, 'name': v.name, 'sku': v.sku, 'price': str(v.price),
        'regular_price': str(v.base_price), 'stock': v.stock,
        'images': [{'url': i.image.url, 'medium': i.medium.url, 'thumbnail': i.thumbnail.url, 'alt': i.alt}
                   for i in images if i.variant_id is None or i.variant_id == v.pk],
    } for v in variants]
    structured = {
        '@context': 'https://schema.org', '@type': 'Product', 'name': product.name,
        'description': product.seo_description or product.description[:300], 'sku': selected.sku,
        'image': [request.build_absolute_uri(i.image.url) for i in gallery],
        'offers': {'@type': 'Offer', 'priceCurrency': 'PKR', 'price': str(selected.price),
            'availability': 'https://schema.org/InStock' if selected.stock else 'https://schema.org/OutOfStock',
            'url': request.build_absolute_uri(product.get_absolute_url() + f'?variant={selected.pk}')},
    }
    if product.brand:
        structured['brand'] = {'@type': 'Brand', 'name': product.brand.name}
    return render(request, 'catalog/detail.html', {'product': product, 'selected_variant': selected,
        'gallery': gallery, 'variant_data': variant_data, 'structured_data': structured,
        'related': Product.objects.published().cards().filter(collection=product.collection).exclude(pk=product.pk)[:4]})

def wishlist(request):
    ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True) if request.user.is_authenticated else request.session.get('wishlist', [])
    return render(request, 'catalog/wishlist.html', {'products': Product.objects.published().cards().filter(pk__in=ids)})

@require_POST
def wishlist_toggle(request, product_id):
    product = get_object_or_404(Product.objects.published(), pk=product_id)
    if request.user.is_authenticated:
        saved, created = Wishlist.objects.get_or_create(user=request.user, product=product)
        if not created:
            saved.delete()
        active = created
    else:
        ids = request.session.get('wishlist', [])
        active = product.pk not in ids
        ids = (ids + [product.pk])[-100:] if active else [pk for pk in ids if pk != product.pk]
        request.session['wishlist'] = ids
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'saved': active, 'message': 'Saved to your wishlist.' if active else 'Removed from your wishlist.'})
    messages.success(request, 'Wishlist updated.')
    return safe_redirect(request, product.get_absolute_url())
