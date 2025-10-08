# hotels/serializers.py
# version: 0.1
# This file contains serializers for converting hotel-related models to JSON format.

from rest_framework import serializers
from .models import (
    City, Amenity, Hotel, RoomType, BoardType,
    TouristAttraction, HotelCategory, BedType, RoomCategory,
    HotelImage, RoomImage
)

class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'icon'] # icon field added for frontend use

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

# New serializer for board types (e.g., Breakfast, Full Board).
class BoardTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoardType
        fields = ['id', 'name', 'code', 'description']

# Enhanced serializer for RoomType, calculates price and shows board types.
class RoomTypeSerializer(serializers.ModelSerializer):
    amenities = AmenitySerializer(many=True, read_only=True)
    images = RoomImageSerializer(many=True, read_only=True)
    bed_types = BedTypeSerializer(many=True, read_only=True)
    room_categories = RoomCategorySerializer(many=True, read_only=True)
    board_types = serializers.SerializerMethodField()
    calculated_price = serializers.SerializerMethodField()

    class Meta:
        model = RoomType
        fields = [
            'id', 'name', 'code', 'description', 'base_capacity', 'price_per_night',
            'extra_capacity', 'child_capacity', 'extra_person_price', 'child_price',
            'amenities', 'images', 'bed_types', 'room_categories',
            'board_types', 'calculated_price' # New dynamic fields
        ]

    def get_board_types(self, obj):
        board_types = BoardType.objects.all()
        return BoardTypeSerializer(board_types, many=True).data

    def get_calculated_price(self, obj):
        duration_str = self.context.get('duration')
        duration = 1
        if duration_str:
            try:
                duration = int(duration_str) if int(duration_str) > 0 else 1
            except (ValueError, TypeError):
                duration = 1
        
        total_price = obj.price_per_night * duration
        return {'price': total_price, 'duration': duration}

# Main serializer for Hotel details, now includes available rooms.
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
            'available_rooms' # Changed from room_types
        ]
        
    def get_available_rooms(self, obj):
        # This method will contain the logic to filter available rooms.
        # For now, it returns all rooms but passes the context for price calculation.
        room_types = obj.room_types.all()
        serializer_context = self.context
        return RoomTypeSerializer(room_types, many=True, context=serializer_context).data
