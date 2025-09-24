# pricing/selectors.py

from datetime import timedelta
from django.db.models import Q
from hotels.models import RoomType, BoardType
from agencies.models import Contract, StaticRate
from .models import Availability, Price
from django.shortcuts import get_object_or_404
from decimal import Decimal


def _get_daily_price_for_user(room_type, board_type, date, user):
    """
    تابع کمکی نهایی برای پیدا کردن قیمت یک اتاق با یک سرویس خاص در یک روز خاص برای یک کاربر خاص.
    این تابع قوانین اولویت‌بندی قراردادها را پیاده‌سازی می‌کند.
    """
    # ۱. قیمت عمومی را به عنوان قیمت پایه در نظر می‌گیریم
    price_obj = Price.objects.filter(
        room_type=room_type, 
        board_type=board_type, 
        date=date
    ).first()
    if not price_obj:
        return None 
    
    price_info = {
        'price_per_night': price_obj.price_per_night,
        'extra_person_price': price_obj.extra_person_price,
        'child_price': price_obj.child_price
    }

    # اگر کاربر احراز هویت نشده یا عضو آژانس نباشد، قیمت عمومی را برمی‌گردانیم
    if not user or not user.is_authenticated or not hasattr(user, 'agency') or not user.agency:
        return price_info

    agency = user.agency
    
    # ۲. بررسی قراردادها با اولویت‌بندی
    # اولویت ۱: قرارداد نرخ ثابت برای این هتل خاص
    contract = Contract.objects.filter(
        agency=agency, 
        hotel=room_type.hotel, 
        contract_type='static',
        start_date__lte=date, 
        end_date__gte=date
    ).first()
    if contract:
        static_rate = StaticRate.objects.filter(
            contract=contract, 
            room_type=room_type
        ).first()
        if static_rate:
            price_info.update({
                'price_per_night': static_rate.price_per_night,
                'extra_person_price': static_rate.extra_person_price,
                'child_price': static_rate.child_price
            })
            return price_info

    # اولویت ۲: قرارداد درصد تخفیف برای این هتل خاص
    contract = Contract.objects.filter(
        agency=agency, 
        hotel=room_type.hotel, 
        contract_type='dynamic',
        start_date__lte=date, 
        end_date__gte=date
    ).first()
    if contract and contract.discount_percentage:
        discount = Decimal(contract.discount_percentage) / Decimal(100)
        price_info['price_per_night'] = price_info['price_per_night'] * (1 - discount)
        # می‌توان تخفیف را برای نفر اضافه و کودک هم اعمال کرد
        return price_info

    # اولویت ۳: تخفیف پیش‌فرض آژانس
    if agency.default_discount_percentage > 0:
        discount = Decimal(agency.default_discount_percentage) / Decimal(100)
        price_info['price_per_night'] = price_info['price_per_night'] * (1 - discount)
        return price_info

    return price_info


def find_available_rooms(city_id: int, check_in_date, check_out_date, adults: int, children: int, user):
    """
    موتور جستجوی نهایی که انواع سرویس‌ها و قیمت‌های مختلف را برمی‌گرداند.
    """
    duration = (check_out_date - check_in_date).days
    if duration <= 0:
        return []

    date_range = [check_in_date + timedelta(days=i) for i in range(duration)]
    
    room_types = RoomType.objects.filter(
        hotel__city_id=city_id,
        # فیلتر کردن بر اساس تعداد نفرات در مرحله جستجو حذف شد
    ).select_related('hotel').prefetch_related('prices__board_type')

    final_results = []
    for room in room_types:
        # بررسی موجودی برای کل دوره
        is_available = Availability.objects.filter(
            room_type=room, 
            date__in=date_range, 
            quantity__gt=0
        ).count() == duration
        if not is_available:
            continue

        available_prices = Price.objects.filter(
            room_type=room, 
            date__in=date_range
        ).select_related('board_type')
        
        prices_by_board_type = {}
        for price in available_prices:
            board_type_id = price.board_type.id
            if board_type_id not in prices_by_board_type:
                prices_by_board_type[board_type_id] = {
                    'board_type': price.board_type, 
                    'total_price': Decimal(0),
                    'total_extra_adults_cost': Decimal(0),
                    'total_children_cost': Decimal(0),
                    'is_complete': True
                }
            
            price_info = _get_daily_price_for_user(room, price.board_type, price.date, user)
            if price_info:
                extra_adults = max(0, adults - room.base_capacity)
                prices_by_board_type[board_type_id]['total_price'] += price_info['price_per_night']
                prices_by_board_type[board_type_id]['total_extra_adults_cost'] += extra_adults * price_info['extra_person_price']
                prices_by_board_type[board_type_id]['total_children_cost'] += children * price_info['child_price']
            else:
                prices_by_board_type[board_type_id]['is_complete'] = False

        board_options = [
            {
                'board_type_id': data['board_type'].id,
                'board_type_name': data['board_type'].name,
                # محاسبه قیمت نهایی شامل هزینه‌های اضافی
                'total_price': data['total_price'] + data['total_extra_adults_cost'] + data['total_children_cost']
            }
            for bt_id, data in prices_by_board_type.items() if data['is_complete']
        ]

        if board_options:
            final_results.append({
                'room_id': room.id,
                'room_name': room.name,
                'hotel_id': room.hotel.id,
                'hotel_name': room.hotel.name,
                'board_options': board_options
            })

    return final_results


def calculate_booking_price(room_type_id: int, board_type_id: int, check_in_date, check_out_date, adults: int, children: int, user):
    room_type = get_object_or_404(RoomType, id=room_type_id)
    board_type = get_object_or_404(BoardType, id=board_type_id)
    duration = (check_out_date - check_in_date).days
    date_range = [check_in_date + timedelta(days=i) for i in range(duration)]

    price_breakdown = []
    total_base_price = Decimal(0)
    total_extra_adults_cost = Decimal(0)
    total_children_cost = Decimal(0)
    
    extra_adults = max(0, adults - room_type.base_capacity)
    
    for single_date in date_range:
        price_info = _get_daily_price_for_user(room_type, board_type, single_date, user)
        if not price_info:
            return None

        base_price = price_info['price_per_night']
        extra_person_price = price_info['extra_person_price']
        child_price = price_info['child_price']
        
        price_breakdown.append({
            "date": single_date.strftime("%Y-%m-%d"), 
            "price": base_price
        })
        total_base_price += base_price
        total_extra_adults_cost += extra_adults * extra_person_price
        total_children_cost += children * child_price

    total_price = total_base_price + total_extra_adults_cost + total_children_cost
    
    return {
        "room_name": room_type.name,
        "hotel_name": room_type.hotel.name,
        "board_type_name": board_type.name,
        "price_breakdown": price_breakdown,
        "extra_adults_cost": total_extra_adults_cost,
        "children_cost": total_children_cost,
        "total_price": total_price,
    }
