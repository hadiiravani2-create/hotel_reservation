# reservations/models.py
# version: 0.0.3
# CRITICAL FIX: Modified custom validators (validate_iranian_national_id and validate_iranian_mobile)
# to allow empty/None values, preventing ValidationError on optional fields for secondary guests.

import random
import time
from django.db import models
from django.conf import settings
from hotels.models import RoomType, BoardType
from django_jalali.db import models as jmodels
from django.core.exceptions import ValidationError
import re
from agencies.models import Agency

def generate_numeric_booking_code():
    """Generates a unique 8-digit numeric booking code based on timestamp and random part."""
    timestamp_part = str(int(time.time()))[-5:]
    random_part = str(random.randint(100, 999))
    return timestamp_part + random_part

class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'در انتظار پرداخت'),
        ('confirmed', 'تایید شده'),
        ('cancelled', 'لغو شده'),
        ('cancellation_requested', 'درخواست لغو شده'),
        ('modification_requested', 'درخواست ویرایش شده'),
    )

    booking_code = models.CharField(max_length=8, default=generate_numeric_booking_code, unique=True, verbose_name="کد رزرو")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings", verbose_name="کاربر رزرو کننده")
    
    check_in = jmodels.jDateField(verbose_name="تاریخ ورود")
    check_out = jmodels.jDateField(verbose_name="تاریخ خروج")

    # FIX: null=True و blank=True برای رفع IntegrityError و محاسبه قیمت در save_model
    total_price = models.DecimalField(max_digits=20, decimal_places=0, verbose_name="قیمت نهایی", null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings", verbose_name="رزرو برای آژانس")
    notification_sent = models.BooleanField(default=False, verbose_name="اطلاع‌رسانی ارسال شده؟")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین ویرایش")

    class Meta:
        verbose_name = "رزرو"
        verbose_name_plural = "رزروها"
        ordering = ['-created_at']

    def __str__(self):
        return f"رزرو {self.booking_code}"

class BookingRoom(models.Model):
    """
    این مدل واسط، رزرو را به انواع اتاق‌ها و تعداد آن‌ها متصل می‌کند.
    """
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="booking_rooms", verbose_name="رزرو")
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name="booking_rooms", verbose_name="نوع اتاق")
    board_type = models.ForeignKey(BoardType, on_delete=models.PROTECT, related_name="booking_rooms", verbose_name="نوع سرویس")
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name="تعداد اتاق")

    # فیلدهای نفرات اضافی در سطح اتاق
    adults = models.PositiveSmallIntegerField(default=0, verbose_name="تعداد نفرات اضافی (بالای ظرفیت پایه)")
    children = models.PositiveSmallIntegerField(default=0, verbose_name="تعداد کودکان این اتاق")
    # New field for extra guest requests
    extra_requests = models.TextField(blank=True, null=True, verbose_name="درخواست‌های اضافی اتاق")
    
    class Meta:
        verbose_name = "اتاق رزرو شده"
        verbose_name_plural = "اتاق‌های رزرو شده"
        unique_together = ('booking', 'room_type', 'board_type')

def validate_iranian_national_id(value):
    """Validates the format of the Iranian national ID, allowing empty values for optional fields."""
    if not value: # CRITICAL FIX: Allow empty or None value to pass validation
        return 
    if not re.match(r'^\d{10}$', value):
        raise ValidationError("کد ملی باید ۱۰ رقم باشد.")

def validate_iranian_mobile(value):
    """Validates the format of the Iranian mobile number, allowing empty values for optional fields."""
    if not value: # CRITICAL FIX: Allow empty or None value to pass validation
        return
    if not re.match(r'^09\d{9}$', value):
        raise ValidationError("شماره موبایل باید با 09 شروع شده و ۱۱ رقم باشد.")

class Guest(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="guests", verbose_name="رزرو")
    # FIX: Added blank=True for optional secondary guests
    first_name = models.CharField(max_length=100, blank=True, verbose_name="نام")
    last_name = models.CharField(max_length=100, blank=True, verbose_name="نام خانوادگی")

    is_foreign = models.BooleanField(default=False, verbose_name="میهمان خارجی است؟")
    # Custom validators are now safe for empty optional fields
    national_id = models.CharField(max_length=10, blank=True, null=True, verbose_name="کد ملی", validators=[validate_iranian_national_id])
    passport_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="شماره پاسپورت")
    phone_number = models.CharField(max_length=11, blank=True, null=True, verbose_name="شماره تماس", validators=[validate_iranian_mobile])
    nationality = models.CharField(max_length=50, blank=True, null=True, verbose_name="تابعیت")
    # New field for the city of origin
    city_of_origin = models.CharField(max_length=100, blank=True, null=True, verbose_name="شهر مبدأ")

    class Meta:
        verbose_name = "میهمان"
        verbose_name_plural = "میهمانان"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class PaymentTransaction(models.Model):
    """
    مدل برای ثبت تراکنش‌های درگاه پرداخت
    """
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payment_transactions", verbose_name="رزرو")
    amount = models.DecimalField(max_digits=20, decimal_places=0, verbose_name="مبلغ")
    transaction_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="شناسه تراکنش")
    is_successful = models.BooleanField(default=False, verbose_name="موفق بود؟")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    
    class Meta:
        verbose_name = "تراکنش پرداخت"
        verbose_name_plural = "تراکنش‌های پرداخت"

    def __str__(self):
        return f"تراکنش برای رزرو {self.booking.booking_code}"
