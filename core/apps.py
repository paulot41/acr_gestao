from django.apps import AppConfig

class CoreConfig(AppConfig):
    """App config for the core domain models."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core (ACR Gestão)"
