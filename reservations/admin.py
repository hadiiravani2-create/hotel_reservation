# FILE: hotel_reservation/reservations/admin.py
# version: 1.1.2
# FIX: Resolved FieldError by replacing 'duration' with 'duration_display' method in fieldsets and readonly_fields.

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from django.urls import path, reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.contenttypes.admin import GenericTabularInline

from .models import Booking, Guest, BookingRoom, OfflineBank, PaymentConfirmation 
from .forms import BookingForm
from agencies.models import AgencyTransaction
from pricing.selectors import calculate_multi_booking_price
from hotels.models import RoomType, BoardType

# --- Inlines ---

class GuestInline(admin.TabularInline):
    model = Guest
    extra = 1
    classes = ('dynamic-guests',)
    fields = ('first_name', 'last_name', 'national_id', 'phone_number', 'is_foreign')

class BookingRoomInline(admin.TabularInline):
    model = BookingRoom
    extra = 1
    # price_per_night removed to avoid errors as it is calculated on the fly usually
    fields = ('room_type', 'board_type', 'quantity', 'adults', 'children')
    
class PaymentConfirmationInline(GenericTabularInline):
    """
    Inline admin to show payment confirmations directly inside the Booking page.
    """
    model = PaymentConfirmation
    extra = 0
    fields = ('tracking_code', 'offline_bank', 'payment_amount', 'payment_date', 'is_verified', 'status_badge')
    readonly_fields = ('submission_date', 'status_badge')
    verbose_name = "تراکنش مالی"
    verbose_name_plural = "لیست واریزی‌ها (تطبیق مالی)"
    can_delete = True

    def status_badge(self, obj):
        if obj.is_verified:
            return format_html('<span style="color:white; background:green; padding:3px 8px; border-radius:5px;">تایید شده</span>')
        return format_html('<span style="color:white; background:orange; padding:3px 8px; border-radius:5px;">در انتظار بررسی</span>')
    status_badge.short_description = "وضعیت"


# --- Admins ---

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingForm
    list_display = (
        'booking_code', 
        'user_link', 
        'hotel_name_display',
        'check_in_jalali', 
        'total_price_display', 
        'paid_amount_display', 
        'status', 
    )
    list_filter = ('status', 'check_in', 'booking_rooms__room_type__hotel')
    search_fields = ('booking_code', 'user__username', 'guests__last_name', 'guests__national_id')
    inlines = [GuestInline, BookingRoomInline, PaymentConfirmationInline]
    
    # FIX: Added 'duration_display' to readonly fields so it can be used in fieldsets
    readonly_fields = ('booking_code', 'total_price', 'created_at', 'updated_at', 'duration_display') 
    
    list_editable = ('status',)
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': (('booking_code', 'status'), 'user', 'agency')
        }),
        ('اطلاعات زمانی', {
            # FIX: Changed 'duration' to 'duration_display'
            'fields': (('check_in', 'check_out'), 'duration_display')
        }),
        ('اطلاعات مالی', {
            'fields': (('total_price', 'paid_amount'),),
            'description': 'در صورتی که مبلغ پرداخت شده با مبلغ کل برابر باشد، وضعیت رزرو می‌تواند تایید شود.'
        }),
        ('تاریخچه', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    class Media:
        css = { 'all': ('admin/css/admin_fixes.css',) }
        js = ("admin/js/guest_form.js",) 

    # --- Custom Methods for List/Readonly Display ---

    def duration_display(self, obj):
        """Calculates duration based on check-in/out for display."""
        if obj.check_in and obj.check_out:
            return f"{obj.get_duration_days()} شب"
        return "-"
    duration_display.short_description = "مدت اقامت"

    def user_link(self, obj):
        return obj.user.get_full_name() if obj.user else "کاربر مهمان"
    user_link.short_description = "کاربر"

    def hotel_name_display(self, obj):
        first_room = obj.booking_rooms.first()
        return first_room.room_type.hotel.name if first_room else "-"
    hotel_name_display.short_description = "هتل"

    def check_in_jalali(self, obj):
        return obj.check_in.strftime("%Y/%m/%d")
    check_in_jalali.short_description = "تاریخ ورود"

    def total_price_display(self, obj):
        return f"{obj.total_price:,} تومان"
    total_price_display.short_description = "مبلغ کل"

    def paid_amount_display(self, obj):
        """Visualizes the financial status (Green if fully paid, Red if debt)."""
        if obj.paid_amount >= obj.total_price:
            return format_html('<span style="color: green; font-weight: bold;">تسویه شده</span>')
        remaining = obj.total_price - obj.paid_amount
        return format_html(
            f'<span style="color: red;">{obj.paid_amount:,} (مانده: {remaining:,})</span>'
        )
    paid_amount_display.short_description = "پرداختی / مانده"

    # --- Bulk Actions ---
    actions = ['mark_as_confirmed', 'mark_as_cancelled']

    def mark_as_confirmed(self, request, queryset):
        rows_updated = queryset.update(status='confirmed')
        self.message_user(request, f"{rows_updated} رزرو به وضعیت تایید شده تغییر یافتند.")
    mark_as_confirmed.short_description = "تایید رزروهای انتخاب شده"

    def mark_as_cancelled(self, request, queryset):
        rows_updated = queryset.update(status='cancelled')
        self.message_user(request, f"{rows_updated} رزرو لغو شدند.")
    mark_as_cancelled.short_description = "لغو رزروهای انتخاب شده"

    # --- Overridden Methods ---

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return ('booking_code', 'user', 'total_price', 'paid_amount', 'created_at', 'updated_at', 'duration_display') 
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
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
    list_display = (
        'related_object_link', 
        'offline_bank', 
        'tracking_code', 
        'payment_date', 
        'payment_amount', 
        'is_verified', 
        'submission_date'
    )
    list_filter = ('is_verified', 'submission_date', 'offline_bank', 'content_type')
    search_fields = ('tracking_code', 'object_id')
    readonly_fields = ('content_object', 'tracking_code', 'payment_date', 'payment_amount', 'offline_bank', 'submission_date')
    list_editable = ('is_verified',)

    def related_object_link(self, obj):
        """Creates a clickable link to the related object's admin change page."""
        related_obj = obj.content_object
        if related_obj:
            try:
                app_label = related_obj._meta.app_label
                model_name = related_obj._meta.model_name
                url = reverse(f'admin:{app_label}_{model_name}_change', args=[related_obj.pk])
                return format_html('<a href="{}">{}</a>', url, related_obj)
            except:
                return str(related_obj)
        return "No linked object"
    related_object_link.short_description = 'موجودیت مرتبط'
