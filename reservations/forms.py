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
        # فیلد room_type حذف شده و به جای آن از booking_rooms استفاده می‌کنیم
        fields = ['user', 'check_in', 'check_out', 'adults', 'children', 'total_price', 'status', 'agency']

    def clean(self):
        cleaned_data = super().clean()
        adults = cleaned_data.get("adults")
        children = cleaned_data.get("children")
        
        # این بخش از اعتبارسنجی فرم، به دلیل حذف فیلد room_type باید تغییر کند.
        # اعتبارسنجی ظرفیت اتاق‌ها باید به جای اینجا، در منطق رزرو گروهی در views انجام شود.
        
        # if room_type and adults is not None and children is not None:
        #    total_adult_capacity = room_type.base_capacity + room_type.extra_capacity
        #    if adults > total_adult_capacity:
        #        raise ValidationError(f"تعداد بزرگسالان نمی‌تواند بیشتر از ظرفیت کل ({total_adult_capacity} نفر) باشد.")
        #    if children > room_type.child_capacity:
        #         raise ValidationError(f"تعداد کودکان نمی‌تواند بیشتر از ظرفیت کودک اتاق ({room_type.child_capacity} نفر) باشد.")

        return cleaned_data
