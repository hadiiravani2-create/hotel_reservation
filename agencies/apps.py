# agencies/apps.py

from django.apps import AppConfig

class AgenciesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agencies'

    def ready(self):
        import agencies.signals # فایل سیگنال را وارد می‌کنیم