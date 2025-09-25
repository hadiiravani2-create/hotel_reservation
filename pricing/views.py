# pricing/views.py
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from jdatetime import datetime as jdatetime

from hotels.models import RoomType
from .selectors import find_available_rooms, calculate_booking_price
from .serializers import RoomSearchResultSerializer, PriceQuoteInputSerializer, PriceQuoteOutputSerializer

# ایمپورت‌های جدید برای View محاسبه قیمت چند اتاقه
from reservations.serializers import PriceQuoteMultiRoomInputSerializer 
from core.models import CustomUser

def get_rooms_for_hotel(request, hotel_id):
    rooms = RoomType.objects.filter(hotel_id=hotel_id).order_by('name')
    room_list = list(rooms.values('id', 'name'))
    return JsonResponse(room_list, safe=False)

class RoomSearchAPIView(APIView):
    authentication_classes = []
    permission_classes = []

     
    def get(self, request):
       city_id = request.query_params.get('city_id')
       check_in_str = request.query_params.get('check_in')
       check_out_str = request.query_params.get('check_out')
       adults = request.query_params.get('adults', 1)
       children = request.query_params.get('children', 0)
       
       # اضافه کردن پارامترهای فیلتر جدید
       min_price = request.query_params.get('min_price')
       max_price = request.query_params.get('max_price')
       stars = request.query_params.get('stars')
       amenities = request.query_params.get('amenities')
       hotel_category = request.query_params.get('hotel_category')
       room_category = request.query_params.get('room_category')

       if not all([city_id, check_in_str, check_out_str]):
           return Response({"error": "پارامترهای city_id, check_in و check_out الزامی هستند."}, status=status.HTTP_400_BAD_REQUEST)
           
       try:
           check_in = jdatetime.strptime(check_in_str, '%Y-%m-%d').date()
           check_out = jdatetime.strptime(check_out_str, '%Y-%m-%d').date()
           adults = int(adults)
           children = int(children)
           city_id = int(city_id)
           
           # تبدیل پارامترهای جدید به نوع داده مناسب
           min_price = int(min_price) if min_price else None
           max_price = int(max_price) if max_price else None
           stars = int(stars) if stars else None
           amenities = [int(a) for a in amenities.split(',')] if amenities else None
           hotel_category = int(hotel_category) if hotel_category else None
           room_category = int(room_category) if room_category else None
           
       except (ValueError, TypeError):
           return Response({"error": "فرمت پارامترها نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

       # توجه: تابع find_available_rooms از منطق قدیمی adults و children استفاده می‌کند 
       # و باید با منطق جدید تطبیق داده شود اگر قرار است در این مرحله فیلتر ظرفیت انجام شود.
       available_rooms = find_available_rooms(
           city_id=city_id, check_in_date=check_in, check_out_date=check_out,
           adults=adults, children=children, user=request.user
       )

       # فیلتر نهایی بر اساس پارامترهای قیمت و دسته‌بندی
       if min_price is not None:
           available_rooms = [room for room in available_rooms if any(opt['total_price'] >= min_price for opt in room['board_options'])]
       if max_price is not None:
           available_rooms = [room for room in available_rooms if any(opt['total_price'] <= max_price for opt in room['board_options'])]
       if stars is not None:
           # این فیلتر به دلیل عدم وجود hotel_stars در ساختار results، احتمالا کار نمی‌کند.
           pass 
       if amenities is not None:
           # این بخش نیاز به تغییر در سلکتور برای برگرداندن amenities دارد
           pass
       
       serializer = RoomSearchResultSerializer(available_rooms, many=True)
       return Response(serializer.data)

class PriceQuoteAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = PriceQuoteInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        data = serializer.validated_data
        try:
            check_in = jdatetime.strptime(data['check_in'], '%Y-%m-%d').date()
            check_out = jdatetime.strptime(data['check_out'], '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "فرمت تاریخ نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
        
        # توجه: این تماس از منطق قدیمی adults/children استفاده می‌کند.
        price_details = calculate_booking_price(
            room_type_id=data['room_type_id'],
            board_type_id=data['board_type_id'],
            check_in_date=check_in, check_out_date=check_out,
            extra_adults=data['adults'], children=data['children'], user=request.user # نام پارامترها در selector تغییر کرده است
        )

        if price_details is None:
            return Response({"error": "قیمت برای تمام روزهای انتخابی یافت نشد یا سرویس در این تاریخ ارائه نمی‌شود."}, status=status.HTTP_400_BAD_REQUEST)
            
        output_serializer = PriceQuoteOutputSerializer(price_details)
        return Response(output_serializer.data)


class PriceQuoteMultiRoomAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = PriceQuoteMultiRoomInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        data = serializer.validated_data
        
        try:
            check_in = jdatetime.strptime(data['check_in'], '%Y-%m-%d').date()
            check_out = jdatetime.strptime(data['check_out'], '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "فرمت تاریخ نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        # شبیه‌سازی کاربر آژانسی برای اعمال قوانین قیمت‌گذاری
        user = request.user 
        if data.get('user_id'):
            try:
                user = CustomUser.objects.get(id=data['user_id'])
            except CustomUser.DoesNotExist:
                 return Response({"error": "کاربر مورد نظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        total_final_price = 0
        
        # محاسبه قیمت کل
        for room_data in data['booking_rooms']:
            price_details = calculate_booking_price(
                room_type_id=room_data['room_type_id'],
                board_type_id=room_data['board_type_id'],
                check_in_date=check_in, 
                check_out_date=check_out, 
                # ارسال مستقیم تعداد نفرات اضافی و کودکان
                extra_adults=room_data['extra_adults'],
                children=room_data['children_count'], 
                user=user
            )
            if price_details is None:
                return Response({"error": "قیمت برای تمام روزهای انتخابی یا سرویس یافت نشد. (اتاق ناموجود یا بدون قیمت است)"}, status=status.HTTP_400_BAD_REQUEST)
            
            # قیمت کل هر اتاق * تعداد اتاق از آن نوع
            total_final_price += price_details['total_price'] * room_data['quantity']

        return Response({"total_price": total_final_price}, status=status.HTTP_200_OK)
