# In services/models.py

from django.db import models
from hotels.models import Hotel
from reservations.models import Booking

class ServiceType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نوع سرویس")
    # Determines if this service type requires extra input from the user (e.g., flight number)
    requires_details = models.BooleanField(default=False, verbose_name="نیازمند اطلاعات اضافی؟")

    def __str__(self):
        return self.name

class HotelService(models.Model):
    class PricingModel(models.TextChoices):
        PER_PERSON = 'PERSON', 'به ازای هر نفر'
        PER_BOOKING = 'BOOKING', 'به ازای هر رزرو'
        FREE = 'FREE', 'رایگان'

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='services', verbose_name="هتل")
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT, verbose_name="نوع سرویس")
    name = models.CharField(max_length=255, verbose_name="نام سرویس")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    pricing_model = models.CharField(max_length=10, choices=PricingModel.choices, verbose_name="مدل قیمت‌گذاری")
    price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="قیمت")

    def __str__(self):
        return f"{self.name} ({self.hotel.name})"

class BookedService(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_services', verbose_name="رزرو")
    hotel_service = models.ForeignKey(HotelService, on_delete=models.PROTECT, verbose_name="سرویس هتل")
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name="تعداد")
    total_price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="مبلغ نهایی سرویس")
    # JSONField to store dynamic data like flight number, arrival time, etc.
    details = models.JSONField(null=True, blank=True, verbose_name="جزئیات")

    def __str__(self):
        return f"سرویس {self.hotel_service.name} برای رزرو {self.booking.booking_code}"
