# services/admin.py
# version: 1.0.0
# Initial creation of the admin panel configuration for the services module.

from django.contrib import admin
from .models import ServiceType, HotelService, BookedService

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    """
    Admin configuration for ServiceType model.
    """
    list_display = ('name', 'requires_details')
    search_fields = ('name',)

@admin.register(HotelService)
class HotelServiceAdmin(admin.ModelAdmin):
    """
    Admin configuration for HotelService model.
    Allows for easy filtering and searching.
    """
    list_display = ('name', 'hotel', 'service_type', 'pricing_model', 'price')
    list_filter = ('hotel', 'service_type', 'pricing_model')
    search_fields = ('name', 'hotel__name')
    autocomplete_fields = ('hotel',) # For easier hotel selection

@admin.register(BookedService)
class BookedServiceAdmin(admin.ModelAdmin):
    """
    Admin configuration for BookedService model.
    Primarily for viewing and debugging purposes.
    """
    list_display = ('booking', 'hotel_service', 'quantity', 'total_price')
    list_filter = ('hotel_service__hotel',)
    search_fields = ('booking__booking_code', 'hotel_service__name')
    readonly_fields = ('booking', 'hotel_service', 'quantity', 'total_price', 'details') # These should not be editable

    def has_add_permission(self, request):
        # Prevent manual creation of BookedService from the admin
        return False
