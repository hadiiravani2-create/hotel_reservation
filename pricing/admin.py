# pricing/admin.py
# version 2
# Feature: Added search and autocomplete fields for better user experience.

from django.contrib import admin
from .models import Availability , Price
from .forms import AvailabilityRangeForm , PriceRangeForm
from datetime import timedelta
from django.urls import reverse
from django.utils.html import format_html

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    form = AvailabilityRangeForm
    list_display = ('get_hotel_name', 'room_type', 'date', 'quantity')
    list_filter = ('room_type__hotel', 'date')
    search_fields = ('room_type__name', 'room_type__hotel__name')
    autocomplete_fields = ('room_type',)

    @admin.display(description='هتل', ordering='room_type__hotel')
    def get_hotel_name(self, obj):
        return obj.room_type.hotel.name

    class Media:
        # فایل جاوا اسکریپت سفارشی را به صفحه ادمین اضافه می‌کنیم
        js = ("admin/js/availability_form.js",)

    def save_model(self, request, obj, form, change):
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        room_type = form.cleaned_data['room_type']
        quantity = form.cleaned_data['quantity']

        current_date = start_date
        while current_date <= end_date:
            Availability.objects.update_or_create(
                room_type=room_type,
                date=current_date,
                defaults={'quantity': quantity}
            )
            current_date += timedelta(days=1)

@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    form = PriceRangeForm
    list_display = ('get_hotel_name', 'room_type', 'board_type', 'date', 'price_per_night', 'extra_person_price', 'child_price')
    list_filter = ('room_type__hotel', 'date', 'board_type')
    search_fields = ('room_type__name', 'room_type__hotel__name')
    autocomplete_fields = ('room_type', 'board_type')

    @admin.display(description='هتل', ordering='room_type__hotel')
    def get_hotel_name(self, obj):
        return obj.room_type.hotel.name

    class Media:
        js = ("admin/js/availability_form.js",)

    def save_model(self, request, obj, form, change):
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        room_type = form.cleaned_data['room_type']
        
        price_per_night = form.cleaned_data['price_per_night']
        extra_person_price = form.cleaned_data['extra_person_price']
        child_price = form.cleaned_data['child_price']
        board_type = form.cleaned_data['board_type'] 
        current_date = start_date
        while current_date <= end_date:
            Price.objects.update_or_create(
                room_type=room_type,
                date=current_date,
                board_type=board_type,
                defaults={
                    'price_per_night': price_per_night,
                    'extra_person_price': extra_person_price,
                    'child_price': child_price,
                }
            )
            current_date += timedelta(days=1)
