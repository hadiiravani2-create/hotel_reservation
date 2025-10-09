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
        # total_price از فرم حذف شد.
        fields = ['user', 'check_in', 'check_out', 'status', 'agency']

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
