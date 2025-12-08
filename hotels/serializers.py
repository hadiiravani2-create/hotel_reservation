# hotels/serializers.py
# version: 1.5.1
# FIX: Re-supplying full file to ensure '_get_dynamic_extra_price' helper method is present.

from rest_framework import serializers
from django.db.models import Count, Min, Avg
from datetime import timedelta
from persiantools.jdatetime import JalaliDate
from decimal import Decimal

from .models import (
    City, Amenity, Hotel, RoomType, BoardType,
    TouristAttraction, HotelCategory, BedType, RoomCategory,
    HotelImage, RoomImage
)
from pricing.models import Availability, Price
from pricing.selectors import _get_daily_price_for_user
from cancellations.serializers import CancellationPolicySerializer


# --- START: All Base Serializers Defined First ---

class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'icon']

class HotelImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelImage
        fields = ['image', 'caption', 'order']

class RoomImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomImage
        fields = ['image', 'caption', 'order']

class BoardTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardType
        fields = ['id', 'name', 'code', 'description']

class TouristAttractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TouristAttraction
        fields = ['id', 'name', 'description', 'image', 'latitude', 'longitude']

class HotelCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelCategory
        fields = ['id', 'name', 'slug']

class BedTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BedType
        fields = ['id', 'name', 'slug']
        
class RoomCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomCategory
        fields = ['id', 'name', 'slug']

class CitySerializer(serializers.ModelSerializer):
    attractions = TouristAttractionSerializer(many=True, read_only=True)
    class Meta:
        model = City
        fields = ['id', 'name', 'slug', 'description', 'image', 'attractions']

# --- END: All Base Serializers Defined First ---


# --- Composite and Method-based Serializers ---

class PricedBoardTypeSerializer(serializers.Serializer):
    board_type = BoardTypeSerializer(read_only=True)
    total_price = serializers.DecimalField(max_digits=20, decimal_places=0, read_only=True)

class RoomTypeSerializer(serializers.ModelSerializer):
    amenities = AmenitySerializer(many=True, read_only=True)
    images = RoomImageSerializer(many=True, read_only=True)
    bed_types = BedTypeSerializer(many=True, read_only=True)
    room_categories = RoomCategorySerializer(many=True, read_only=True)
    
    # Dynamic pricing fields
    extra_adult_price = serializers.SerializerMethodField()
    child_price = serializers.SerializerMethodField()

    is_available = serializers.SerializerMethodField()
    availability_quantity = serializers.SerializerMethodField()
    priced_board_types = serializers.SerializerMethodField()
    error_message = serializers.SerializerMethodField()

    class Meta:
        model = RoomType
        fields = [
            'id', 'name', 'code', 'description', 'base_capacity', 
            'extra_capacity', 'child_capacity', 
            'extra_adult_price', 'child_price', 
            'amenities', 'images', 
            'bed_types', 'room_categories',
            'is_available', 'availability_quantity', 'priced_board_types', 'error_message'
        ]

    def _get_date_range(self):
        check_in_str = self.context.get('check_in')
        duration_str = self.context.get('duration')
        if not check_in_str or not duration_str: return None, 0
        try:
            check_in_date = JalaliDate.fromisoformat(check_in_str).to_gregorian()
            duration = int(duration_str)
            if duration <= 0: return None, 0
            return [check_in_date + timedelta(days=i) for i in range(duration)], duration
        except (ValueError, TypeError): return None, 0

    # --- Helper Method that was missing ---
    def _get_dynamic_extra_price(self, obj, field_name):
        date_range, duration = self._get_date_range()
        
        # Determine the fallback static field name on the model
        static_field = 'extra_person_price' if field_name == 'extra' else 'child_price'
        
        if not date_range:
            return getattr(obj, static_field, 0)

        # Fetch actual prices for the date range
        avg_price = Price.objects.filter(
            room_type=obj,
            date__in=date_range
        ).aggregate(
            avg_val=Avg(static_field)
        )['avg_val']

        if avg_price is not None:
            return int(avg_price)
        
        # If no dynamic prices exist, fallback to static
        return getattr(obj, static_field, 0)

    def get_extra_adult_price(self, obj):
        return self._get_dynamic_extra_price(obj, 'extra')

    def get_child_price(self, obj):
        return self._get_dynamic_extra_price(obj, 'child')

    def get_is_available(self, obj):
        date_range, duration = self._get_date_range()
        if not date_range: return False
        return Availability.objects.filter(room_type=obj, date__in=date_range, quantity__gt=0).count() == duration

    def get_availability_quantity(self, obj):
        date_range, duration = self._get_date_range()
        if not date_range: return 0
        if not self.get_is_available(obj): return 0
        min_availability = Availability.objects.filter(
            room_type=obj, 
            date__in=date_range
        ).aggregate(min_q=Min('quantity'))['min_q'] or 0
        return min_availability

    def get_error_message(self, obj):
        if self.context.get('check_in') and not self.get_is_available(obj):
            return "این اتاق در تاریخ انتخابی شما ظرفیت پذیرش ندارد."
        return None

    def get_priced_board_types(self, obj):
        date_range, duration = self._get_date_range()
        if not date_range or self.get_availability_quantity(obj) == 0: return []
        user = self.context.get('request').user if self.context.get('request') else None
        
        priced_boards = []
        for board_type in BoardType.objects.all():
            current_total_price, is_calculable = Decimal(0), True
            for date in date_range:
                price_info = _get_daily_price_for_user(obj, board_type, date, user)
                if price_info and 'price_per_night' in price_info:
                    current_total_price += price_info['price_per_night']
                else:
                    is_calculable = False; break
            
            if is_calculable and current_total_price > 0:
                priced_boards.append({'board_type': board_type, 'total_price': current_total_price})
        
        return PricedBoardTypeSerializer(priced_boards, many=True).data

class HotelSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    images = HotelImageSerializer(many=True, read_only=True)
    hotel_categories = HotelCategorySerializer(many=True, read_only=True)
    available_rooms = serializers.SerializerMethodField()
    cancellation_policy_normal = CancellationPolicySerializer(read_only=True)
    cancellation_policy_peak = CancellationPolicySerializer(read_only=True)

    class Meta:
        model = Hotel
        fields = [
            'id', 'name', 'slug', 'stars', 'description', 'address', 'city',
            'amenities', 'images', 'hotel_categories', 'meta_title',
            'meta_description', 'latitude', 'longitude', 'check_in_time',
            'check_out_time', 'contact_phone', 'contact_email', 'rules',
            'available_rooms','cancellation_policy_normal', 'cancellation_policy_peak'
        ]

    def get_available_rooms(self, obj):
        if not self.context.get('check_in') or not self.context.get('duration'): return []
        all_rooms_data = RoomTypeSerializer(obj.room_types.all(), many=True, context=self.context).data
        available_rooms = [room for room in all_rooms_data if room.get('is_available')]
        def sort_key(room):
            prices = [item['total_price'] for item in room.get('priced_board_types', [])]
            return min(prices) if prices else float('inf') 
        available_rooms.sort(key=sort_key)
        return available_rooms

class SuggestedHotelSerializer(serializers.ModelSerializer):
    """
    A lightweight serializer for displaying suggested hotels on the homepage.
    """
    city_name = serializers.CharField(source='city.name')
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = ['id', 'name', 'slug', 'stars', 'city_name', 'main_image']

    def get_main_image(self, obj):
        first_image = obj.images.first()
        if first_image:
            request = self.context.get('request')
            return request.build_absolute_uri(first_image.image.url) if request else first_image.image.url
        return None
