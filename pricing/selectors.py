# pricing/selectors.py

from datetime import timedelta
from django.utils import timezone
from hotels.models import Hotel, RoomType
from agencies.models import Contract, StaticRate
from .models import Availability, Price
from django.shortcuts import get_object_or_404
from jdatetime import date as jdate

def _get_daily_price_for_user(room_type, date, user):
    """
    یک تابع کمکی برای پیدا کردن قیمت یک اتاق در یک روز خاص برای یک کاربر خاص.
    این تابع منطق قراردادها را بررسی می‌کند.
    """
    # حالت پیش‌فرض: قیمت عمومی
    daily_price_obj = Price.objects.filter(room_type=room_type, date=date).first()
    if daily_price_obj:
        price_per_night = daily_price_obj.price_per_night
        extra_person_price = daily_price_obj.extra_person_price
        child_price = daily_price_obj.child_price
    else:
        price_per_night = room_type.price_per_night
        extra_person_price = room_type.extra_person_price
        child_price = room_type.child_price

    # اگر کاربر احراز هویت نشده یا عضو آژانس نباشد، همین قیمت عمومی را برمی‌گردانیم
    if not user or not user.is_authenticated or not hasattr(user, 'agency') or not user.agency:
        return price_per_night, extra_person_price, child_price

    # اگر کاربر عضو آژانس بود، به دنبال قرارداد می‌گردیم
    agency = user.agency
    contract = Contract.objects.filter(
        agency=agency,
        hotel=room_type.hotel,
        start_date__lte=date,
        end_date__gte=date
    ).first()

    if contract:
        if contract.contract_type == 'static':
            static_rate = StaticRate.objects.filter(contract=contract, room_type=room_type).first()
            if static_rate:
                # اگر نرخ ثابت در قرارداد وجود داشت، آن را برمی‌گردانیم
                return static_rate.price_per_night, static_rate.extra_person_price, static_rate.child_price

        elif contract.contract_type == 'dynamic' and contract.discount_percentage:
            # اگر قرارداد تخفیف درصدی بود، تخفیف را اعمال می‌کنیم
            discount = contract.discount_percentage / 100
            price_per_night -= (price_per_night * discount)
            extra_person_price -= (extra_person_price * discount)
            child_price -= (child_price * discount)
            return price_per_night, extra_person_price, child_price

    # اگر قراردادی برای هتل خاص یافت نشد، تخفیف پیش‌فرض آژانس را اعمال می‌کنیم
    if agency.default_discount_percentage > 0:
        discount = agency.default_discount_percentage / 100
        price_per_night -= (price_per_night * discount)
        # ... (می‌توان تخفیف را برای نفر اضافه و کودک هم اعمال کرد)

    return price_per_night, extra_person_price, child_price


def find_available_rooms(city_id: int, check_in_date, check_out_date, adults: int, children: int, user):
    duration = (check_out_date - check_in_date).days
    if duration <= 0:
        return []
    date_range = [check_in_date + timedelta(days=i) for i in range(duration)]

    room_types = RoomType.objects.filter(
        hotel__city_id=city_id,
        base_capacity__gte=adults
    ).select_related('hotel')

    available_rooms_with_price = []
    for room in room_types:
        is_available_for_all_nights = True
        total_price = 0

        availabilities = {a.date: a.quantity for a in Availability.objects.filter(room_type=room, date__in=date_range)}

        for single_date in date_range:
            if availabilities.get(single_date, 0) < 1:
                is_available_for_all_nights = False
                break

            # از تابع کمکی جدید برای گرفتن قیمت استفاده می‌کنیم
            price_per_night, _, _ = _get_daily_price_for_user(room, single_date, user)
            total_price += price_per_night

        if is_available_for_all_nights:
            available_rooms_with_price.append({
                'room_id': room.id,
                'room_name': room.name,
                'hotel_id': room.hotel.id,
                'hotel_name': room.hotel.name,
                'total_price': total_price,
                'price_per_night_avg': total_price / duration if duration > 0 else 0,
            })
    return available_rooms_with_price


def calculate_booking_price(room_type_id: int, check_in_date, check_out_date, adults: int, children: int, user):
    room_type = get_object_or_404(RoomType, id=room_type_id)
    duration = (check_out_date - check_in_date).days
    date_range = [check_in_date + timedelta(days=i) for i in range(duration)]

    price_breakdown = []
    total_base_price = 0
    total_extra_adults_cost = 0
    total_children_cost = 0

    extra_adults = max(0, adults - room_type.base_capacity)

    for single_date in date_range:
        # از تابع کمکی جدید برای گرفتن قیمت هر شب استفاده می‌کنیم
        base_price, extra_person_price, child_price = _get_daily_price_for_user(room_type, single_date, user)

        price_breakdown.append({"date": single_date.strftime("%Y-%m-%d"), "price": base_price})
        total_base_price += base_price
        total_extra_adults_cost += extra_adults * extra_person_price
        total_children_cost += children * child_price

    total_price = total_base_price + total_extra_adults_cost + total_children_cost

    return {
        "room_name": room_type.name,
        "hotel_name": room_type.hotel.name,
        "price_breakdown": price_breakdown,
        "extra_adults_cost": total_extra_adults_cost,
        "children_cost": total_children_cost,
        "total_price": total_price,
    }