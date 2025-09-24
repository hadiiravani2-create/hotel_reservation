# pricing/serializers.py
from rest_framework import serializers

class BoardOptionSerializer(serializers.Serializer):
    board_type_id = serializers.IntegerField()
    board_type_name = serializers.CharField()
    total_price = serializers.DecimalField(max_digits=20, decimal_places=0)


class RoomSearchResultSerializer(serializers.Serializer):
    room_id = serializers.IntegerField()
    room_name = serializers.CharField()
    hotel_id = serializers.IntegerField()
    hotel_name = serializers.CharField()
    board_options = BoardOptionSerializer(many=True)


class PriceQuoteInputSerializer(serializers.Serializer):
    room_type_id = serializers.IntegerField()
    board_type_id = serializers.IntegerField()
    check_in = serializers.CharField()
    check_out = serializers.CharField()
    adults = serializers.IntegerField(min_value=1)
    children = serializers.IntegerField(min_value=0, default=0)


class PriceBreakdownSerializer(serializers.Serializer):
    date = serializers.CharField()
    price = serializers.DecimalField(max_digits=20, decimal_places=0)


class PriceQuoteOutputSerializer(serializers.Serializer):
    room_name = serializers.CharField()
    hotel_name = serializers.CharField()
    board_type_name = serializers.CharField()
    price_breakdown = PriceBreakdownSerializer(many=True)
    extra_adults_cost = serializers.DecimalField(max_digits=20, decimal_places=0)
    children_cost = serializers.DecimalField(max_digits=20, decimal_places=0)
    total_price = serializers.DecimalField(max_digits=20, decimal_places=0)   

