# reservations/serializers.py

from rest_framework import serializers
from .models import Guest, Booking

class GuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        # فیلدهایی که از ورودی دریافت می‌کنیم
        fields = ['first_name', 'last_name', 'is_foreign', 'national_id', 'passport_number', 'phone_number', 'nationality']


class CreateBookingSerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    check_in = serializers.CharField()
    check_out = serializers.CharField()
    adults = serializers.IntegerField(min_value=1)
    children = serializers.IntegerField(min_value=0, default=0)
    # یک لیست تو در تو از میهمانان
    guests = GuestSerializer(many=True)

    def validate(self, data):
        # اعتبارسنجی اینکه تعداد میهمانان با تعداد بزرگسالان و کودکان مطابقت دارد
        if len(data['guests']) != (data['adults'] + data['children']):
            raise serializers.ValidationError("تعداد میهمانان باید با مجموع تعداد بزرگسالان و کودکان برابر باشد.")
        return data
# reservations/serializers.py

# ... (import های قبلی) ...

class BookingListSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source='room_type.hotel.name', read_only=True)
    room_name = serializers.CharField(source='room_type.name', read_only=True)

    class Meta:
        model = Booking
        fields = ['booking_code', 'hotel_name', 'room_name', 'check_in', 'check_out', 'total_price', 'status']