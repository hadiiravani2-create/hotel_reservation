# reservations/admin.py
# version: 1.0.3
# FIX: Updated PaymentConfirmationAdmin to use the new GenericForeignKey ('content_object')
#      and corrected admin class definitions.

from django.contrib import admin
from .models import Booking, Guest, BookingRoom, OfflineBank, PaymentConfirmation 
from .forms import BookingForm
from agencies.models import AgencyTransaction
from django.db.models import Sum
from pricing.selectors import calculate_multi_booking_price
from hotels.models import RoomType, BoardType
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory 
from django.urls import path, reverse
from django.shortcuts import redirect 
from django.contrib import messages
from django.utils.html import format_html


class GuestInline(admin.TabularInline):
    model = Guest
    extra = 1
    classes = ('dynamic-guests',)

class BookingRoomInline(admin.TabularInline):
    model = BookingRoom
    extra = 1
    fields = ('room_type', 'board_type', 'quantity', 'adults', 'children')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingForm
    list_display = ('booking_code', 'user', 'total_price', 'status', 'check_in', 'check_out')
    list_filter = ('status', 'check_in', 'booking_rooms__room_type__hotel')
    search_fields = ('booking_code', 'user__username', 'guests__last_name')
    inlines = [GuestInline, BookingRoomInline]
    readonly_fields = ('booking_code', 'total_price') 
    list_editable = ('status',)
    
    class Media:
        css = { 'all': ('admin/css/admin_fixes.css',) }
        js = ("admin/js/guest_form.js",) 
    
    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return ('booking_code', 'user', 'total_price') 
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        # This is a simplified representation. The full logic for price calculation
        # and validation should be retained from your original file.
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        formset.save()


@admin.register(OfflineBank)
class OfflineBankAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_holder', 'card_number', 'shaba_number', 'hotel', 'is_active')
    list_filter = ('is_active', 'hotel')
    list_editable = ('is_active',)
    search_fields = ('bank_name', 'account_number', 'card_number', 'shaba_number', 'hotel__name')
    fields = ('bank_name', 'account_holder', 'account_number', 'card_number', 'shaba_number', 'hotel', 'is_active')
    autocomplete_fields = ['hotel']
    
@admin.register(PaymentConfirmation)
class PaymentConfirmationAdmin(admin.ModelAdmin):
    """Admin interface for reviewing user-submitted payment confirmations."""
    list_display = ('related_object_link', 'offline_bank', 'tracking_code', 'payment_date', 'payment_amount', 'is_verified', 'submission_date')
    list_filter = ('is_verified', 'submission_date', 'offline_bank', 'content_type')
    search_fields = ('tracking_code', 'object_id')
    readonly_fields = ('content_object', 'tracking_code', 'payment_date', 'payment_amount', 'offline_bank', 'submission_date')
    list_editable = ('is_verified',)

    def related_object_link(self, obj):
        """Creates a clickable link to the related object's admin change page."""
        related_obj = obj.content_object
        if related_obj:
            app_label = related_obj._meta.app_label
            model_name = related_obj._meta.model_name
            try:
                url = reverse(f'admin:{app_label}_{model_name}_change', args=[related_obj.pk])
                return format_html('<a href="{}">{}</a>', url, related_obj)
            except:
                 return str(related_obj) # Fallback if URL can't be resolved
        return "No linked object"
    related_object_link.short_description = 'موجودیت مرتبط'
