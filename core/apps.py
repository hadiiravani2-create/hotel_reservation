# core/apps.py
# version: 1.0.1
# CONFIG: Imported signals to ensure they are connected when the app is ready.

from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        Import signals when the app is initialized.
        """
        import core.signals
