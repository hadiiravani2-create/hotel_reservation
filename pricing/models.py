# pricing/models.py


from django.db import models
from django_jalali.db import models as jmodels
from hotels.models import RoomType, BoardType # BoardType را اضافه می‌کنیم


class Availability(models.Model):
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name="availabilities", verbose_name="نوع اتاق")
    date = jmodels.jDateField(verbose_name="تاریخ")
    quantity = models.PositiveSmallIntegerField(default=0, verbose_name="تعداد موجود")

    class Meta:
        verbose_name = "موجودی روزانه"
        verbose_name_plural = "موجودی‌های روزانه"
        unique_together = ('room_type', 'date')
        ordering = ['date']

    def __str__(self):
        return f"موجودی {self.room_type} در تاریخ {self.date}: {self.quantity} اتاق"
        

class Price(models.Model):
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name="prices", verbose_name="نوع اتاق")
    # فیلد جدید برای ارتباط با نوع سرویس
    board_type = models.ForeignKey(BoardType, on_delete=models.CASCADE, related_name="prices", verbose_name="نوع سرویس")
    date = jmodels.jDateField(verbose_name="تاریخ")

    price_per_night = models.DecimalField(max_digits=20, decimal_places=0, verbose_name="قیمت پایه آن شب (تومان)")
    extra_person_price = models.DecimalField(max_digits=20, decimal_places=0, verbose_name="قیمت نفر اضافه (تومان)")
    child_price = models.DecimalField(max_digits=20, decimal_places=0, verbose_name="قیمت کودک (تومان)")

    class Meta:
        verbose_name = "قیمت روزانه"
        verbose_name_plural = "قیمت‌های روزانه"
        # یکتایی قیمت بر اساس هر سه فیلد خواهد بود
        unique_together = ('room_type', 'date', 'board_type')
        ordering = ['date']

    def __str__(self):
         return f"قیمت {self.room_type} ({self.board_type}) در تاریخ {self.date}"
