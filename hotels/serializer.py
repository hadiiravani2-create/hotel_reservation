# hotels/serializers.py

from rest_framework import serializers
from .models import (
    City, Amenity, Hotel, RoomType, BoardType,
    TouristAttraction, HotelCategory, BedType, RoomCategory,
    HotelImage, RoomImage
)

class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name']

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

class RoomTypeSerializer(serializers.ModelSerializer):
    amenities = AmenitySerializer(many=True, read_only=True)
    images = RoomImageSerializer(many=True, read_only=True)
    bed_types = BedTypeSerializer(many=True, read_only=True)
    room_categories = RoomCategorySerializer(many=True, read_only=True)

    class Meta:
        model = RoomType
        fields = [
            'id', 'name', 'code', 'description', 'amenities', 'images', 'bed_types',
            'room_categories', 'base_capacity', 'extra_capacity', 'child_capacity',
            'extra_person_price', 'child_price'
        ]


class HotelSerializer(serializers.ModelSerializer):
    amenities = AmenitySerializer(many=True, read_only=True)
    images = HotelImageSerializer(many=True, read_only=True)
    hotel_categories = HotelCategorySerializer(many=True, read_only=True)
    room_types = RoomTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Hotel
        fields = [
            'id', 'name', 'slug', 'stars', 'description', 'address', 'city', 'amenities',
            'images', 'hotel_categories', 'meta_title', 'meta_description', 'latitude',
            'longitude', 'check_in_time', 'check_out_time', 'contact_phone',
            'contact_email', 'room_types'
        ]
