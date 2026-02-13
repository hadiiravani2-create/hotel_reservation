# services/serializers.py
# version: 1.1.0
# FIX: Added the missing BookedServiceSerializer.

from rest_framework import serializers
from .models import HotelService, ServiceType, BookedService

class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = ['id', 'name', 'requires_details']

class HotelServiceSerializer(serializers.ModelSerializer):
    service_type = ServiceTypeSerializer(read_only=True)
    class Meta:
        model = HotelService
        fields = [
            'id',
            'name',
            'description',
            'pricing_model',
            'price',
            'service_type',
            'is_taxable'
        ]

# --- ADDITION: The missing serializer ---
class BookedServiceSerializer(serializers.ModelSerializer):
    """
    Serializer for the BookedService model, used to display services attached to a booking.
    """
    hotel_service = HotelServiceSerializer(read_only=True)
    class Meta:
        model = BookedService
        fields = ['id', 'hotel_service', 'quantity', 'total_price', 'details']
# --- END ADDITION ---
