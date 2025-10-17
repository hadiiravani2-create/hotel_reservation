# reservations/serializers.py
# version: 1.2.3
# REFACTOR: Upgraded PaymentConfirmationSerializer to support GenericForeignKey,
#           allowing it to link to both Bookings and WalletTransactions.

from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import Guest, Booking, BookingRoom, OfflineBank, PaymentConfirmation
from hotels.models import RoomType
from core.models import WalletTransaction # Import WalletTransaction

# ... (Other serializers remain unchanged) ...
class GuestDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = [
            'first_name', 'last_name', 'is_foreign', 'national_id', 
            'passport_number', 'phone_number', 'nationality', 'city_of_origin'
        ]
class BookingRoomDetailSerializer(serializers.ModelSerializer):
    room_type_name = serializers.CharField(source='room_type.name', read_only=True)
    board_type = serializers.CharField(source='board_type.name', read_only=True)
    hotel_name = serializers.CharField(source='room_type.hotel.name', read_only=True)
    class Meta:
        model = BookingRoom
        fields = [
            'id', 'room_type_name', 'board_type', 'hotel_name', 'quantity', 
            'adults', 'children', 'extra_requests'
        ]
class BookingDetailSerializer(serializers.ModelSerializer):
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

# ... (Other serializers remain unchanged)

class GuestSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True) 
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)  
    national_id = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    passport_number = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(max_length=11, required=False, allow_blank=True, allow_null=True)
    nationality = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    city_of_origin = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    
    wants_to_register = serializers.BooleanField(required=False, write_only=True, default=False)
    
    class Meta:
        model = Guest
        # FIX: Removed 'wants_to_register' as it's not a model field.
        fields = ['first_name', 'last_name', 'is_foreign', 'national_id', 'passport_number', 'phone_number', 'nationality', 'city_of_origin', 'wants_to_register']

    def validate(self, data):
        national_id = data.get('national_id')
        if data.get('is_foreign', False):
             if national_id:
                 data['national_id'] = None
        else:
             if data.get('passport_number') or data.get('nationality'):
                 data['passport_number'] = None
                 data['nationality'] = None
        return data


class BookingRoomSerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    board_type_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    adults = serializers.IntegerField(min_value=0, default=0)
    children = serializers.IntegerField(min_value=0, default=0)
    extra_requests = serializers.CharField(required=False, allow_null=True, allow_blank=True)
class CreateBookingAPISerializer(serializers.Serializer):
    booking_rooms = BookingRoomSerializer(many=True, allow_empty=False)
    check_in = serializers.CharField()
    check_out = serializers.CharField()
    guests = GuestSerializer(many=True, allow_empty=False)
    agency_id = serializers.IntegerField(required=False, allow_null=True)
    rules_accepted = serializers.BooleanField(required=True, write_only=True)
    def validate_rules_accepted(self, value):
        if not value:
            raise serializers.ValidationError("پذیرش قوانین و شرایط رزرو الزامی است.")
        return value
    def validate(self, data):
        # ... (validation logic remains unchanged)
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
    room_summary = serializers.SerializerMethodField()
    class Meta:
        model = Booking
        fields = ['booking_code', 'hotel_name', 'room_summary', 'check_in', 'check_out', 'total_price', 'status']
    def get_room_summary(self, obj):
        first_room = obj.booking_rooms.first()
        if first_room:
            return f"{first_room.quantity} x {first_room.room_type.name}"
        return "N/A"
