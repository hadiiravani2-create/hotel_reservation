# reservations/apps.py
# version: 1.0.1
# CLEANUP: Corrected comments and ensured signals are properly imported.

from django.apps import AppConfig

class ReservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reservations'

    def ready(self):
        """
        This method is called when the application is ready.
        It's the standard place to import signals to ensure they are connected.
        """
        import reservations.signals
