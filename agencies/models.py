# agencies/models.py v1.2
# Feature: Added priority field to Contract model to resolve ambiguity.
from django.db import models
from django.conf import settings
from hotels.models import Hotel, RoomType
from django_jalali.db import models as jmodels
from jdatetime import date as jdate


class Agency(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="نام آژانس")
    contact_person = models.CharField(max_length=100, blank=True, null=True, verbose_name="فرد رابط")
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="شماره تماس")
    credit_limit = models.DecimalField(max_digits=20, decimal_places=0, default=0, verbose_name="سقف اعتبار (تومان)")
    current_balance = models.DecimalField(max_digits=20, decimal_places=0, default=0, verbose_name="بدهی فعلی (تومان)")
    credit_blacklist_hotels = models.ManyToManyField(Hotel, blank=True, verbose_name="هتل‌های لیست سیاه اعتباری")
    default_discount_percentage = models.PositiveSmallIntegerField(default=0, help_text="در صورتی که قراردادی برای هتل یافت نشود، این تخفیف اعمال می‌شود", verbose_name="درصد تخفیف پیش‌فرض")

    class Meta:
        verbose_name = "آژانس"
        verbose_name_plural = "آژانس‌ها"

    def __str__(self):
        return self.name

class AgencyUser(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agency_profile", verbose_name="کاربر")
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="profiles", verbose_name="آژانس")

    class Meta:
        verbose_name = "کاربر آژانس"
        verbose_name_plural = "کاربران آژانس"
        unique_together = ('user', 'agency')

    def __str__(self):
        return f"{self.user.username} - {self.agency.name}"


class AgencyTransaction(models.Model):
    TRANSACTION_TYPES = (('booking', 'رزرو اعتباری'), ('payment', 'پرداخت/تسویه'), ('adjustment', 'اصلاح حساب'))
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="transactions", verbose_name="آژانس")
    booking = models.ForeignKey('reservations.Booking', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="رزرو مرتبط")
    amount = models.DecimalField(max_digits=20, decimal_places=0, verbose_name="مبلغ")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name="نوع تراکنش")
    transaction_date = jmodels.jDateField(verbose_name="تاریخ تراکنش", default=jdate.today)
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    tracking_code = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره پیگیری/تراکنش")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="ثبت توسط")

    class Meta:
        verbose_name = "تراکنش مالی آژانس"
        verbose_name_plural = "تراکنش‌های مالی آژانس"
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.get_transaction_type_display()} برای {self.agency.name} به مبلغ {self.amount}"

    @property
    def signed_amount(self):
        if self.transaction_type == 'payment': return -self.amount
        return self.amount


class Contract(models.Model):
    CONTRACT_TYPES = (('dynamic', 'درصد تخفیف'), ('static', 'نرخ ثابت'))
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name="contracts", verbose_name="آژانس")
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="contracts", verbose_name="هتل")
    title = models.CharField(max_length=255, verbose_name="عنوان قرارداد")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات قرارداد")
    start_date = jmodels.jDateField(verbose_name="تاریخ شروع قرارداد")
    end_date = jmodels.jDateField(verbose_name="تاریخ پایان قرارداد")
    contract_type = models.CharField(max_length=10, choices=CONTRACT_TYPES, verbose_name="نوع قرارداد")
    discount_percentage = models.PositiveSmallIntegerField(blank=True, null=True, help_text="فقط برای قراردادهای درصد تخفیف", verbose_name="درصد تخفیف")
    # --- START: Added priority field ---
    priority = models.PositiveSmallIntegerField(default=0, help_text="قرارداد با عدد بالاتر، اولویت بیشتری دارد", verbose_name="اولویت")
    # --- END: Added priority field ---

    class Meta:
        verbose_name = "قرارداد"
        verbose_name_plural = "قراردادها"
        # --- START: Added ordering by priority ---
        ordering = ['-priority']
        # --- END: Added ordering by priority ---

    def __str__(self):
        return self.title

class StaticRate(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="static_rates", verbose_name="قرارداد")
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name="static_rates", verbose_name="نوع اتاق")
    price_per_night = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="قیمت پایه (تومان)")
    extra_person_price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="قیمت هر نفر اضافه (تومان)")
    child_price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="قیمت هر کودک (تومان)")

    class Meta:
        verbose_name = "نرخ ثابت"
        verbose_name_plural = "نرخ‌های ثابت"
        unique_together = ('contract', 'room_type')

    def __str__(self):
        return f"نرخ {self.room_type.name} برای قرارداد {self.contract.title}"
