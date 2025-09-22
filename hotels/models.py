# hotels/models.py

from django.db import models
from django.conf import settings

class City(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام شهر")

    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"

    def __str__(self):
        return self.name

class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام امکانات")

    class Meta:
        verbose_name = "امکانات رفاهی"
        verbose_name_plural = "امکانات رفاهی"

    def __str__(self):
        return self.name

class Hotel(models.Model):
    name = models.CharField(max_length=255, verbose_name="نام هتل")
    stars = models.PositiveSmallIntegerField(default=3, verbose_name="ستاره هتل")
    description = models.TextField(verbose_name="توضیحات هتل", null=True, blank=True)
    address = models.CharField(max_length=500, verbose_name="آدرس")
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="hotels", verbose_name="شهر")
    amenities = models.ManyToManyField(Amenity, blank=True, verbose_name="امکانات رفاهی")
    # vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hotels") # Todo uncomment

    class Meta:
        verbose_name = "هتل"
        verbose_name_plural = "هتل‌ها"
        unique_together = ('name', 'city') # unique

    def __str__(self):
        return self.name



class RoomType(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="room_types", verbose_name="هتل")
    name = models.CharField(max_length=100, verbose_name="نام نوع اتاق")
    description = models.TextField(verbose_name="توضیحات نوع اتاق", null=True, blank=True)
    base_capacity = models.PositiveSmallIntegerField(default=2, verbose_name="ظرفیت پایه (نفر)")
    price_per_night = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="قیمت پایه هر شب (تومان)")

    extra_capacity = models.PositiveSmallIntegerField(default=0, verbose_name="ظرفیت نفر اضافه")
    child_capacity = models.PositiveSmallIntegerField(default=0, verbose_name="ظرفیت کودک")

    extra_person_price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="قیمت هر نفر اضافه (تومان)")
    child_price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="قیمت هر کودک (تومان)")
    amenities = models.ManyToManyField(Amenity, blank=True, related_name="room_types", verbose_name="امکانات اختصاصی اتاق")

    class Meta:
        verbose_name = "نوع اتاق"
        verbose_name_plural = "انواع اتاق"
        unique_together = ('hotel', 'name') # جلوگیری از تعریف اتاق هم‌نام در یک هتل

    def __str__(self):
        return f"{self.name} - {self.hotel.name}"

class BoardType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام سرویس")
    code = models.CharField(max_length=10, unique=True, verbose_name="کد اختصاری (مثلا: BB, FB)")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    class Meta:
        verbose_name = "نوع سرویس"
        verbose_name_plural = "انواع سرویس"

    def __str__(self):
        return self.name