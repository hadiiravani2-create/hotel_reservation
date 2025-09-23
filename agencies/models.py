# agencies/models.py

from django.db import models
from django.conf import settings
from hotels.models import Hotel, RoomType # RoomType را اضافه می‌کنیم
from django_jalali.db import models as jmodels
from jdatetime import date as jdate


class Agency(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="نام آژانس")
    contact_person = models.CharField(max_length=100, blank=True, null=True, verbose_name="فرد رابط")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="شماره تماس")
    credit_limit = models.DecimalField(max_digits=20, decimal_places=0, default=0, verbose_name="سقف اعتبار (تومان)")
    current_balance = models.DecimalField(max_digits=20, decimal_places=0, default=0, verbose_name="بدهی فعلی (تومان)")
    # فیلد جدید: درصد تخفیف پیش‌فرض
    credit_blacklist_hotels = models.ManyToManyField(Hotel, blank=True, verbose_name="هتل‌های لیست سیاه اعتباری")
    default_discount_percentage = models.PositiveSmallIntegerField(default=0, help_text="در صورتی که قراردادی برای هتل یافت نشود، این تخفیف اعمال می‌شود", verbose_name="درصد تخفیف پیش‌فرض")

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

    # به فیلد تاریخ، یک مقدار پیش‌فرض (تاریخ امروز) اضافه می‌کنیم
    transaction_date = jmodels.jDateField(verbose_name="تاریخ تراکنش", default=jdate.today)

    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="ثبت توسط")

    class Meta:
        verbose_name = "تراکنش مالی آژانس"
        verbose_name_plural = "تراکنش‌های مالی آژانس"
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.get_transaction_type_display()} برای {self.agency.name} به مبلغ {self.amount}"


class Contract(models.Model):
    CONTRACT_TYPES = (
        ('dynamic', 'درصد تخفیف'),
        ('static', 'نرخ ثابت'),
    )
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="contracts", verbose_name="آژانس")
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="contracts", verbose_name="هتل")
    # فیلدهای جدید
    title = models.CharField(max_length=255, verbose_name="عنوان قرارداد")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات قرارداد")

    start_date = jmodels.jDateField(verbose_name="تاریخ شروع قرارداد")
    end_date = jmodels.jDateField(verbose_name="تاریخ پایان قرارداد")
    contract_type = models.CharField(max_length=10, choices=CONTRACT_TYPES, verbose_name="نوع قرارداد")
    discount_percentage = models.PositiveSmallIntegerField(blank=True, null=True, help_text="فقط برای قراردادهای درصد تخفیف", verbose_name="درصد تخفیف")

    class Meta:
        verbose_name = "قرارداد"
        verbose_name_plural = "قراردادها"

    def __str__(self):
        return self.title

class StaticRate(models.Model):
    """
    این مدل جدید، قیمت‌های ثابت برای هر اتاق در یک قرارداد را نگهداری می‌کند
    """
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="static_rates", verbose_name="قرارداد")
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name="static_rates", verbose_name="نوع اتاق")
    price_per_night = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="قیمت پایه (تومان)")
    extra_person_price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="قیمت نفر اضافه (تومان)")
    child_price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="قیمت کودک (تومان)")

    class Meta:
        verbose_name = "نرخ ثابت"
        verbose_name_plural = "نرخ‌های ثابت"
        unique_together = ('contract', 'room_type')

    def __str__(self):
        return f"نرخ {self.room_type.name} برای قرارداد {self.contract.title}"
