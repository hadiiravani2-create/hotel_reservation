# pricing/selectors.py

from datetime import timedelta
from hotels.models import Hotel, RoomType
from .models import Availability, Price
from hotels.models import RoomType
from django.shortcuts import get_object_or_404
from jdatetime import date as jdate


def find_available_rooms(city_id: int, check_in_date, check_out_date, adults: int, children: int):
    """
    موتور جستجوی اصلی برای پیدا کردن اتاق‌های موجود.
    """
    # محاسبه تعداد شب‌های اقامت
    duration = (check_out_date - check_in_date).days
    if duration <= 0:
        return []

    # ایجاد لیست تاریخ‌های مورد نیاز برای اقامت
    date_range = [check_in_date + timedelta(days=i) for i in range(duration)]

    # ۱. پیدا کردن تمام اتاق‌های شهر مورد نظر که ظرفیت کافی دارند
    room_types = RoomType.objects.filter(
        hotel__city_id=city_id,
        base_capacity__gte=adults # فعلاً ظرفیت پایه را در نظر می‌گیریم
        # در آینده می‌توان منطق نفر اضافه و کودک را پیچیده‌تر کرد
    ).prefetch_related('hotel')

    available_rooms_with_price = []

    # ۲. بررسی موجودی و قیمت برای هر اتاق
    for room in room_types:
        is_available_for_all_nights = True
        total_price = 0

        # اطلاعات موجودی و قیمت را برای کل بازه یکجا از دیتابیس می‌خوانیم
        availabilities = {a.date.strftime("%Y-%m-%d"): a.quantity for a in Availability.objects.filter(room_type=room, date__in=date_range)}
        prices = {p.date.strftime("%Y-%m-%d"): p for p in Price.objects.filter(room_type=room, date__in=date_range)}

        for single_date in date_range:
            date_str = single_date.strftime("%Y-%m-%d")

            # ۳. بررسی موجودی برای آن شب
            if availabilities.get(date_str, 0) < 1:
                is_available_for_all_nights = False
                break  # اگر یک شب هم موجودی نبود، این اتاق در دسترس نیست

            # ۴. محاسبه قیمت برای آن شب
            daily_price_obj = prices.get(date_str)
            if daily_price_obj:
                # اگر قیمت روزانه تعریف شده بود، از آن استفاده کن
                total_price += daily_price_obj.price_per_night
                # منطق قیمت نفر اضافه و کودک را هم می‌توان اینجا اضافه کرد
            else:
                # در غیر این صورت، از قیمت پیش‌فرض خود اتاق استفاده کن
                total_price += room.price_per_night

        # ۵. اگر اتاق برای تمام شب‌ها موجود بود، آن را به لیست نتایج اضافه کن
        if is_available_for_all_nights:
            available_rooms_with_price.append({
                'room_id': room.id,
                'room_name': room.name,
                'hotel_id': room.hotel.id,
                'hotel_name': room.hotel.name,
                'total_price': total_price,
                'price_per_night_avg': total_price / duration,
            })

    return available_rooms_with_price
    
    
def calculate_booking_price(room_type_id: int, check_in_date, check_out_date, adults: int, children: int):
    room_type = get_object_or_404(RoomType, id=room_type_id)
    duration = (check_out_date - check_in_date).days
    date_range = [check_in_date + timedelta(days=i) for i in range(duration)]

    prices_db = {p.date: p for p in Price.objects.filter(room_type=room_type, date__in=date_range)}

    price_breakdown = []
    total_base_price = 0
    total_extra_adults_cost = 0
    total_children_cost = 0

    # محاسبه تعداد نفرات اضافه
    extra_adults = max(0, adults - room_type.base_capacity)

    for single_date in date_range:
        daily_price_obj = prices_db.get(single_date)

        if daily_price_obj:
            base_price = daily_price_obj.price_per_night
            extra_person_price = daily_price_obj.extra_person_price
            child_price = daily_price_obj.child_price
        else:
            # استفاده از قیمت پیش‌فرض اتاق
            base_price = room_type.price_per_night
            extra_person_price = room_type.extra_person_price
            child_price = room_type.child_price

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