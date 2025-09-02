from django.apps import AppArhy-config as CoreConfig
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core (ACR Gestão)"
