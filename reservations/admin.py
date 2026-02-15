# FILE: back/reservations/admin.py
# version: 5.0.0
# STRATEGY: Back to Standard. Strict ReadOnly for Rooms/Financials.
# UI: CSS handles hiding buttons. Python handles Data Safety.

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.contenttypes.admin import GenericTabularInline
import traceback

from .models import Booking, Guest, BookingRoom, OfflineBank, PaymentConfirmation 
from .forms import BookingForm
from .pdf_utils import generate_booking_confirmation_pdf 

# ==========================================
# 1. INLINES
# ==========================================

class GuestInline(admin.TabularInline):
    """
    لیست مهمان‌ها: تنها جایی که ورودی (Input) دارد.
    """
    model = Guest
    extra = 0
    fields = ('first_name', 'last_name', 'national_id', 'phone_number')
    verbose_name = "میهمان"
    verbose_name_plural = "لیست میهمانان (جهت ویرایش)"
    can_delete = True

class BookingRoomInline(admin.TabularInline):
    """
    لیست اتاق‌ها: تبدیل شده به متن ساده (Read Only).
    این کار باعث می‌شود تمام دراپ‌داون‌ها و آیکون‌ها حذف شوند.
    """
    model = BookingRoom
    extra = 0
    # نکته: نام فیلدها باید دقیقاً با متدهای تعریف شده پایین یکی باشد
    fields = ('room_type_text', 'board_type_text', 'quantity', 'total_price_text')
    # این خط جادویی است که اینپوت‌ها را به متن تبدیل می‌کند:
    readonly_fields = ('room_type_text', 'board_type_text', 'quantity', 'total_price_text')
    
    can_delete = False
    max_num = 0 
    verbose_name = "اتاق"
    verbose_name_plural = "اتاق‌های رزرو شده"

    def room_type_text(self, obj):
        return obj.room_type.name
    room_type_text.short_description = "نوع اتاق"

    def board_type_text(self, obj):
        return obj.board_type.name
    board_type_text.short_description = "سرویس"

    def total_price_text(self, obj):
        return f"{obj.total_price:,}"
    total_price_text.short_description = "قیمت کل"

class PaymentConfirmationInline(GenericTabularInline):
    model = PaymentConfirmation
    extra = 0
    verbose_name = "تراکنش"
    verbose_name_plural = "واریزی‌ها"
    fields = ('offline_bank', 'tracking_code', 'payment_amount', 'payment_date', 'status_badge', 'action_btn')
    readonly_fields = ('offline_bank', 'tracking_code', 'payment_amount', 'payment_date', 'status_badge', 'action_btn')
    can_delete = False

    def status_badge(self, obj):
        if obj.is_verified:
            return format_html('<span style="color:green;">✅ تایید شده</span>')
        return format_html('<span style="color:orange;">⏳ بررسی نشده</span>')
    status_badge.short_description = "وضعیت"

    def action_btn(self, obj):
        if obj and obj.id and not obj.is_verified:
            url = reverse('admin:verify-payment-action', args=[obj.id])
            return format_html(
                '<a class="voucher-btn" style="background-color:green; padding:3px 8px; font-size:11px;" href="{}">✓ تایید</a>',
                url
            )
        return "-"
    action_btn.short_description = "عملیات"


# ==========================================
# 2. MAIN ADMIN
# ==========================================

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingForm
    list_display = ('booking_code', 'user_display', 'check_in_jalali', 'status_badge', 'total_price_display')
    list_filter = ('status', 'check_in')
    search_fields = ('booking_code', 'user__username', 'guests__last_name')
    
    inlines = [PaymentConfirmationInline, BookingRoomInline, GuestInline]

    # لیست فیلدهایی که نباید قابل ویرایش باشند
    readonly_fields = (
        'voucher_download_link', # دکمه دانلود ووچر
        'booking_code', 
        'user', 'agency',        # کاربر و آژانس فقط خواندنی
        'total_price', 'paid_amount', 'total_vat', 'total_service_price',
        'check_in', 'check_out', 'duration_display',
        'created_at', 'updated_at'
    )

    fieldsets = (
        ('عملیات', {
            'fields': ('voucher_download_link', 'status')
        }),
        ('اطلاعات رزرو (غیرقابل تغییر)', {
            'fields': (
                ('booking_code', 'user'),
                ('check_in', 'check_out', 'duration_display'),
                ('agency',)
            )
        }),
        ('وضعیت مالی', {
            'fields': (
                ('total_price', 'paid_amount'),
                ('total_vat', 'total_service_price')
            )
        }),
        ('تاریخچه', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    class Media:
        css = { 'all': ('admin/css/custom_admin.css',) }

    # --- Actions ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:booking_id>/download-voucher/', self.admin_site.admin_view(self.download_voucher_view), name='booking-download-voucher'),
            path('verify-payment/<int:payment_id>/', self.admin_site.admin_view(self.process_payment_verification), name='verify-payment-action'),
        ]
        return custom_urls + urls

    def download_voucher_view(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)
        try:
            pdf_bytes = generate_booking_confirmation_pdf(booking)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Voucher_{booking.booking_code}.pdf"'
            return response
        except Exception:
            traceback.print_exc()
            self.message_user(request, "خطا در تولید PDF", messages.ERROR)
            return redirect(request.META.get('HTTP_REFERER', 'admin:index'))

    def process_payment_verification(self, request, payment_id):
        payment = get_object_or_404(PaymentConfirmation, id=payment_id)
        if not payment.is_verified:
            payment.is_verified = True
            payment.save()
            booking = payment.content_object
            if isinstance(booking, Booking):
                booking.paid_amount += payment.payment_amount
                if booking.paid_amount >= booking.total_price and booking.status == 'awaiting_confirmation':
                    booking.status = 'confirmed'
                booking.save()
                self.message_user(request, "پرداخت تایید شد.", messages.SUCCESS)
        return redirect(request.META.get('HTTP_REFERER', 'admin:index'))

    # --- Display Fields ---
    def voucher_download_link(self, obj):
        if obj.pk:
            url = reverse('admin:booking-download-voucher', args=[obj.pk])
            return format_html(
                '<a class="voucher-btn" href="{}" target="_blank">📥 دانلود ووچر (PDF)</a>',
                url
            )
        return "-"
    voucher_download_link.short_description = "ووچر"
    voucher_download_link.allow_tags = True

    def user_display(self, obj):
        return obj.user.get_full_name() or obj.user.username if obj.user else "مهمان"
    user_display.short_description = "کاربر"

    def status_badge(self, obj):
        colors = {'pending': 'orange', 'confirmed': 'green', 'cancelled': 'red', 'awaiting_confirmation': 'blue'}
        color = colors.get(obj.status, 'black')
        # استایل خطی ساده برای سازگاری با همه تم‌ها
        return format_html(f'<span style="color:{color}; font-weight:bold;">{obj.get_status_display()}</span>')
    status_badge.short_description = "وضعیت"

    def total_price_display(self, obj):
        return f"{obj.total_price:,}"
    total_price_display.short_description = "مبلغ"

    def check_in_jalali(self, obj):
        return obj.check_in.strftime("%Y/%m/%d")
    check_in_jalali.short_description = "ورود"

    def duration_display(self, obj):
        return f"{obj.get_duration_days()} شب" if obj.check_in else "-"
    duration_display.short_description = "مدت"

# --- Other Admins ---
@admin.register(OfflineBank)
class OfflineBankAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'card_number', 'is_active')

@admin.register(PaymentConfirmation)
class PaymentConfirmationAdmin(admin.ModelAdmin):
    list_display = ('tracking_code', 'payment_amount', 'is_verified')
