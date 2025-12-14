# core/models.py
# version: 1.1.3
# FIX: Removed 'reservations.models' import to break circular dependency chain (Core -> Reservations -> Hotels -> Core).

import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Sum
from django.conf import settings

# REMOVED: try/except block for importing Booking. String reference is sufficient.

# --- NEW ABSTRACT MODEL ---
# This must be defined BEFORE any other model imports it.
class ImageMetadata(models.Model):
    """
    Abstract base class for models that require image metadata such as caption and display order.
    Used to implement DRY principle for similar image-related models.
    """
    caption = models.CharField(max_length=255, blank=True, null=True, verbose_name="توضیحات تصویر")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    
    class Meta:
        abstract = True
        ordering = ['order']

# --- EXISTING MODELS ---

class AgencyUserRole(models.Model):
    ROLE_CHOICES = (
        ('admin', 'مدیر آژانس'),
        ('booking_agent', 'کاربر رزرو'),
        ('finance_manager', 'مدیر مالی'),
        ('viewer', 'فقط مشاهده‌گر'),
    )
    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True, verbose_name="نقش")
    class Meta:
        verbose_name = "نقش کاربر آژانس"
        verbose_name_plural = "نقش‌های کاربران آژانس"
    def __str__(self):
        return self.get_name_display()

class CustomUser(AbstractUser):
    # Using string reference for Agency to avoid circular import with agencies app
    agency = models.ForeignKey('agencies.Agency', on_delete=models.SET_NULL, null=True, blank=True, related_name="users", verbose_name="آژانس")
    agency_role = models.ForeignKey(AgencyUserRole, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="نقش در آژانس")

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet', verbose_name="کاربر")
    balance = models.DecimalField(max_digits=20, decimal_places=0, default=0, verbose_name="موجودی")
    class Meta:
        verbose_name = "کیف پول"
        verbose_name_plural = "کیف‌های پول"
    def __str__(self):
        return f"کیف پول کاربر {self.user.username}"
    def calculate_balance(self):
        aggregation = self.transactions.filter(status='completed').aggregate(
            calculated_balance=Sum('amount')
        )
        return aggregation.get('calculated_balance') or 0

class WalletTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'شارژ کیف پول'),
        ('payment', 'پرداخت رزرو'),
        ('refund', 'بازگشت وجه لغو رزرو'),
        ('withdrawal', 'برداشت از کیف پول'),
        ('gift', 'اعتبار هدیه'),
        ('adjustment', 'اصلاح حساب توسط مدیر'),
    )
    STATUS_CHOICES = (
        ('pending', 'در انتظار'),
        ('completed', 'انجام شده'),
        ('failed', 'ناموفق'),
    )
    
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name="شناسه تراکنش")
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions', verbose_name="کیف پول")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name="نوع تراکنش")
    amount = models.DecimalField(max_digits=20, decimal_places=0, help_text="مبالغ مثبت برای واریز و مبالغ منفی برای برداشت", verbose_name="مبلغ")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    # Using string reference for Booking to avoid circular import with reservations app
    booking = models.ForeignKey('reservations.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='wallet_transactions', verbose_name="رزرو مرتبط")
    description = models.CharField(max_length=255, blank=True, null=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")

    class Meta:
        verbose_name = "تراکنش کیف پول"
        verbose_name_plural = "تراکنش‌های کیف پول"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} ({self.get_status_display()}) - {self.wallet.user.username}"

class SpecialPeriod(models.Model):
    name = models.CharField(max_length=255, verbose_name="نام دوره", help_text="مثال: نوروز ۱۴۰۵")
    start_date = models.DateField(verbose_name="تاریخ شروع")
    end_date = models.DateField(verbose_name="تاریخ پایان")

    class Meta:
        verbose_name = "دوره زمانی خاص"
        verbose_name_plural = "دوره‌های زمانی خاص"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

class SiteSettings(models.Model):
    site_name = models.CharField(max_length=100, default="نام سایت", verbose_name="نام وب‌سایت")
    slogan = models.CharField(max_length=255, blank=True, null=True, verbose_name="شعار یا توضیح کوتاه سایت")
    logo = models.ImageField(upload_to='site_settings/', blank=True, null=True, verbose_name="لوگو")
    favicon = models.ImageField(upload_to='site_settings/', blank=True, null=True, verbose_name="فایوآیکون (Favicon)")
    primary_color = models.CharField(max_length=7, default="#007BFF", verbose_name="رنگ اصلی")
    secondary_color = models.CharField(max_length=7, default="#6c757d", verbose_name="رنگ ثانویه")
    text_color = models.CharField(max_length=7, default="#333333", verbose_name="رنگ متن")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="شماره تلفن")
    email = models.EmailField(blank=True, null=True, verbose_name="آدرس ایمیل")
    address = models.TextField(blank=True, null=True, verbose_name="آدرس فیزیکی")
    instagram_url = models.URLField(blank=True, null=True, verbose_name="لینک اینستاگرام")
    telegram_url = models.URLField(blank=True, null=True, verbose_name="لینک تلگرام")
    whatsapp_url = models.URLField(blank=True, null=True, verbose_name="لینک واتس‌اپ")
    footer_text = models.TextField(blank=True, null=True, verbose_name="متن کوتاه درباره ما در فوتر")
    enamad_code = models.TextField(blank=True, null=True, verbose_name="کد HTML اینماد")
    copyright_text = models.CharField(max_length=255, blank=True, null=True, verbose_name="متن کپی‌رایت")
    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"
    def __str__(self):
        return self.site_name

class Menu(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="نام منو")
    slug = models.SlugField(unique=True, help_text="برای فراخوانی در کد استفاده می‌شود (مثلا: main-menu)")
    class Meta:
        verbose_name = "منو"
        verbose_name_plural = "منوها"
    def __str__(self):
        return self.name

class MenuItem(models.Model):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="items", verbose_name="منوی اصلی")
    title = models.CharField(max_length=100, verbose_name="عنوان لینک")
    url = models.CharField(max_length=255, verbose_name="آدرس URL")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name="children", verbose_name="والد")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    class Meta:
        verbose_name = "آیتم منو"
        verbose_name_plural = "آیتم‌های منو"
        ordering = ['order']
    def __str__(self):
        return self.title
