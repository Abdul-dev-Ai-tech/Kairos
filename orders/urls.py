from django.urls import path
from . import views
from .webhooks import whatsapp_webhook, notification_cron
app_name = 'orders'
urlpatterns = [
    path('internal/notifications/run/', notification_cron, name='notification_cron'),
    path('webhooks/whatsapp/', whatsapp_webhook, name='whatsapp_webhook'),
    path('bag/', views.cart, name='cart'),
    path('bag/summary/', views.cart_summary, name='cart_summary'),
    path('bag/change/', views.cart_change, name='cart_change'),
    path('bag/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('bag/coupon/', views.coupon_apply, name='coupon'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/quote/', views.quote, name='quote'),
    path('orders/', views.history, name='history'),
    path('orders/<uuid:order_id>/', views.detail, name='detail'),
    path('orders/<uuid:order_id>/receipt/', views.receipt, name='receipt'),
]
