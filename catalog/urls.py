from django.urls import path
from . import views
app_name = 'catalog'
urlpatterns = [
    path('shop/', views.listing, name='shop'),
    path('search/', views.listing, name='search'),
    path('collections/<slug:collection_slug>/', views.listing, name='collection'),
    path('new-arrivals/', views.listing, {'edit': 'new'}, name='new'),
    path('featured/', views.listing, {'edit': 'featured'}, name='featured'),
    path('watch/<slug:slug>/', views.detail, name='detail'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/<int:product_id>/toggle/', views.wishlist_toggle, name='wishlist_toggle'),
]
