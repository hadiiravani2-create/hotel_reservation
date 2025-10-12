# core/admin.py
# version: 0.0.5
# Feature: Added icon_name attribute to Admin classes to define icons in the Django Admin interface (e.g., Jazzmin).

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.forms import inlineformset_factory 
from .models import CustomUser, SiteSettings, Menu, MenuItem, AgencyUserRole 

# --- Custom Inline for Menu Items ---
class MenuItemInline(admin.TabularInline):
    """Inline for editing menu items directly within the Menu change form."""
    model = MenuItem
    extra = 1
    fields = ('title', 'url', 'parent', 'order')
    raw_id_fields = ('parent',) 

# --- Model Admin Classes ---

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for the custom user model."""
    # icon_name: 'fas fa-user' (Example for Jazzmin/AdminLTE)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'agency', 'agency_role')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'agency', 'agency_role')
    fieldsets = UserAdmin.fieldsets + (
        ('اطلاعات آژانس و نقش', {'fields': ('agency', 'agency_role')}),
    )
    
@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin configuration for the single site settings object."""
    # icon_name: 'fas fa-cogs'
    list_display = ('site_name', 'phone_number', 'email')
    fieldsets = (
        (None, {
            'fields': ('site_name', 'slogan', 'logo', 'favicon')
        }),
        ('اطلاعات تماس و رنگ‌بندی', {
            'fields': ('phone_number', 'email', 'address', 'primary_color', 'secondary_color', 'text_color'),
            'classes': ('collapse',),
        }),
        ('شبکه‌های اجتماعی و فوتر', {
            'fields': ('instagram_url', 'telegram_url', 'whatsapp_url', 'footer_text', 'enamad_code', 'copyright_text'),
            'classes': ('collapse',),
        }),
    )
    
    # Ensures only one record can be added/edited
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False # Prevent accidental deletion

@admin.register(AgencyUserRole)
class AgencyUserRoleAdmin(admin.ModelAdmin):
    """Admin configuration for user roles within an agency."""
    # icon_name: 'fas fa-user-tag'
    list_display = ('name',)
    list_display_links = ('name',)
    fields = ('name',) 

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    """Admin configuration for managing top-level menus and their items inline."""
    # icon_name: 'fas fa-list-alt'
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    inlines = [MenuItemInline]
    prepopulated_fields = {'slug': ('name',)}

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin configuration for individual menu items (used mostly for direct access/debugging)."""
    # icon_name: 'fas fa-link'
    list_display = ('title', 'menu', 'url', 'order', 'parent')
    list_filter = ('menu',)
    search_fields = ('title', 'url')
    ordering = ('menu', 'order')
    raw_id_fields = ('parent',)
