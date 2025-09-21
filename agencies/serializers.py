# agencies/serializers.py

from rest_framework import serializers
from .models import Agency, AgencyTransaction
from reservations.serializers import BookingListSerializer

class AgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = ['name', 'contact_person', 'phone_number', 'credit_limit', 'current_balance']

class AgencyTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgencyTransaction
        fields = ['amount', 'transaction_type', 'transaction_date', 'description', 'created_at']

class AgencyReportSerializer(serializers.Serializer):
    """
    این سریالایزر، داده‌های چند مدل مختلف را برای گزارش نهایی ترکیب می‌کند.
    """
    agency = AgencySerializer()
    bookings = BookingListSerializer(many=True)
    transactions = AgencyTransactionSerializer(many=True)