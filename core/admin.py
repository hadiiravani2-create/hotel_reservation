# core/admin.py
# version: 0.0.6
# FEATURE: Registered Wallet and WalletTransaction models to the admin panel.

from django.contrib import admin
from django.db import models
from django.contrib.auth.admin import UserAdmin
from django.forms import inlineformset_factory
from jalali_date.widgets import AdminJalaliDateWidget
from .models import CustomUser, SiteSettings, Menu, MenuItem, AgencyUserRole, Wallet, WalletTransaction, SpecialPeriod

# --- Custom Inline for Menu Items ---
class MenuItemInline(admin.TabularInline):
    """Inline for editing menu items directly within the Menu change form."""
    model = MenuItem
    extra = 1
    fields = ('title', 'url', 'parent', 'order')
    raw_id_fields = ('parent',)

# --- NEW: Wallet Inlines and Admins ---

class WalletTransactionInline(admin.TabularInline):
    """
    Inline view for wallet transactions. All fields are read-only as transactions are immutable.
    """
    model = WalletTransaction
    extra = 0
    readonly_fields = ('transaction_type', 'amount', 'booking', 'description', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(SpecialPeriod)
class SpecialPeriodAdmin(admin.ModelAdmin):
    """
    Admin interface for managing Special Periods (e.g., peak seasons).
    Uses Jalali calendar widgets and filters, similar to pricing forms.
    """
    list_display = ('name', 'start_date', 'end_date')
    search_fields = ('name',)
    list_filter = ('start_date', 'end_date')
    ordering = ('-start_date',)

    formfield_overrides = {
        models.DateField: {'widget': AdminJalaliDateWidget},
    }

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Admin configuration for the Wallet model."""
    list_display = ('user', 'balance', 'calculated_balance')
    search_fields = ('user__username',)
    # The balance field is read-only because it should be updated via signals from transactions.
    readonly_fields = ('user', 'balance', 'calculated_balance')
    inlines = [WalletTransactionInline]

    def calculated_balance(self, obj):
        """A method to display the real-time calculated balance for verification."""
        return obj.calculate_balance()
    calculated_balance.short_description = "موجودی محاسبه شده"

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    """
    Admin configuration for WalletTransaction. Primarily for viewing, searching, and filtering.
    Transactions should not be editable.
    """
    list_display = ('wallet', 'transaction_type', 'amount', 'booking', 'created_at')
    list_filter = ('transaction_type',)
    search_fields = ('wallet__user__username', 'booking__booking_code', 'description')
    readonly_fields = ('wallet', 'transaction_type', 'amount', 'booking', 'description', 'created_at')
    
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# --- Existing Model Admin Classes ---

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for the custom user model."""
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'agency', 'agency_role')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'agency', 'agency_role')
    fieldsets = UserAdmin.fieldsets + (
        ('اطلاعات آژانس و نقش', {'fields': ('agency', 'agency_role')}),
    )
    
@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin configuration for the single site settings object."""
    list_display = ('site_name', 'phone_number', 'email')
    # ... (rest of the class remains unchanged)

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(AgencyUserRole)
class AgencyUserRoleAdmin(admin.ModelAdmin):
    """Admin configuration for user roles within an agency."""
    list_display = ('name',)
    list_display_links = ('name',)
    fields = ('name',)

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    """Admin configuration for managing top-level menus and their items inline."""
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')
    inlines = [MenuItemInline]
    prepopulated_fields = {'slug': ('name',)}

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin configuration for individual menu items."""
    list_display = ('title', 'menu', 'url', 'order', 'parent')
    list_filter = ('menu',)
    search_fields = ('title', 'url')
    ordering = ('menu', 'order')
    raw_id_fields = ('parent',)
