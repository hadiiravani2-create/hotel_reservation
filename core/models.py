# core/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from agencies.models import Agency

class AgencyUserRole(models.Model):
    """
    مدل برای تعریف نقش‌های مختلف کاربران زیرمجموعه آژانس
    """
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
    agency = models.ForeignKey(Agency, on_delete=models.SET_NULL, null=True, blank=True, related_name="users", verbose_name="آژانس")
    # فیلد جدید برای ارتباط با نقش کاربر در آژانس
    agency_role = models.ForeignKey(AgencyUserRole, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="نقش در آژانس")

class SiteSettings(models.Model):
    # بخش اطلاعات اصلی سایت
    site_name = models.CharField(max_length=100, default="نام سایت", verbose_name="نام وب‌سایت")
    slogan = models.CharField(max_length=255, blank=True, null=True, verbose_name="شعار یا توضیح کوتاه سایت")
    logo = models.ImageField(upload_to='site_settings/', blank=True, null=True, verbose_name="لوگو")
    favicon = models.ImageField(upload_to='site_settings/', blank=True, null=True, verbose_name="فایوآیکون (Favicon)")
    # فیلدهای جدید برای رنگ‌بندی
    primary_color = models.CharField(max_length=7, default="#007BFF", verbose_name="رنگ اصلی")
    secondary_color = models.CharField(max_length=7, default="#6c757d", verbose_name="رنگ ثانویه")
    text_color = models.CharField(max_length=7, default="#333333", verbose_name="رنگ متن")
    # بخش اطلاعات تماس
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="شماره تلفن")
    email = models.EmailField(blank=True, null=True, verbose_name="آدرس ایمیل")
    address = models.TextField(blank=True, null=True, verbose_name="آدرس فیزیکی")
    
    # بخش شبکه‌های اجتماعی
    instagram_url = models.URLField(blank=True, null=True, verbose_name="لینک اینستاگرام")
    telegram_url = models.URLField(blank=True, null=True, verbose_name="لینک تلگرام")
    whatsapp_url = models.URLField(blank=True, null=True, verbose_name="لینک واتس‌اپ")

    # بخش فوتر و کپی‌رایت
    footer_text = models.TextField(blank=True, null=True, verbose_name="متن کوتاه درباره ما در فوتر")
    enamad_code = models.TextField(blank=True, null=True, verbose_name="کد HTML اینماد")
    copyright_text = models.CharField(max_length=255, blank=True, null=True, verbose_name="متن کپی‌رایت")

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def __str__(self):
        return self.site_name
        
# مدل‌های جدید برای مدیریت منو
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
    # برای ایجاد منوهای تو در تو
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name="children", verbose_name="والد")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")

    class Meta:
        verbose_name = "آیتم منو"
        verbose_name_plural = "آیتم‌های منو"
        ordering = ['order']

    def __str__(self):
        return self.title


class PaymentSettings(models.Model):
    """
    مدل برای ذخیره تنظیمات پرداخت دستی
    """
    bank_name = models.CharField(max_length=100, verbose_name="نام بانک")
    account_number = models.CharField(max_length=50, verbose_name="شماره حساب")
    card_number = models.CharField(max_length=16, verbose_name="شماره کارت")
    sheba_number = models.CharField(max_length=24, verbose_name="شماره شبا")
    is_active = models.BooleanField(default=True, verbose_name="فعال است؟")

    class Meta:
        verbose_name = "تنظیمات پرداخت"
        verbose_name_plural = "تنظیمات پرداخت"

    def __str__(self):
        return f"تنظیمات پرداخت {self.bank_name}"
