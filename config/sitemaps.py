from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from catalog.models import Product, Collection
from core.models import Page

class ProductSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Product.objects.published()

    def lastmod(self, obj):
        return obj.updated_at

class CollectionSitemap(Sitemap):
    def items(self):
        return Collection.objects.all()

class PageSitemap(Sitemap):
    def items(self):
        return Page.objects.order_by('pk')

    def location(self, obj):
        return reverse('page', args=[obj.slug])

class StaticSitemap(Sitemap):
    def items(self):
        return ['home', 'catalog:shop', 'contact']

    def location(self, item):
        return reverse(item)
