# attractions/serializers.py
# version: 2.0.0
# FEATURE: Updated serializers to support list of categories, amenities, and audiences.

from rest_framework import serializers
from .models import (
    Attraction, AttractionCategory, AttractionGallery,
    AttractionAudience, AttractionAmenity
)

class AttractionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttractionCategory
        fields = ['id', 'name', 'slug', 'icon_name']

class AttractionAudienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttractionAudience
        fields = ['id', 'name']

class AttractionAmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttractionAmenity
        fields = ['id', 'name', 'icon_name']

class AttractionGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttractionGallery
        fields = ['image', 'caption', 'order', 'is_cover']

class AttractionSerializer(serializers.ModelSerializer):
    # Nested Serializers for rich data response
    categories = AttractionCategorySerializer(many=True, read_only=True)
    audiences = AttractionAudienceSerializer(many=True, read_only=True)
    amenities = AttractionAmenitySerializer(many=True, read_only=True)
    
    images = AttractionGallerySerializer(many=True, read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    
    visit_info = serializers.SerializerMethodField()

    class Meta:
        model = Attraction
        fields = [
            'id', 'name', 'slug', 'city_name', 
            'categories', 'audiences', 'amenities',
            'description', 'short_description', 
            'latitude', 'longitude', 
            'visiting_hours', 'best_visit_time', 'entry_fee', # Updated fields
            'rating', 'is_featured', 'images', 'visit_info'
        ]

    def get_visit_info(self, obj):
        return {
            'hours': obj.visiting_hours,
            'best_time': obj.get_best_visit_time_display(),
            'fee': obj.entry_fee
        }
