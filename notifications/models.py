# notifications/models.py

from django.db import models

class SmsSettings(models.Model):
    provider_name = models.CharField(max_length=100, default="فراز اس‌ام‌اس", verbose_name="نام سرویس‌دهنده")
    api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="کلید API")
    sender_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="شماره خط ارسال‌کننده")
    is_active = models.BooleanField(default=False, help_text="تنها یک کانفیگ می‌تواند فعال باشد.", verbose_name="فعال است؟")

    class Meta:
        verbose_name = "تنظیمات پیامک"
        verbose_name_plural = "تنظیمات پیامک"

    def __str__(self):
        return self.provider_name

class EmailSettings(models.Model):
    provider_name = models.CharField(max_length=100, verbose_name="نام سرویس‌دهنده (مثلا: ایمیل اصلی)")
    host = models.CharField(max_length=255, verbose_name="هاست (Host)")
    port = models.PositiveIntegerField(default=587, verbose_name="پورت (Port)")
    username = models.CharField(max_length=255, verbose_name="نام کاربری")
    password = models.CharField(max_length=255, verbose_name="رمز عبور")
    use_tls = models.BooleanField(default=True, verbose_name="استفاده از TLS")
    use_ssl = models.BooleanField(default=False, verbose_name="استفاده از SSL")
    is_active = models.BooleanField(default=False, help_text="تنها یک کانفیگ می‌تواند فعال باشد.", verbose_name="فعال است؟")

    class Meta:
        verbose_name = "تنظیمات ایمیل"
        verbose_name_plural = "تنظیمات ایمیل"

    def __str__(self):
        return self.provider_name

    def save(self, *args, **kwargs):
        if self.is_active:
            EmailSettings.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


