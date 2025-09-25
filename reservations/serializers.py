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
    # اضافه شدن فیلدهای نفرات در سطح اتاق
    adults = serializers.IntegerField(min_value=0, default=0)
    children = serializers.IntegerField(min_value=0, default=0)

# این سریالایزر دیگر استفاده نخواهد شد زیرا منطق تعداد نفرات عوض شده است
class CreateBookingSerializer(serializers.Serializer):
    # به جای فیلدهای مجزا برای اتاق، از یک لیست از BookingRoom استفاده می‌کنیم
    booking_rooms = BookingRoomSerializer(many=True)
    check_in = serializers.CharField()
    check_out = serializers.CharField()
    # adults و children کلی حذف شدند
    guests = GuestSerializer(many=True)
    # فیلد جدید برای تعیین نوع پرداخت
    payment_method = serializers.ChoiceField(choices=['online', 'credit', 'in_person'], default='online')

    def validate(self, data):
        # بررسی تعداد میهمانان (این منطق باید به save_formset در ادمین و CreateBookingAPIView در API منتقل شود)
        
        # محاسبه تعداد کل نفرات از BookingRooms
        total_guests_count = 0
        for room_data in data['booking_rooms']:
            try:
                room_type = RoomType.objects.get(id=room_data['room_type_id'])
            except RoomType.DoesNotExist:
                raise serializers.ValidationError(f"اتاق با شناسه {room_data['room_type_id']} یافت نشد.")
                
            # ظرفیت پایه * تعداد اتاق + نفرات اضافی + کودکان
            total_guests_count += (room_type.base_capacity * room_data['quantity'])
            total_guests_count += room_data['adults'] # نفرات اضافی
            total_guests_count += room_data['children']

        if len(data['guests']) != total_guests_count:
             raise serializers.ValidationError(f"تعداد میهمانان ({len(data['guests'])}) باید با ظرفیت کل رزرو ({total_guests_count}) برابر باشد.")

        return data

# سریالایزرهای API محاسبه قیمت

class BookingRoomQuoteSerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    board_type_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    # فیلدهای نفرات اضافی و کودک در سطح اتاق
    extra_adults = serializers.IntegerField(min_value=0, default=0) 
    children_count = serializers.IntegerField(min_value=0, default=0)

class PriceQuoteMultiRoomInputSerializer(serializers.Serializer):
    booking_rooms = BookingRoomQuoteSerializer(many=True)
    check_in = serializers.CharField()
    check_out = serializers.CharField()
    # adults و children کلی حذف شدند
    user_id = serializers.IntegerField(required=False, allow_null=True) 


class BookingListSerializer(serializers.ModelSerializer):
    # برای رزرو گروهی، نیاز به نمایش جزئیات اتاق‌ها داریم
    hotel_name = serializers.CharField(source='booking_rooms.first.room_type.hotel.name', read_only=True)
    room_name = serializers.CharField(source='booking_rooms.first.room_type.name', read_only=True)
    
    class Meta:
        model = Booking
        # حذف adults و children از لیست فیلدها
        fields = ['booking_code', 'hotel_name', 'room_name', 'check_in', 'check_out', 'total_price', 'status']
