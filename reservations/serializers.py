# reservations/serializers.py v1
# Update: Added board_type_id to BookingRoomSerializer for price calculation.
from rest_framework import serializers
from .models import Guest, Booking, BookingRoom
from hotels.models import RoomType

class GuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = ['first_name', 'last_name', 'is_foreign', 'national_id', 'passport_number', 'phone_number', 'nationality']


class BookingRoomSerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    # --- START: Added board_type_id ---
    board_type_id = serializers.IntegerField()
    # --- END: Added board_type_id ---
    quantity = serializers.IntegerField(min_value=1)
    adults = serializers.IntegerField(min_value=0, default=0, help_text="Number of extra adults beyond base capacity")
    children = serializers.IntegerField(min_value=0, default=0)

# Renamed to be more specific for its purpose
class CreateBookingAPISerializer(serializers.Serializer):
    booking_rooms = BookingRoomSerializer(many=True, allow_empty=False)
    check_in = serializers.CharField()
    check_out = serializers.CharField()
    guests = GuestSerializer(many=True, allow_empty=False)
    payment_method = serializers.ChoiceField(choices=['online', 'credit', 'in_person'], default='online')
    agency_id = serializers.IntegerField(required=False, allow_null=True) # Optional for agency bookings

    def validate(self, data):
        """
        Validates that the number of guests matches the total capacity of all booked rooms.
        """
        total_capacity_count = 0
        for room_data in data['booking_rooms']:
            try:
                room_type = RoomType.objects.get(id=room_data['room_type_id'])
            except RoomType.DoesNotExist:
                raise serializers.ValidationError(f"اتاق با شناسه {room_data['room_type_id']} یافت نشد.")

            # Validate capacity for each room selection
            quantity = room_data.get('quantity', 1)
            extra_adults = room_data.get('adults', 0)
            children = room_data.get('children', 0)

            if extra_adults > (room_type.extra_capacity * quantity):
                raise serializers.ValidationError(f"تعداد نفرات اضافه برای اتاق '{room_type.name}' بیش از حد مجاز است.")
            
            if children > (room_type.child_capacity * quantity):
                raise serializers.ValidationError(f"تعداد کودکان برای اتاق '{room_type.name}' بیش از حد مجاز است.")

            # Calculate total capacity for this room selection
            total_capacity_count += (room_type.base_capacity * quantity) + extra_adults

        if len(data['guests']) != total_capacity_count:
             raise serializers.ValidationError(f"تعداد میهمانان ({len(data['guests'])}) باید با ظرفیت کل بزرگسالان رزرو شده ({total_capacity_count}) برابر باشد.")

        return data

# ... (بقیه سریالایزرها بدون تغییر باقی می‌مانند) ...

class BookingRoomQuoteSerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    board_type_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    extra_adults = serializers.IntegerField(min_value=0, default=0) 
    children_count = serializers.IntegerField(min_value=0, default=0)

class PriceQuoteMultiRoomInputSerializer(serializers.Serializer):
    booking_rooms = BookingRoomQuoteSerializer(many=True)
    check_in = serializers.CharField()
    check_out = serializers.CharField()
    user_id = serializers.IntegerField(required=False, allow_null=True) 


class BookingListSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source='booking_rooms.first.room_type.hotel.name', read_only=True)
    # To show a summary of rooms, we can use a SerializerMethodField if more detail is needed
    room_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = ['booking_code', 'hotel_name', 'room_summary', 'check_in', 'check_out', 'total_price', 'status']

    def get_room_summary(self, obj):
        first_room = obj.booking_rooms.first()
        if first_room:
            return f"{first_room.quantity} x {first_room.room_type.name}"
        return "N/A"
