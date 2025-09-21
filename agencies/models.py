# agencies/models.py

from django.db import models
from django.conf import settings
from hotels.models import Hotel
from django_jalali.db import models as jmodels

class Agency(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="نام آژانس")
    contact_person = models.CharField(max_length=100, blank=True, null=True, verbose_name="فرد رابط")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="شماره تماس")
    credit_limit = models.DecimalField(max_digits=20, decimal_places=0, default=0, verbose_name="سقف اعتبار (تومان)")
    current_balance = models.DecimalField(max_digits=20, decimal_places=0, default=0, verbose_name="بدهی فعلی (تومان)")

    class Meta:
        verbose_name = "آژانس"
        verbose_name_plural = "آژانس‌ها"

    def __str__(self):
        return self.name

class AgencyTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('booking', 'رزرو اعتباری'),
        ('payment', 'پرداخت/تسویه'),
        ('adjustment', 'اصلاح حساب'),
    )
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="transactions", verbose_name="آژانس")
    booking = models.ForeignKey('reservations.Booking', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="رزرو مرتبط")
    amount = models.DecimalField(max_digits=20, decimal_places=0, verbose_name="مبلغ")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name="نوع تراکنش")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="ثبت توسط")

    class Meta:
        verbose_name = "تراکنش مالی آژانس"
        verbose_name_plural = "تراکنش‌های مالی آژانس"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_transaction_type_display()} برای {self.agency.name} به مبلغ {self.amount}"

class Contract(models.Model):
    CONTRACT_TYPES = (
        ('dynamic', 'درصد تخفیف'),
        ('static', 'قیمت ثابت'),
    )
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="contracts", verbose_name="آژانس")
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="contracts", verbose_name="هتل")
    start_date = jmodels.jDateField(verbose_name="تاریخ شروع قرارداد")
    end_date = jmodels.jDateField(verbose_name="تاریخ پایان قرارداد")
    contract_type = models.CharField(max_length=10, choices=CONTRACT_TYPES, verbose_name="نوع قرارداد")
    discount_percentage = models.PositiveSmallIntegerField(blank=True, null=True, help_text="فقط برای قراردادهای درصد تخفیف", verbose_name="درصد تخفیف")
    static_rates = models.JSONField(blank=True, null=True, help_text="فقط برای قراردادهای قیمت ثابت. مثال: {\"room_type_id_1\": 250000}", verbose_name="نرخ‌های ثابت")
    credit_blacklist_hotels = models.ManyToManyField(Hotel, blank=True, related_name="blacklisted_contracts", verbose_name="هتل‌های لیست سیاه اعتباری")

    class Meta:
        verbose_name = "قرارداد"
        verbose_name_plural = "قراردادها"

    def __str__(self):
        return f"قرارداد {self.agency.name} با {self.hotel.name}"