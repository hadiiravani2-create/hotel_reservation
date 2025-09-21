# pricing/serializers.py

from rest_framework import serializers

class RoomSearchResultSerializer(serializers.Serializer):
    """
    این سریالایزر، ساختار خروجی نتایج جستجو را تعریف میکند.
    """
    room_id = serializers.IntegerField()
    room_name = serializers.CharField(max_length=255)
    hotel_id = serializers.IntegerField()
    hotel_name = serializers.CharField(max_length=255)
    total_price = serializers.DecimalField(max_digits=20, decimal_places=0)
    price_per_night_avg = serializers.DecimalField(max_digits=20, decimal_places=0)

    # چون این سریالایزر فقط برای نمایش داده است، نیازی به متدهای create یا update ندارد.
    

class PriceQuoteInputSerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    check_in = serializers.CharField() # اعتبارسنجی دقیق‌تر تاریخ بعدا انجام می‌شود
    check_out = serializers.CharField()
    adults = serializers.IntegerField(min_value=1)
    children = serializers.IntegerField(min_value=0, default=0)

class PriceBreakdownSerializer(serializers.Serializer):
    date = serializers.CharField()
    price = serializers.DecimalField(max_digits=20, decimal_places=0)

class PriceQuoteOutputSerializer(serializers.Serializer):
    room_name = serializers.CharField()
    hotel_name = serializers.CharField()
    price_breakdown = PriceBreakdownSerializer(many=True)
    extra_adults_cost = serializers.DecimalField(max_digits=20, decimal_places=0)
    children_cost = serializers.DecimalField(max_digits=20, decimal_places=0)
    total_price = serializers.DecimalField(max_digits=20, decimal_places=0)