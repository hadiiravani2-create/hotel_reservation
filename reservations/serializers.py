# reservations/serializers.py
# version: 1.1.7
# CRITICAL FIX: Removed 'payment_method' from BookingDetailSerializer.Meta.fields as it does not exist on the Booking model.
#               Ensured all previous fixes for optional guests and detail serializers are present.

from rest_framework import serializers
from .models import Guest, Booking, BookingRoom
from hotels.models import RoomType
# Note: Assuming hotels.serializers is importable if needed for BoardTypeSerializer
# from hotels.serializers import BoardTypeSerializer 


# --- Detail Serializers for Read Operations ---

class GuestDetailSerializer(serializers.ModelSerializer):
    """Serializer for displaying full guest details (Read-Only)."""
    class Meta:
        model = Guest
        fields = [
            'first_name', 'last_name', 'is_foreign', 'national_id', 
            'passport_number', 'phone_number', 'nationality', 'city_of_origin'
        ]

class BookingRoomDetailSerializer(serializers.ModelSerializer):
    """Serializer for displaying details of a booked room."""
    room_type_name = serializers.CharField(source='room_type.name', read_only=True)
    board_type = serializers.CharField(source='board_type.name', read_only=True) # Name of board type
    hotel_name = serializers.CharField(source='room_type.hotel.name', read_only=True)
    
    class Meta:
        model = BookingRoom
        fields = [
            'id', 'room_type_name', 'board_type', 'hotel_name', 'quantity', 
            'adults', 'children', 'extra_requests'
        ]

class BookingDetailSerializer(serializers.ModelSerializer):
    """Master serializer for displaying full booking summary on the payment page."""
    hotel_name = serializers.CharField(source='booking_rooms.first.room_type.hotel.name', read_only=True)
    total_guests = serializers.SerializerMethodField()
    booking_rooms = BookingRoomDetailSerializer(many=True, read_only=True)
    guests = GuestDetailSerializer(many=True, read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'booking_code', 'hotel_name', 'check_in', 'check_out', 'total_price', 
            'status', 'created_at', 'updated_at', 'total_guests',
            'booking_rooms', 'guests', # CRITICAL FIX: Removed 'payment_method' 
        ]
        read_only_fields = fields 

    def get_total_guests(self, obj):
        # Calculate total number of actual guests recorded
        return obj.guests.count()


# --- Write/Input Serializers ---

class GuestSerializer(serializers.ModelSerializer):
    # Overriding ModelSerializer default behavior for optional fields:
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True) 
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)  
    
    # Explicitly setting allow_null=True for CharFields that are null=True on the model
    national_id = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    passport_number = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(max_length=11, required=False, allow_blank=True, allow_null=True)
    nationality = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    city_of_origin = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    
    # NEW: Optional field for guest booking, indicating intent to register later.
    wants_to_register = serializers.BooleanField(required=False, write_only=True, default=False)
    
    class Meta:
        model = Guest
        # All fields are included, but optionality is controlled by explicit definitions above
        fields = ['first_name', 'last_name', 'is_foreign', 'national_id', 'passport_number', 'phone_number', 'nationality', 'city_of_origin', 'wants_to_register']

    def validate(self, data):
        """
        Custom validation for a single guest. Now relies on the parent CreateBookingAPISerializer 
        to enforce mandatory fields for the principal guest only.
        """
        national_id = data.get('national_id')
        
        # Clean up conflicting ID fields based on the 'is_foreign' flag.
        if data.get('is_foreign', False):
             # Ensure national_id is None for foreign guests if supplied
             if national_id:
                 data['national_id'] = None
        else:
             # Ensure passport info is None for domestic guests if supplied
             if data.get('passport_number') or data.get('nationality'):
                 data['passport_number'] = None
                 data['nationality'] = None
            
        return data


class BookingRoomSerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    board_type_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    adults = serializers.IntegerField(min_value=0, default=0, help_text="Number of extra adults beyond base capacity")
    children = serializers.IntegerField(min_value=0, default=0)
    # New field for extra guest requests
    extra_requests = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class CreateBookingAPISerializer(serializers.Serializer):
    BOOKING_PAYMENT_CHOICES = [
        ('online', 'آنلاین'),
        ('credit', 'اعتباری'),
        ('in_person', 'حضوری'),
        ('card_to_card', 'کارت به کارت'), # Added new payment method
    ]

    booking_rooms = BookingRoomSerializer(many=True, allow_empty=False)
    check_in = serializers.CharField()
    check_out = serializers.CharField()
    guests = GuestSerializer(many=True, allow_empty=False)
    # payment_method is removed from the payload for the two-step flow. We keep it here
    # temporarily but it must be ignored by the view (which is currently the case).
    payment_method = serializers.ChoiceField(choices=BOOKING_PAYMENT_CHOICES, default='online') 
    agency_id = serializers.IntegerField(required=False, allow_null=True) # Optional for agency bookings
    
    # New field for mandatory acceptance of rules
    rules_accepted = serializers.BooleanField(required=True, write_only=True)

    def validate_rules_accepted(self, value):
        if not value:
            raise serializers.ValidationError("پذیرش قوانین و شرایط رزرو الزامی است.")
        return value

    def validate(self, data):
        """
        Validates capacity and ensures the first guest (principal) has all required data.
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

            # Calculate total capacity for this room selection (Base + Extra Adults)
            total_adult_capacity = (room_type.base_capacity * quantity) + extra_adults
            total_capacity_count += total_adult_capacity

        # Rule 1: Validate total guests count (Adults + Children) - MUST BE KEPT
        total_expected_guests = total_capacity_count + sum(r.get('children', 0) * r.get('quantity', 1) for r in data['booking_rooms'])

        if len(data['guests']) != total_expected_guests:
             raise serializers.ValidationError(f"تعداد میهمانان ({len(data['guests'])}) باید با ظرفیت کل رزرو شده ({total_expected_guests}) برابر باشد.")

        # Rule 2: Validate principal guest (First guest) - ALL FIELDS ARE MANDATORY FOR THIS GUEST
        if not data['guests']:
             raise serializers.ValidationError("حداقل یک میهمان (رزرو کننده) باید وجود داشته باشد.")

        principal_guest_data = data['guests'][0]

        # Name, Last Name and Phone are always mandatory for principal guest
        if not principal_guest_data.get('first_name') or not principal_guest_data.get('last_name') or not principal_guest_data.get('phone_number'):
            raise serializers.ValidationError({"guests": ["اطلاعات نام، نام خانوادگی و شماره تماس رزرو کننده (نفر اول) الزامی است."]})

        # National ID/Passport rule for principal guest
        is_foreign = principal_guest_data.get('is_foreign', False)
        if is_foreign and (not principal_guest_data.get('passport_number') or not principal_guest_data.get('nationality')):
            raise serializers.ValidationError({"guests": ["برای رزرو کننده خارجی، شماره پاسپورت و تابعیت الزامی است."]})
        elif not is_foreign and not principal_guest_data.get('national_id'):
            # National ID is mandatory for domestic principal guest
            raise serializers.ValidationError({"guests": ["کد ملی رزرو کننده (نفر اول) برای میهمانان ایرانی الزامی است."]})
        
        # Rule 3: Validation for secondary guests (REMOVED) - Only Rule 1 & 2 are enforced.

        return data


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
