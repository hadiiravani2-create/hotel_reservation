# reservations/forms.py
from django import forms
from django_jalali.forms import jDateField
from .models import Booking
from jalali_date.widgets import AdminJalaliDateWidget
from django.core.exceptions import ValidationError

class BookingForm(forms.ModelForm):
    check_in = jDateField(label="تاریخ ورود", widget=AdminJalaliDateWidget)
    check_out = jDateField(label="تاریخ خروج", widget=AdminJalaliDateWidget)

    class Meta:
        model = Booking
        fields = '__all__'

# reservations/forms.py
def clean(self):
    cleaned_data = super().clean()
    room_type = cleaned_data.get("room_type")
    adults = cleaned_data.get("adults")
    children = cleaned_data.get("children")

    if room_type and adults is not None and children is not None:
        total_adult_capacity = room_type.base_capacity + room_type.extra_capacity
        if adults > total_adult_capacity:
            raise ValidationError(f"تعداد بزرگسالان نمی‌تواند بیشتر از ظرفیت کل ({total_adult_capacity} نفر) باشد.")
        if children > room_type.child_capacity:
             raise ValidationError(f"تعداد کودکان نمی‌تواند بیشتر از ظرفیت کودک اتاق ({room_type.child_capacity} نفر) باشد.")

    return cleaned_data
