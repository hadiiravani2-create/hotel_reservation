# pricing/selectors.py
# version: 6.1.0
# FIX: Added 'HotelImage' import and logic to fetch 'main_image' for search results.
# FEATURE: Includes hotel image URL in the find_available_hotels output.

from datetime import timedelta
from django.db.models import Count
# FIX: Added HotelImage to imports
from hotels.models import RoomType, BoardType, Hotel, HotelImage
from agencies.models import Contract, StaticRate
from .models import Price
from django.shortcuts import get_object_or_404
from decimal import Decimal
from collections import defaultdict

def _get_daily_price_for_user(room_type: RoomType, board_type: BoardType, date, user):
    """
    Calculates the price for a single room on a specific day for a given user.
    """
    public_price_obj = Price.objects.filter(room_type=room_type, board_type=board_type, date=date).first()

    if not public_price_obj:
        return None
    
    final_price = {
        'price_per_night': public_price_obj.price_per_night,
        'extra_person_price': public_price_obj.extra_person_price,
        'child_price': public_price_obj.child_price,
    }

    agency_user = user.agency_profile if hasattr(user, 'agency_profile') else None
    if not user.is_authenticated or not agency_user:
        return final_price

    contract = Contract.objects.filter(
        agency=agency_user.agency,
        start_date__lte=date,
        end_date__gte=date,
        hotel=room_type.hotel,
        is_active=True
    ).order_by('-priority').first()

    if not contract:
        return final_price

    static_rate = StaticRate.objects.filter(contract=contract, room_type=room_type).first()
    if static_rate:
        final_price['price_per_night'] = static_rate.price_per_night
        final_price['extra_person_price'] = static_rate.extra_person_price
        final_price['child_price'] = static_rate.child_price
        return final_price

    if contract.contract_type == 'dynamic' and contract.discount_percentage > 0:
        discount = final_price['price_per_night'] * (contract.discount_percentage / Decimal(100))
        final_price['price_per_night'] -= discount

    return final_price

def find_available_hotels(city_id: int, check_in_date, check_out_date, user, **filters):
    """
    جستجوی هتل‌های موجود بر اساس شهر و تاریخ، با قابلیت فیلتر قیمت و ستاره.
    """
    duration = (check_out_date - check_in_date).days
    if duration <= 0:
        return []

    date_range = [check_in_date + timedelta(days=i) for i in range(duration)]

    # گام ۱: پیدا کردن شناسه اتاق‌هایی که در کل بازه زمانی ظرفیت دارند
    available_room_ids = RoomType.objects.filter(
        hotel__city_id=city_id,
        availabilities__date__in=date_range,
        availabilities__quantity__gt=0
    ).annotate(
        num_available_days=Count('availabilities__date', distinct=True)
    ).filter(
        num_available_days=duration
    ).values_list('id', flat=True)

    if not available_room_ids:
        return []

    # گام ۲: دریافت یکجای تمام قیمت‌ها برای جلوگیری از N+1 Query
    all_prices = Price.objects.filter(
        room_type_id__in=available_room_ids,
        date__in=date_range
    ).select_related('room_type__hotel', 'board_type').order_by('date')
    
    prices_map = defaultdict(lambda: defaultdict(list))
    for price in all_prices:
        prices_map[price.room_type_id][price.date].append(price)

    # گام ۳: محاسبه ارزان‌ترین قیمت برای هر هتل
    hotel_min_prices = defaultdict(lambda: float('inf'))
    hotel_details = {}

    for room_id in available_room_ids:
        min_room_total_price = float('inf')
        
        # پیدا کردن BoardType هایی که برای کل مدت اقامت قیمت دارند
        board_type_day_counts = defaultdict(int)
        for date in date_range:
            for price_obj in prices_map[room_id][date]:
                board_type_day_counts[price_obj.board_type_id] += 1
        
        valid_board_type_ids = [bt_id for bt_id, count in board_type_day_counts.items() if count == duration]

        if not valid_board_type_ids:
            continue 

        # محاسبه قیمت کل برای هر سرویس معتبر
        for bt_id in valid_board_type_ids:
            current_board_total_price = Decimal(0)
            is_valid_stay = True
            
            for date in date_range:
                price_obj_for_day = next((p for p in prices_map[room_id][date] if p.board_type_id == bt_id), None)
                if price_obj_for_day is None: 
                    is_valid_stay = False; break
                
                price_info = _get_daily_price_for_user(price_obj_for_day.room_type, price_obj_for_day.board_type, date, user)
                if price_info is None: 
                    is_valid_stay = False; break 
                
                current_board_total_price += price_info['price_per_night']

            if is_valid_stay and current_board_total_price < min_room_total_price:
                min_room_total_price = current_board_total_price

        if min_room_total_price == float('inf') or min_room_total_price <= 0: 
            continue
            
        avg_price = min_room_total_price / Decimal(duration)
        
        # دسترسی به آبجکت هتل از طریق اولین قیمت پیدا شده برای اتاق
        first_price_obj = all_prices.filter(room_type_id=room_id).first()
        if not first_price_obj: continue
        
        hotel = first_price_obj.room_type.hotel
        hotel_id = hotel.id

        # ذخیره کمترین قیمت هتل و جزئیات آن
        if avg_price < hotel_min_prices[hotel_id]:
            hotel_min_prices[hotel_id] = avg_price
            # رفع باگ: ذخیره صریح آدرس
            hotel_details[hotel_id] = {
                'id': hotel_id, 
                'name': hotel.name, 
                'slug': hotel.slug, 
                'stars': hotel.stars,
                'address': hotel.address 
            }

    # گام ۳.۵: دریافت تصاویر اصلی هتل‌ها
    found_hotel_ids = list(hotel_details.keys())
    images = HotelImage.objects.filter(hotel_id__in=found_hotel_ids).order_by('hotel_id', 'order')
    image_map = {}
    for img in images:
        if img.hotel_id not in image_map:
            image_map[img.hotel_id] = img.image.url

    # پردازش فیلتر ستاره (تبدیل رشته "3,4,5" به لیست اعداد)
    target_stars = []
    if filters.get('stars'):
        try:
            # اگر فرمت string باشد (از URL) آن را تبدیل کن، اگر لیست باشد همان را استفاده کن
            stars_input = filters['stars']
            if isinstance(stars_input, str):
                target_stars = [int(s) for s in stars_input.split(',') if s.strip().isdigit()]
            elif isinstance(stars_input, list):
                target_stars = [int(s) for s in stars_input]
        except:
            pass

    # گام ۴: ساخت لیست نهایی و اعمال فیلترها
    results = []
    for hotel_id, info in hotel_details.items():
        min_price = hotel_min_prices[hotel_id]
        
        # ۱. فیلتر قیمت
        if (filters.get('min_price') and min_price < filters['min_price']) or \
           (filters.get('max_price') and min_price > filters['max_price']):
            continue

        # ۲. فیلتر ستاره
        if target_stars and info['stars'] not in target_stars:
            continue

        results.append({
            'hotel_id': info['id'],
            'hotel_name': info['name'],
            'hotel_slug': info['slug'],
            'hotel_stars': info['stars'],
            'min_price': min_price,
            'main_image': image_map.get(hotel_id),
            'address': info.get('address', '') # استفاده از .get برای اطمینان
        })
        
    return results

def calculate_multi_booking_price(booking_rooms, check_in_date, check_out_date, user):
    """
    Calculates the final price for a list of multiple room bookings across the entire stay duration.
    """
    room_types_map = {rt.id: rt for rt in RoomType.objects.filter(id__in=[r['room_type_id'] for r in booking_rooms])}
    board_types_map = {bt.id: bt for bt in BoardType.objects.filter(id__in=[r['board_type_id'] for r in booking_rooms])}
    
    duration = (check_out_date - check_in_date).days
    if duration <= 0: return None

    total_booking_price = Decimal(0)
    
    for room_data in booking_rooms:
        room_type_id = room_data['room_type_id']
        board_type_id = room_data['board_type_id']
        quantity = room_data['quantity']
        
        extra_adults = room_data.get('adults') or room_data.get('extra_adults') or 0
        children = room_data.get('children') or room_data.get('children_count') or 0

        room_type = room_types_map.get(room_type_id)
        board_type = board_types_map.get(board_type_id)

        if not room_type or not board_type:
            return None 

        room_selection_price = Decimal(0)
        
        for i in range(duration):
            current_date = check_in_date + timedelta(days=i)
            price_info = _get_daily_price_for_user(room_type, board_type, current_date, user)
            
            if price_info is None:
                return None

            daily_base_price_total = price_info['price_per_night'] * quantity
            daily_extra_adults_cost = Decimal(extra_adults) * price_info['extra_person_price'] * quantity
            daily_children_cost = Decimal(children) * price_info['child_price'] * quantity
            
            room_selection_price += daily_base_price_total + daily_extra_adults_cost + daily_children_cost

        total_booking_price += room_selection_price

    return {
        "total_price": total_booking_price
    }
