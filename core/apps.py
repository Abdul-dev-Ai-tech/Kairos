from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig

class KairosAdminConfig(AdminConfig):
    default_site = 'core.admin_site.KairosAdminSite'

class CoreConfig(AppConfig):
    name = 'core'
