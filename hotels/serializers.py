# hotels/serializers.py
# version: 2.1.1
# FIX: Robust handling of None values in price calculation (TypeError fix).
#      Added safety checks for 'current_total_extra' and 'current_total_child'.

from rest_framework import serializers
from django.db.models import Count, Min, Avg
from datetime import timedelta
from persiantools.jdatetime import JalaliDate
from decimal import Decimal

from .models import (
    City, Amenity, Hotel, RoomType, BoardType,
    HotelCategory, BedType, RoomCategory,
    HotelImage, RoomImage
)

from attractions.models import Attraction, AttractionGallery

from pricing.models import Availability, Price
from pricing.selectors import _get_daily_price_for_user
from cancellations.serializers import CancellationPolicySerializer


# ==============================================================================
# 1. NESTED SERIALIZERS (Defined First)
# ==============================================================================

def calculate_hotel_min_price(hotel_obj, context):
    """
    Helper to calculate min price for Hotel and SuggestedHotel serializers.
    """
    request = context.get('request')
    check_in_str = None
    
    if context.get('check_in'):
        check_in_str = context.get('check_in')
    elif request and request.query_params.get('check_in'):
        check_in_str = request.query_params.get('check_in')
        
    target_date = None
    if check_in_str:
        try:
            target_date = JalaliDate.fromisoformat(check_in_str).to_gregorian()
        except ValueError:
            pass
    
    if not target_date:
        target_date = JalaliDate.today().to_gregorian()

    min_p = float('inf')
    found_price = False
    user = request.user if request else None
    
    for room in hotel_obj.room_types.all():
        for board in BoardType.objects.all():
            price_info = _get_daily_price_for_user(room, board, target_date, user)
            if price_info and price_info.get('price_per_night'):
                price = price_info['price_per_night']
                if price > 0 and price < min_p:
                    min_p = price
                    found_price = True
    
    return min_p if found_price else 0

class AttractionGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = AttractionGallery
        fields = ['image', 'caption', 'order', 'is_cover']

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


# ==============================================================================
# 2. MAIN SERIALIZERS
# ==============================================================================

class AttractionSerializer(serializers.ModelSerializer):
    images = AttractionGallerySerializer(many=True, read_only=True)
    
    class Meta:
        model = Attraction
        fields = ['id', 'name', 'slug', 'description', 'images', 'latitude', 'longitude']

class CitySerializer(serializers.ModelSerializer):
    attractions = AttractionSerializer(many=True, read_only=True)
    class Meta:
        model = City
        fields = ['id', 'name', 'slug', 'description', 'image', 'attractions', 'latitude', 'longitude']

class PricedBoardTypeSerializer(serializers.Serializer):
    board_type = BoardTypeSerializer(read_only=True)
    total_price = serializers.DecimalField(max_digits=20, decimal_places=0, read_only=True)
    total_extra_adult_price = serializers.DecimalField(max_digits=20, decimal_places=0, read_only=True)
    total_child_price = serializers.DecimalField(max_digits=20, decimal_places=0, read_only=True)

class RoomTypeSerializer(serializers.ModelSerializer):
    amenities = AmenitySerializer(many=True, read_only=True)
    images = RoomImageSerializer(many=True, read_only=True)
    bed_types = BedTypeSerializer(many=True, read_only=True)
    room_categories = RoomCategorySerializer(many=True, read_only=True)
    
    extra_adult_price = serializers.SerializerMethodField()
    child_price = serializers.SerializerMethodField()
    
    is_available = serializers.SerializerMethodField()
    availability_quantity = serializers.SerializerMethodField()
    priced_board_types = serializers.SerializerMethodField()
    error_message = serializers.SerializerMethodField()

    class Meta:
        model = RoomType
        fields = [
            'id', 'name', 'priority', 'code', 'description', 'base_capacity', 
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

    def _get_dynamic_extra_price(self, obj, field_name):
        date_range, duration = self._get_date_range()
        static_field = 'extra_person_price' if field_name == 'extra' else 'child_price'
        
        if not date_range:
            return getattr(obj, static_field, 0)

        avg_price = Price.objects.filter(
            room_type=obj,
            date__in=date_range
        ).aggregate(
            avg_val=Avg(static_field)
        )['avg_val']

        if avg_price is not None:
            return int(avg_price)
        
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
            current_total_price = Decimal(0)
            current_total_extra = Decimal(0) 
            current_total_child = Decimal(0) 
            is_calculable = True
            
            for date in date_range:
                price_info = _get_daily_price_for_user(obj, board_type, date, user)
                
                if price_info and 'price_per_night' in price_info:
                    # [GEM-UPDATE] Added 'or 0' to prevent TypeError if value is None
                    current_total_price += (price_info['price_per_night'] or 0)
                    current_total_extra += (price_info.get('extra_person_price') or 0)
                    current_total_child += (price_info.get('child_price') or 0)
                else:
                    is_calculable = False; break
            
            if is_calculable and current_total_price > 0:
                priced_boards.append({
                    'board_type': board_type, 
                    'total_price': current_total_price,
                    'total_extra_adult_price': current_total_extra,
                    'total_child_price': current_total_child
                })
        
        return PricedBoardTypeSerializer(priced_boards, many=True).data

class HotelSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    images = HotelImageSerializer(many=True, read_only=True)
    hotel_categories = HotelCategorySerializer(many=True, read_only=True)
    min_price = serializers.SerializerMethodField()
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
            'min_price', 'available_rooms',
            'cancellation_policy_normal', 'cancellation_policy_peak'
        ]

    def get_min_price(self, obj):
        return calculate_hotel_min_price(obj, self.context)

    def get_available_rooms(self, obj):
        # تغییر منطق: اگر تاریخ نبود، همه اتاق‌ها را بده. اگر بود، فیلتر کن.
        check_in = self.context.get('check_in')
        duration = self.context.get('duration')
        
        all_rooms_serializer = RoomTypeSerializer(obj.room_types.all(), many=True, context=self.context)
        all_rooms_data = all_rooms_serializer.data

        if check_in and duration:
            # حالت اول: تاریخ انتخاب شده -> فیلتر کردن اتاق‌های پر شده
            available_rooms = [room for room in all_rooms_data if room.get('is_available')]
        else:
            # حالت دوم: تاریخ انتخاب نشده -> نمایش همه اتاق‌ها (برای ویترین)
            available_rooms = all_rooms_data

        def sort_key(room):
            # 1. اولویت (Priority)
            priority = room.get('priority', 0)
            
            # 2. قیمت
            # نکته: اگر تاریخ نباشد، priced_board_types خالی است و قیمت inf می‌شود که برای مرتب‌سازی اوکی است
            prices = [item['total_price'] for item in room.get('priced_board_types', [])]
            min_price = min(prices) if prices else float('inf')
            
            return (priority, min_price)
            
        available_rooms.sort(key=sort_key)
        return available_rooms

class SuggestedHotelSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name')
    main_image = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = ['id', 'name', 'slug', 'stars', 'city_name', 'main_image', 'min_price']

    def get_main_image(self, obj):
        first_image = obj.images.first()
        if first_image:
            request = self.context.get('request')
            return request.build_absolute_uri(first_image.image.url) if request else first_image.image.url
        return None

    def get_min_price(self, obj):
        return calculate_hotel_min_price(obj, self.context)

