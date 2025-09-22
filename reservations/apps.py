# reservations/apps.py

from django.apps import AppConfig

class ReservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reservations'

    def ready(self):
        import reservations.signals # فایل سیگنال را وارد می‌کنیم تا شنونده‌ها فعال شوند
