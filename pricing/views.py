# pricing/views.py

from django.http import JsonResponse
from hotels.models import RoomType

def get_rooms_for_hotel(request, hotel_id):
    # اتاق‌های مربوط به هتل درخواست شده را فیلتر می‌کنیم
    rooms = RoomType.objects.filter(hotel_id=hotel_id).order_by('name')
    # لیست اتاق‌ها را به فرمت مناسب برای پاسخ JSON تبدیل می‌کنیم
    room_list = list(rooms.values('id', 'name'))
    return JsonResponse(room_list, safe=False)