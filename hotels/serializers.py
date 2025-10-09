# hotels/serializers.py
# version: 1.1
# This file contains serializers for converting hotel-related models to JSON format, with robust dynamic pricing and availability checks.

from rest_framework import serializers
from django.db.models import Count
from datetime import timedelta
from persiantools.jdatetime import JalaliDate
from decimal import Decimal

from .models import (
    City, Amenity, Hotel, RoomType, BoardType,
    TouristAttraction, HotelCategory, BedType, RoomCategory,
    HotelImage, RoomImage
)
# FIX: Import models and selectors from the pricing app for dynamic calculations.
from pricing.models import Availability, Price
from pricing.selectors import _get_daily_price_for_user

class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'icon']

class TouristAttractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TouristAttraction
        fields = ['id', 'name', 'description', 'image', 'latitude', 'longitude']

class CitySerializer(serializers.ModelSerializer):
    attractions = TouristAttractionSerializer(many=True, read_only=True)

    class Meta:
        model = City
        fields = ['id', 'name', 'slug', 'description', 'image', 'meta_title', 'meta_description', 'is_featured', 'attractions']

class HotelImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelImage
        fields = ['image', 'caption', 'order']

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

class RoomImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomImage
        fields = ['image', 'caption', 'order']

class BoardTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardType
        fields = ['id', 'name', 'code', 'description']

# FIX: Completely refactored RoomTypeSerializer to integrate dynamic pricing and availability.
class RoomTypeSerializer(serializers.ModelSerializer):
    amenities = AmenitySerializer(many=True, read_only=True)
    images = RoomImageSerializer(many=True, read_only=True)
    bed_types = BedTypeSerializer(many=True, read_only=True)
    room_categories = RoomCategorySerializer(many=True, read_only=True)
    
    # --- New dynamic fields ---
    is_available = serializers.SerializerMethodField()
    board_types = serializers.SerializerMethodField()
    calculated_price = serializers.SerializerMethodField()
    error_message = serializers.SerializerMethodField()

    class Meta:
        model = RoomType
        fields = [
            'id', 'name', 'code', 'description', 'base_capacity', 
            'extra_capacity', 'child_capacity', 'extra_person_price', 'child_price',
            'amenities', 'images', 'bed_types', 'room_categories',
            'is_available', 'board_types', 'calculated_price', 'error_message'
        ]

    def _get_date_range(self):
        """Helper to get and validate the date range from context."""
        check_in_str = self.context.get('check_in')
        duration_str = self.context.get('duration')

        if not check_in_str or not duration_str:
            return None, 0

        try:
            # Convert Jalali string to date object
            check_in_date = JalaliDate.fromisoformat(check_in_str).to_gregorian()
            duration = int(duration_str)
            if duration <= 0:
                return None, 0
            
            date_range = [check_in_date + timedelta(days=i) for i in range(duration)]
            return date_range, duration
        except (ValueError, TypeError):
            return None, 0

    def get_is_available(self, obj):
        """Check if the room has availability (quantity > 0) for the entire duration."""
        date_range, duration = self._get_date_range()
        if not date_range:
            return False

        available_days_count = Availability.objects.filter(
            room_type=obj,
            date__in=date_range,
            quantity__gt=0
        ).count()
        
        return available_days_count == duration

    def get_board_types(self, obj):
        """
        FIX: Returns board types that are valid for the stay.
        First, it checks for board types with defined daily prices for the entire duration.
        If none are found, it returns ALL board types, allowing the price calculation
        to use the fallback (base price) logic.
        """
        date_range, duration = self._get_date_range()
        if not date_range or not self.get_is_available(obj):
            return []

        # Find BoardTypes that have price entries for all days in the range
        valid_board_types = BoardType.objects.filter(
            prices__room_type=obj,
            prices__date__in=date_range
        ).annotate(
            days_priced=Count('prices__date')
        ).filter(
            days_priced=duration
        ).distinct()

        if valid_board_types.exists():
            return BoardTypeSerializer(valid_board_types, many=True).data
        
        # FIX: If no board types have daily prices for the whole duration,
        # return all board types so the fallback logic can be used.
        all_board_types = BoardType.objects.all()
        return BoardTypeSerializer(all_board_types, many=True).data


    def get_calculated_price(self, obj):
        """
        FIX: Calculates the total price by checking all available board types and selecting the cheapest one.
        It relies on the _get_daily_price_for_user function which contains the fallback logic.
        """
        date_range, duration = self._get_date_range()
        if not date_range or duration == 0 or not self.get_is_available(obj):
            return {'price': 0, 'duration': duration}

        board_types_data = self.get_board_types(obj)
        if not board_types_data:
            return {'price': 0, 'duration': duration, 'error': 'No board types available.'}

        user = self.context.get('request').user if self.context.get('request') else None
        min_total_price = float('inf')

        # Iterate through all valid or fallback board types to find the cheapest price
        for bt_data in board_types_data:
            board_type = BoardType.objects.get(id=bt_data['id'])
            current_total_price = Decimal(0)
            is_calculable = True
            for date in date_range:
                price_info = _get_daily_price_for_user(obj, board_type, date, user)
                if price_info and 'price_per_night' in price_info:
                    current_total_price += price_info['price_per_night']
                else:
                    is_calculable = False
                    break # Stop calculating for this board type if any day is unpriceable
            
            if is_calculable:
                min_total_price = min(min_total_price, current_total_price)

        if min_total_price == float('inf'):
            # This case means no price could be calculated for any board type
            return {'price': 0, 'duration': duration, 'error': 'Pricing could not be determined.'}

        return {'price': min_total_price, 'duration': duration}

    
    def get_error_message(self, obj):
        """Returns an error message if the room is not available for the selected dates."""
        check_in_str = self.context.get('check_in')
        if check_in_str and not self.get_is_available(obj):
            return "این اتاق در تاریخ انتخابی شما ظرفیت پذیرش ندارد، به منظور رزرو این اتاق در روز های دیگر لطفا تاریخ اقامت خود را تغییر دهید"
        return None

# Main serializer for Hotel details
class HotelSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    images = HotelImageSerializer(many=True, read_only=True)
    hotel_categories = HotelCategorySerializer(many=True, read_only=True)
    available_rooms = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = [
            'id', 'name', 'slug', 'stars', 'description', 'address', 'city',
            'amenities', 'images', 'hotel_categories', 'meta_title',
            'meta_description', 'latitude', 'longitude', 'check_in_time',
            'check_out_time', 'contact_phone', 'contact_email', 'rules',
            'available_rooms'
        ]
        
    def get_available_rooms(self, obj):
        """
        If date context is provided, uses the enhanced RoomTypeSerializer for dynamic data.
        If not, returns a basic list of all rooms with their static base price.
        """
        check_in = self.context.get('check_in')
        duration = self.context.get('duration')
        
        serializer_context = self.context
        room_types = obj.room_types.all()

        if check_in and duration:
            return RoomTypeSerializer(room_types, many=True, context=serializer_context).data
        else:
            # Fallback for when no date is selected: show all rooms with base price.
            rooms_data = []
            for room in room_types:
                rooms_data.append({
                    'id': room.id,
                    'name': room.name,
                    'base_capacity': room.base_capacity,
                    'is_available': False,
                    'board_types': [],
                    'calculated_price': {
                        'price': room.price_per_night,
                        'duration': 1
                    },
                    'error_message': None,
                    # Add other necessary fields from RoomTypeSerializer.Meta.fields for consistency
                    'code': room.code,
                    'description': room.description,
                    'extra_capacity': room.extra_capacity,
                    'child_capacity': room.child_capacity,
                    'extra_person_price': room.extra_person_price,
                    'child_price': room.child_price,
                    'amenities': AmenitySerializer(room.amenities.all(), many=True).data,
                    'images': RoomImageSerializer(room.images.all(), many=True).data,
                    'bed_types': BedTypeSerializer(room.bed_types.all(), many=True).data,
                    'room_categories': RoomCategorySerializer(room.room_categories.all(), many=True).data
                })
            return rooms_data
