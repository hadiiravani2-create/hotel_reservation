# pricing/forms.py

from django import forms
from django_jalali.forms import jDateField
from .models import Availability, Price
from hotels.models import Hotel, RoomType
from jalali_date.widgets import AdminJalaliDateWidget

class AvailabilityRangeForm(forms.ModelForm):
    hotel = forms.ModelChoiceField(queryset=Hotel.objects.all(), label="هتل", required=True)
    start_date = jDateField(label="تاریخ شروع", widget=AdminJalaliDateWidget)
    end_date = jDateField(label="تاریخ پایان", widget=AdminJalaliDateWidget)

    class Meta:
        model = Availability
        fields = ['hotel', 'room_type', 'start_date', 'end_date', 'quantity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # اگر فرم با داده‌های ورودی پر شده باشد (یعنی در زمان ثبت یا خطا)
        if self.data and 'hotel' in self.data:
            try:
                hotel_id = int(self.data.get('hotel'))
                # کوئری‌ست را بر اساس هتل انتخاب شده، مجدداً تنظیم می‌کنیم
                self.fields['room_type'].queryset = RoomType.objects.filter(hotel_id=hotel_id).order_by('name')
            except (ValueError, TypeError):
                # اگر هتل معتبر نباشد، لیست را خالی نگه می‌داریم
                self.fields['room_type'].queryset = RoomType.objects.none()
        # اگر فرم برای ویرایش یک نمونه موجود باز شده باشد
        elif self.instance.pk and self.instance.room_type:
            self.fields['hotel'].initial = self.instance.room_type.hotel
            self.fields['room_type'].queryset = self.instance.room_type.hotel.room_types.order_by('name')
        else:
            # در حالت اولیه (فرم خالی)، لیست اتاق‌ها خالی است
            self.fields['room_type'].queryset = RoomType.objects.none()


class PriceRangeForm(forms.ModelForm):
    hotel = forms.ModelChoiceField(queryset=Hotel.objects.all(), label="هتل", required=True)
    start_date = jDateField(label="تاریخ شروع", widget=AdminJalaliDateWidget)
    end_date = jDateField(label="تاریخ پایان", widget=AdminJalaliDateWidget)

    class Meta:
        model = Price
        fields = [
            'hotel', 'room_type', 'start_date', 'end_date',
            'price_per_night', 'extra_person_price', 'child_price'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # این منطق را برای هر دو فرم اعمال می‌کنیم
        if self.data and 'hotel' in self.data:
            try:
                hotel_id = int(self.data.get('hotel'))
                self.fields['room_type'].queryset = RoomType.objects.filter(hotel_id=hotel_id).order_by('name')
            except (ValueError, TypeError):
                self.fields['room_type'].queryset = RoomType.objects.none()
        elif self.instance.pk and self.instance.room_type:
            self.fields['hotel'].initial = self.instance.room_type.hotel
            self.fields['room_type'].queryset = self.instance.room_type.hotel.room_types.order_by('name')
        else:
            self.fields['room_type'].queryset = RoomType.objects.none()