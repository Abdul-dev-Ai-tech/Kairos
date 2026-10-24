from django.contrib import admin
from .models import AuditEvent, Banner, ContactMessage, Page, StoreSettings

class AuditedAdmin(admin.ModelAdmin):
    class Media:
        js = ('js/admin-image-upload.js',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        AuditEvent.objects.create(actor=request.user, action='admin.change' if change else 'admin.create',
            object_label=f'{obj._meta.label} #{obj.pk}', details={'fields': list(form.changed_data)})

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        for formset in formsets:
            if formset.has_changed():
                AuditEvent.objects.create(actor=request.user, action='admin.related_change',
                    object_label=f'{form.instance._meta.label} #{form.instance.pk}', details={'relation': formset.prefix})

    def delete_model(self, request, obj):
        AuditEvent.objects.create(actor=request.user, action='admin.delete', object_label=f'{obj._meta.label} #{obj.pk}')
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            AuditEvent.objects.create(actor=request.user, action='admin.delete', object_label=f'{obj._meta.label} #{obj.pk}')
        super().delete_queryset(request, queryset)

@admin.register(StoreSettings)
class SettingsAdmin(AuditedAdmin):
    fieldsets = [
        ('Brand identity', {'fields': ['name', 'tagline', 'logo', 'favicon', 'announcement', 'demo_mode']}),
        ('Homepage hero', {'fields': ['hero_eyebrow', 'hero_title', 'hero_emphasis', 'hero_text', 'hero_image', 'hero_primary_label', 'hero_primary_link', 'hero_secondary_label', 'hero_secondary_link']}),
        ('Contact & social', {'fields': ['email', 'phone', 'address', 'whatsapp', 'instagram', 'facebook', 'order_notification_whatsapp', 'order_notification_email']}),
        ('Product-page policies', {'fields': ['delivery_info', 'returns_info', 'warranty_info', 'low_stock_threshold']}),
    ]

    def has_add_permission(self, request):
        return not StoreSettings.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Banner)
class BannerAdmin(AuditedAdmin):
    list_display = ['title', 'position', 'active']
    list_editable = ['position', 'active']

@admin.register(Page)
class PageAdmin(AuditedAdmin):
    list_display = ['title', 'slug', 'updated_at']
    prepopulated_fields = {'slug': ('title',)}

@admin.register(ContactMessage)
class ContactAdmin(AuditedAdmin):
    list_display = ['name', 'email', 'created_at', 'handled']
    list_filter = ['handled', 'created_at']
    readonly_fields = ['name', 'email', 'message', 'created_at']

    def has_add_permission(self, request):
        return False

@admin.register(AuditEvent)
class AuditAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'actor', 'action', 'object_label']
    list_filter = ['action', 'created_at']
    search_fields = ['object_label', 'actor__username']
    readonly_fields = ['actor', 'action', 'object_label', 'details', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
