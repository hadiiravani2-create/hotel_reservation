#pricing/serializers.py v1.0.1
#Update: Added HotelSearchResultSerializer to support the new hotel search API response structure.
from rest_framework import serializers

# سریالایزر جدید برای نتایج جستجوی هتل
class HotelSearchResultSerializer(serializers.Serializer):
    hotel_id = serializers.IntegerField()
    hotel_name = serializers.CharField(max_length=255)
    hotel_slug = serializers.SlugField()
    hotel_stars = serializers.IntegerField()
    min_price = serializers.DecimalField(max_digits=20, decimal_places=0)
    main_image = serializers.CharField(allow_null=True, required=False)
    address = serializers.CharField(allow_null=True, required=False)

# --- سریالایزرهای قبلی بدون تغییر باقی می‌مانند ---

class RoomSearchResultSerializer(serializers.Serializer):
    room_id = serializers.IntegerField()
    room_name = serializers.CharField()
    hotel_id = serializers.IntegerField()
    hotel_name = serializers.CharField()
    board_options = serializers.ListField(child=serializers.DictField())


class PriceQuoteInputSerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    board_type_id = serializers.IntegerField()
    check_in = serializers.CharField()
    check_out = serializers.CharField()
    # این دو فیلد برای سازگاری با فرمت قدیمی نگه داشته شده‌اند
    adults = serializers.IntegerField(required=False, default=0) 
    children = serializers.IntegerField(required=False, default=0)


class RoomCalendarSerializer(serializers.Serializer):
    date = serializers.CharField()
    price = serializers.IntegerField(allow_null=True)
    is_available = serializers.BooleanField()
    status_text = serializers.CharField()

class PriceQuoteOutputSerializer(serializers.Serializer):
    room_name = serializers.CharField()
    hotel_name = serializers.CharField()
    board_type_name = serializers.CharField()
    price_breakdown = serializers.ListField(child=serializers.DictField())
    extra_adults_cost = serializers.DecimalField(max_digits=20, decimal_places=0)
    children_cost = serializers.DecimalField(max_digits=20, decimal_places=0)
    total_price = serializers.DecimalField(max_digits=20, decimal_places=0)
