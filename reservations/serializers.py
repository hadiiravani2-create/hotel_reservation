# reservations/serializers.py
# version: 1.1.1
# Feature: Added optional 'wants_to_register' field to GuestSerializer for future user registration support.

from rest_framework import serializers
from .models import Guest, Booking, BookingRoom
from hotels.models import RoomType

class GuestSerializer(serializers.ModelSerializer):
    # Added city_of_origin
    city_of_origin = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    # NEW: Optional field for guest booking, indicating intent to register later.
    wants_to_register = serializers.BooleanField(required=False, write_only=True, default=False)
    
    class Meta:
        model = Guest
        # Added wants_to_register to fields for input payload
        fields = ['first_name', 'last_name', 'is_foreign', 'national_id', 'passport_number', 'phone_number', 'nationality', 'city_of_origin', 'wants_to_register']

    def validate(self, data):
        """
        Custom validation for a single guest based on the first guest's role (main guest)
        and whether they are foreign or domestic.
        """
        is_foreign = data.get('is_foreign', False)
        national_id = data.get('national_id')
        passport_number = data.get('passport_number')
        nationality = data.get('nationality')
        
        # Check compulsory fields for all guests
        if not data.get('first_name') or not data.get('last_name'):
            raise serializers.ValidationError("نام و نام خانوادگی میهمان الزامی است.")
            
        # Check fields based on is_foreign flag
        if is_foreign:
            # If foreign, passport number and nationality are required
            if not passport_number or not nationality:
                raise serializers.ValidationError("برای میهمانان خارجی، شماره پاسپورت و تابعیت الزامی است.")
            if national_id: # National ID must be empty or None
                data['national_id'] = None 
        else:
            # If domestic (or no flag set), national ID is required (will be checked in validate_iranian_national_id)
            # We rely on the model's validator for the format, but ensure one of the IDs is present in case of first guest validation.
            # Here, we only check for the first (principal) guest being complete. For others, we relax the check.
            pass
            
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

        # Rule 1: Validate total adult guests count (excluding children)
        # Assuming that 'adults' in the list of guests only includes adults (base capacity + extra adults)
        # And the children count is separate. The current FE sends ALL guests including children.
        # Based on the FE logic, total guests *should* be adults + extra adults + children.
        # Reverting to old logic to prevent mismatch, assuming FE guests array includes children data fields.
        
        # NOTE: The previous logic assumed the FE Guest array included guests corresponding to children too, 
        # which is incorrect for hotel reservations typically. However, based on the previous FE:
        # total_capacity_count += total_capacity_count (includes base capacity adults + extra adults)
        # The FE's previous logic: `totalGuestsCount = sum (room.base_capacity + room.adults + room.children)`
        # The Guest list should match this count.
        
        total_expected_guests = total_capacity_count + sum(r.get('children', 0) * r.get('quantity', 1) for r in data['booking_rooms'])

        if len(data['guests']) != total_expected_guests:
             raise serializers.ValidationError(f"تعداد میهمانان ({len(data['guests'])}) باید با ظرفیت کل رزرو شده ({total_expected_guests}) برابر باشد.")

        # Rule 2: Validate principal guest (First guest)
        if not data['guests']:
             raise serializers.ValidationError("حداقل یک میهمان (رزرو کننده) باید وجود داشته باشد.")

        principal_guest_data = data['guests'][0]

        # Name and Phone are always mandatory for principal guest
        if not principal_guest_data.get('first_name') or not principal_guest_data.get('last_name') or not principal_guest_data.get('phone_number'):
            raise serializers.ValidationError({"guests": ["اطلاعات نام، نام خانوادگی و شماره تماس رزرو کننده (نفر اول) الزامی است."]})

        # National ID/Passport rule for principal guest
        is_foreign = principal_guest_data.get('is_foreign', False)
        if is_foreign and (not principal_guest_data.get('passport_number') or not principal_guest_data.get('nationality')):
            raise serializers.ValidationError({"guests": ["برای رزرو کننده خارجی، شماره پاسپورت و تابعیت الزامی است."]})
        elif not is_foreign and not principal_guest_data.get('national_id'):
            # National ID is mandatory for domestic principal guest
            raise serializers.ValidationError({"guests": ["کد ملی رزرو کننده (نفر اول) برای میهمانان ایرانی الزامی است."]})
        
        # Rule 3: Validation for secondary guests (only name/last name are strictly mandatory at minimum)
        for i, guest_data in enumerate(data['guests'][1:], start=1):
            if not guest_data.get('first_name') or not guest_data.get('last_name'):
                 raise serializers.ValidationError({"guests": [f"نام و نام خانوادگی میهمان شماره {i+1} الزامی است."]})

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
