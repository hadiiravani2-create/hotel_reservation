# reservations/serializers.py

from rest_framework import serializers
from .models import Guest, Booking, BookingRoom
from hotels.models import RoomType

class GuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        # فیلدهایی که از ورودی دریافت می‌کنیم
        fields = ['first_name', 'last_name', 'is_foreign', 'national_id', 'passport_number', 'phone_number', 'nationality']


class BookingRoomSerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class CreateBookingSerializer(serializers.Serializer):
    # به جای فیلدهای مجزا برای اتاق، از یک لیست از BookingRoom استفاده می‌کنیم
    booking_rooms = BookingRoomSerializer(many=True)
    check_in = serializers.CharField()
    check_out = serializers.CharField()
    adults = serializers.IntegerField(min_value=1)
    children = serializers.IntegerField(min_value=0, default=0)
    guests = GuestSerializer(many=True)
    # فیلد جدید برای تعیین نوع پرداخت
    payment_method = serializers.ChoiceField(choices=['online', 'credit', 'in_person'], default='online')

    def validate(self, data):
        # بررسی تعداد میهمانان
        if len(data['guests']) != (data['adults'] + data['children']):
            raise serializers.ValidationError("تعداد میهمانان باید با مجموع تعداد بزرگسالان و کودکان برابر باشد.")

        # بررسی ظرفیت اتاق‌ها در رزرو گروهی
        for room in data['booking_rooms']:
            try:
                room_type = RoomType.objects.get(id=room['room_type_id'])
                # این منطق باید با دقت بیشتری در view انجام شود
                # فعلاً فقط وجود اتاق را بررسی می‌کنیم.
            except RoomType.DoesNotExist:
                raise serializers.ValidationError(f"اتاق با شناسه {room['room_type_id']} یافت نشد.")

        return data


class BookingListSerializer(serializers.ModelSerializer):
    # برای رزرو گروهی، نیاز به نمایش جزئیات اتاق‌ها داریم
    hotel_name = serializers.CharField(source='booking_rooms.first.room_type.hotel.name', read_only=True)
    room_name = serializers.CharField(source='booking_rooms.first.room_type.name', read_only=True)
    
    class Meta:
        model = Booking
        fields = ['booking_code', 'hotel_name', 'room_name', 'check_in', 'check_out', 'total_price', 'status']
