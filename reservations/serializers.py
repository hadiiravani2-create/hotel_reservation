# reservations/serializers.py
# version: 1.2.2
# Feature: Added GuestBookingLookupSerializer for unauthenticated booking tracking by code and national ID.
# FIX: Ensured case-insensitive comparison (using .upper()) for national_id and passport_number 
#      to prevent lookup failures due to case mismatches in the database or user input.

from rest_framework import serializers
from .models import Guest, Booking, BookingRoom, OfflineBank, PaymentConfirmation # Added new models
from hotels.models import RoomType


# --- Detail Serializers for Read Operations (Kept) ---

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
            'booking_rooms', 'guests', 
        ]
        read_only_fields = fields 

    def get_total_guests(self, obj):
        return obj.guests.count()


# --- NEW Booking Lookup Serializer for Guests ---

class GuestBookingLookupSerializer(serializers.Serializer):
    """Serializer for validating booking lookup data (code + ID)."""
    booking_code = serializers.CharField(required=True, max_length=8)
    # national_id is used for Iranian guests, passport_number for foreign guests
    national_id = serializers.CharField(required=False, allow_blank=True, max_length=10) 
    passport_number = serializers.CharField(required=False, allow_blank=True, max_length=50)

    def validate(self, data):
        booking_code = data.get('booking_code')
        
        # FIX: Normalize inputs to stripped, uppercase strings for robust comparison
        input_national_id = (data.get('national_id') or '').strip().upper()
        input_passport_number = (data.get('passport_number') or '').strip().upper()

        if not input_national_id and not input_passport_number:
            raise serializers.ValidationError("وارد کردن کد ملی یا شماره پاسپورت الزامی است.")

        try:
            # 1. Find the booking
            booking = Booking.objects.get(booking_code=booking_code)
        except Booking.DoesNotExist:
            raise serializers.ValidationError({"booking_code": "کد رزرو وارد شده نامعتبر است."})
        
        # 2. Check the principal guest (first guest in the reservation)
        principal_guest = booking.guests.order_by('id').first()
        if not principal_guest:
            raise serializers.ValidationError("رزرو یافت شده فاقد میهمان اصلی است. با پشتیبانی تماس بگیرید.")
        
        # 3. Validation based on guest type
        is_foreign_lookup = bool(input_passport_number)

        if is_foreign_lookup and principal_guest.is_foreign:
             # Foreign Guest Check: Compare stripped and upper-cased input with DB value
             db_passport = (principal_guest.passport_number or '').strip().upper()
             
             if db_passport != input_passport_number:
                 raise serializers.ValidationError({"passport_number": "شماره پاسپورت وارد شده با میهمان اصلی مطابقت ندارد."})
        
        elif not is_foreign_lookup and not principal_guest.is_foreign:
            # Domestic Guest Check: Compare stripped and upper-cased input with DB value
            db_national_id = (principal_guest.national_id or '').strip().upper()
            
            if db_national_id != input_national_id:
                 raise serializers.ValidationError({"national_id": "کد ملی وارد شده با میهمان اصلی مطابقت ندارد."})
        
        else:
             # Mismatch between lookup type and actual guest type
             raise serializers.ValidationError("نوع مدرک شناسایی (کد ملی/پاسپورت) با نوع میهمان اصلی رزرو شده مطابقت ندارد.")
             
        data['booking'] = booking
        return data


# --- NEW Offline Payment Serializers ---

class OfflineBankSerializer(serializers.ModelSerializer):
    """Serializer for listing active bank accounts for user reference."""
    class Meta:
        model = OfflineBank
        fields = ['id', 'bank_name', 'account_holder', 'account_number', 'card_number']


class PaymentConfirmationSerializer(serializers.ModelSerializer):
    """Serializer for submitting payment confirmation details by the user."""
    booking_code = serializers.CharField(write_only=True, required=True, max_length=8)
    
    class Meta:
        model = PaymentConfirmation
        fields = [
            'booking_code', 'offline_bank', 'tracking_code', 
            'payment_date', 'payment_amount'
        ]
        extra_kwargs = {
            'offline_bank': {'error_messages': {'does_not_exist': 'حساب بانکی مورد نظر یافت نشد یا فعال نیست.'}},
            'payment_date': {'input_formats': ['%Y-%m-%d %H:%M:%S']} # Specify format for API input
        }

    def validate(self, data):
        """Custom validation to ensure the booking exists and is pending."""
        booking_code = data['booking_code']
        try:
            booking = Booking.objects.get(booking_code=booking_code, status='pending')
        except Booking.DoesNotExist:
            raise serializers.ValidationError({"booking_code": "رزرو با این کد یافت نشد یا در وضعیت در انتظار پرداخت نیست."})
        
        # Check if confirmation already exists (OneToOne field check)
        if PaymentConfirmation.objects.filter(booking=booking).exists():
             raise serializers.ValidationError({"booking_code": "اطلاعات پرداخت برای این رزرو قبلاً ثبت شده است."})
        
        data['booking'] = booking
        return data

    def create(self, validated_data):
        """Create PaymentConfirmation instance and link it to the Booking."""
        booking = validated_data.pop('booking')
        validated_data.pop('booking_code') # Remove unnecessary write-only field
        
        return PaymentConfirmation.objects.create(booking=booking, **validated_data)


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
