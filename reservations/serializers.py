# reservations/serializers.py
# version: 1.2.5
# REFACTOR: Upgraded PaymentConfirmationSerializer to support GenericForeignKey,
#           allowing it to link to both Bookings and WalletTransactions.

from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from .models import Guest, Booking, BookingRoom, OfflineBank, PaymentConfirmation
from hotels.models import RoomType
from core.models import WalletTransaction # Import WalletTransaction
from services.serializers import HotelServiceSerializer

# ... (Other serializers remain unchanged) ...

class GuestDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = [
            'first_name', 'last_name', 'is_foreign', 'national_id', 
            'passport_number', 'phone_number', 'nationality', 'city_of_origin'
        ]


class BookingRoomDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for the rooms within a booking. This is a simple, static serializer.
    """
    room_type_name = serializers.CharField(source='room_type.name', read_only=True)
    board_type = serializers.CharField(source='board_type.name', read_only=True)
    hotel_name = serializers.CharField(source='room_type.hotel.name', read_only=True)

    class Meta:
        model = BookingRoom
        fields = [
            'id', 'room_type_name', 'board_type', 'hotel_name', 'quantity',
            'adults', 'children', 'extra_requests'
        ]

class GuestSerializer(serializers.ModelSerializer):
    """Serializer for GUEST INPUT during booking creation."""
    wants_to_register = serializers.BooleanField(required=False, write_only=True, default=False)
    class Meta:
        model = Guest
        # Note: 'wants_to_register' is not a model field, it's handled in the view.
        fields = ['first_name', 'last_name', 'is_foreign', 'national_id', 'passport_number', 'phone_number', 'nationality', 'city_of_origin', 'wants_to_register']

class BookingRoomSerializer(serializers.Serializer):
    """Serializer for ROOM INPUT during booking creation."""
    room_type_id = serializers.IntegerField()
    board_type_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    extra_adults = serializers.IntegerField(min_value=0, default=0)
    children_count = serializers.IntegerField(min_value=0, default=0)
    extra_requests = serializers.CharField(required=False, allow_blank=True, allow_null=True)
# ===================================================================
# SECTION 2: MAIN SERIALIZERS (MAY HAVE DYNAMIC LOGIC)
# These can now safely use the serializers from Section 1.
# ===================================================================

class BookingDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed booking information (read-only).
    Dynamically includes 'booked_services' if the services app is installed.
    """
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if apps.is_installed('services'):
            try:
                BookedServiceSerializer = __import__('services.serializers', fromlist=['BookedServiceSerializer']).BookedServiceSerializer
                self.fields['booked_services'] = BookedServiceSerializer(many=True, read_only=True)
            except (ImportError, AttributeError):
                pass

    def get_total_guests(self, obj):
        return obj.guests.count()

class GuestBookingLookupSerializer(serializers.Serializer):
    booking_code = serializers.CharField(required=True, max_length=8)
    national_id = serializers.CharField(required=False, allow_blank=True, max_length=10) 
    passport_number = serializers.CharField(required=False, allow_blank=True, max_length=50)
    def validate(self, data):
        # ... (validation logic remains unchanged)
        return data

class OfflineBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineBank
        fields = ['id', 'bank_name', 'account_holder', 'account_number', 'card_number']

class PaymentConfirmationSerializer(serializers.ModelSerializer):
    """
    Serializer for submitting offline payment details for different object types (e.g., Booking, WalletTransaction).
    """
    # Write-only fields for identifying the related object generically.
    content_type = serializers.ChoiceField(
        choices=[('booking', 'رزرو'), ('wallet_transaction', 'تراکنش کیف پول')],
        write_only=True,
        required=True
    )
    object_id = serializers.CharField(write_only=True, required=True, help_text="کد رزرو یا شناسه تراکنش")

    class Meta:
        model = PaymentConfirmation
        fields = [
            'content_type', 'object_id', 'offline_bank', 'tracking_code',
            'payment_date', 'payment_amount'
        ]

    def validate(self, data):
        content_type_str = data.pop('content_type')
        object_id_str = data.pop('object_id')
        content_object = None

        if content_type_str == 'booking':
            try:
                content_object = Booking.objects.get(booking_code=object_id_str, status='pending')
                data['content_type'] = ContentType.objects.get_for_model(Booking)
                data['object_id'] = content_object.pk
            except Booking.DoesNotExist:
                raise serializers.ValidationError("رزرو با این کد یافت نشد یا در وضعیت در انتظار پرداخت نیست.")
        
        elif content_type_str == 'wallet_transaction':
            try:
                # Assuming UUID for transaction_id
                content_object = WalletTransaction.objects.get(transaction_id=object_id_str, status='pending')
                data['content_type'] = ContentType.objects.get_for_model(WalletTransaction)
                data['object_id'] = content_object.pk
            except (WalletTransaction.DoesNotExist, ValueError):
                raise serializers.ValidationError("تراکنش شارژ کیف پول با این شناسه یافت نشد یا در وضعیت در انتظار نیست.")
        
        else:
            raise serializers.ValidationError("نوع موجودیت نامعتبر است.")

        # Check if a confirmation already exists for this object
        if PaymentConfirmation.objects.filter(content_type=data['content_type'], object_id=data['object_id']).exists():
            raise serializers.ValidationError("اطلاعات پرداخت برای این مورد قبلاً ثبت شده است.")
            
        return data

    def create(self, validated_data):
        # The 'content_type' and 'object_id' are already correctly set in validate()
        return PaymentConfirmation.objects.create(**validated_data)


class CreateBookingAPISerializer(serializers.Serializer):
    """
    Handles validation for the main booking creation payload.
    It dynamically includes fields for add-on services if the 'services'
    app is enabled, ensuring a pluggable architecture.
    """
    booking_rooms = BookingRoomSerializer(many=True, allow_empty=False)
    check_in = serializers.CharField(max_length=10)
    check_out = serializers.CharField(max_length=10)
    guests = GuestSerializer(many=True, allow_empty=False)
    agency_id = serializers.IntegerField(required=False, allow_null=True)
    rules_accepted = serializers.BooleanField(write_only=True)

    def __init__(self, *args, **kwargs):
        """
        Dynamically adds the 'selected_services' field to the serializer
        if the 'services' application is installed in Django settings.
        """
        super().__init__(*args, **kwargs)
        if apps.is_installed('services'):
            self.fields['selected_services'] = serializers.ListField(
                child=serializers.DictField(), 
                required=False, 
                write_only=True,
                help_text="A list of selected add-on services, e.g., [{'id': 1, 'quantity': 2, 'details': {...}}]"
            )

    def validate_rules_accepted(self, value):
        """
        Ensures the user has accepted the terms and conditions.
        """
        if not value:
            raise serializers.ValidationError("پذیرش قوانین و مقررات رزرو الزامی است.")
        return value

    def validate(self, data):
        """
        Cross-field validation. For example, ensuring check_out is after check_in.
        (This can be expanded with more business logic).
        """
        if data['check_in'] >= data['check_out']:
            raise serializers.ValidationError("تاریخ خروج باید بعد از تاریخ ورود باشد.")
        
        if not data['guests']:
            raise serializers.ValidationError("حداقل اطلاعات یک میهمان (سرپرست) الزامی است.")
            
        # You can add more complex validation logic here if needed.
        return data

class BookingRoomQuoteSerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    board_type_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    extra_adults = serializers.IntegerField(min_value=0, default=0) 
    children_count = serializers.IntegerField(min_value=0, default=0)
    extra_requests = serializers.CharField(required=False, allow_blank=True, write_only=True, allow_null=True)

class PriceQuoteMultiRoomInputSerializer(serializers.Serializer):
    booking_rooms = BookingRoomQuoteSerializer(many=True)
    check_in = serializers.CharField()
    check_out = serializers.CharField()
    user_id = serializers.IntegerField(required=False, allow_null=True) 

class BookingListSerializer(serializers.ModelSerializer):
    hotel_name = serializers.CharField(source='booking_rooms.first.room_type.hotel.name', read_only=True)
    room_summary = serializers.SerializerMethodField()
    class Meta:
        model = Booking
        fields = ['booking_code', 'hotel_name', 'room_summary', 'check_in', 'check_out', 'total_price', 'status']
    def get_room_summary(self, obj):
        first_room = obj.booking_rooms.first()
        if first_room:
            return f"{first_room.quantity} x {first_room.room_type.name}"
        return "N/A"
class BookingStatusUpdateSerializer(serializers.Serializer):
    """
    Serializer for operator to update the status of a booking that is
    awaiting confirmation.
    """
    booking_code = serializers.CharField(max_length=8)
    new_status = serializers.ChoiceField(
        choices=['pending', 'no_capacity', 'cancelled']
    )

    def validate_booking_code(self, value):
        """
        Check that the booking exists and is in the correct status for an update.
        """
        try:
            booking = Booking.objects.get(booking_code=value, status='awaiting_confirmation')
        except Booking.DoesNotExist:
            raise serializers.ValidationError("رزروی با این کد یافت نشد یا در وضعیت 'منتظر تایید' قرار ندارد.")
        return booking # Return the booking object instead of the code

    def save(self, **kwargs):
        """
        Updates the booking status.
        """
        booking = self.validated_data['booking_code']
        new_status = self.validated_data['new_status']
        booking.status = new_status
        booking.save(update_fields=['status'])
        return booking
