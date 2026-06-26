from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'eSYNAPSE 360 — Núcleo'

    def ready(self):
        # Conecta las señales de auditoría automática
        from . import signals  # noqa: F401
