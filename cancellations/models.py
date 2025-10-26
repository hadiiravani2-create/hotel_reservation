# cancellations/models.py
# version: 1.0.0
# FEATURE: Initial models for the Cancellation Penalty Engine.

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class CancellationPolicy(models.Model):
    """
    Defines a named cancellation policy template.
    E.g., "Strict Policy", "Flexible Policy".
    This policy is then linked to a Hotel.
    """
    name = models.CharField(max_length=255, unique=True, verbose_name="نام سیاست")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات (اختیاری)")

    class Meta:
        verbose_name = "سیاست لغو"
        verbose_name_plural = "۱. سیاست‌های لغو" # Numbered for admin sorting

    def __str__(self):
        return self.name

class CancellationRule(models.Model):
    """
    Defines a specific rule within a CancellationPolicy.
    This is the core of the penalty engine.
    """
    
    # Define penalty types
    PENALTY_TYPE_CHOICES = (
        ('PERCENT_TOTAL', 'درصد از کل مبلغ رزرو'),
        ('PERCENT_FIRST_NIGHT', 'درصد از هزینه شب اول'),
        ('FIXED_NIGHTS', 'تعداد ثابت شب اقامت'),
    )

    policy = models.ForeignKey(
        CancellationPolicy, 
        on_delete=models.CASCADE, 
        related_name="rules", 
        verbose_name="سیاست مرتبط"
    )
    
    # The window in days before check-in when this rule applies
    days_before_checkin_min = models.PositiveIntegerField(
        verbose_name="حداقل روز (شروع بازه)", 
        help_text="شروع بازه زمانی. مثال: 7 (برای 7 تا 14 روز قبل از ورود)"
    )
    days_before_checkin_max = models.PositiveIntegerField(
        verbose_name="حداکثر روز (پایان بازه)", 
        help_text="پایان بازه زمانی. مثال: 14 (برای 7 تا 14 روز قبل از ورود). برای یک روز خاص، هر دو را یکسان بگذارید."
    )
    
    # Define the penalty
    penalty_type = models.CharField(
        max_length=30, 
        choices=PENALTY_TYPE_CHOICES, 
        verbose_name="نوع جریمه"
    )
    penalty_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="مقدار جریمه",
        help_text="اگر نوع 'درصد' است، عددی بین 0 تا 100 (مثال: 70.0). اگر 'تعداد شب' است، (مثال: 1.0)."
    )

    class Meta:
        verbose_name = "قانون لغو"
        verbose_name_plural = "۲. قوانین لغو (جزئیات)" # Numbered for admin sorting
        ordering = ['policy', 'days_before_checkin_min']
        # Ensure rules don't overlap for the same policy
        unique_together = ('policy', 'days_before_checkin_min', 'days_before_checkin_max')

    def __str__(self):
        return f"قانون {self.policy.name}: {self.days_before_checkin_min}-{self.days_before_checkin_max} روز مانده"
