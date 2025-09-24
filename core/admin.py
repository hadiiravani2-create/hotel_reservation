# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, SiteSettings, Menu, MenuItem, AgencyUserRole

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('اطلاعات آژانس', {'fields': ('agency', 'agency_role')}),
    )
    list_display = BaseUserAdmin.list_display + ('agency', 'agency_role')
    list_filter = BaseUserAdmin.list_filter + ('agency',)


admin.site.register(AgencyUserRole)

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'menu', 'parent', 'order', 'url')
    list_filter = ('menu',)
    search_fields = ('title', 'url')
    list_editable = ('order',)
