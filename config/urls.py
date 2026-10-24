from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from two_factor.urls import urlpatterns as tf_urls
from core import views
from .sitemaps import ProductSitemap, CollectionSitemap, PageSitemap, StaticSitemap

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(tf_urls)),
    path('accounts/', include('accounts.urls')),
    path('', views.home, name='home'),
    path('', include('catalog.urls')),
    path('', include('orders.urls')),
    path('contact/', views.contact, name='contact'),
    path('pages/<slug:slug>/', views.page, name='page'),
    path('robots.txt', views.robots, name='robots'),
    path('sitemap.xml', sitemap, {'sitemaps': {'products': ProductSitemap, 'collections': CollectionSitemap, 'pages': PageSitemap, 'static': StaticSitemap}}, name='sitemap'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'
