

# notifications/admin.py

from django.contrib import admin
from .models import SmsSettings, EmailSettings

@admin.register(SmsSettings)
class SmsSettingsAdmin(admin.ModelAdmin):
    list_display = ('provider_name', 'sender_number', 'is_active')
    list_editable = ('is_active',)

@admin.register(EmailSettings)
class EmailSettingsAdmin(admin.ModelAdmin):
    list_display = ('provider_name', 'host', 'port', 'username', 'is_active')
    list_editable = ('is_active',)
