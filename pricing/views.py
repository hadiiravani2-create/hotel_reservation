# pricing/views.py

from django.http import JsonResponse
from hotels.models import RoomType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from jdatetime import datetime as jdatetime
from .selectors import find_available_rooms
from .serializers import RoomSearchResultSerializer
from .selectors import calculate_booking_price
from .serializers import PriceQuoteInputSerializer, PriceQuoteOutputSerializer

def get_rooms_for_hotel(request, hotel_id):
    # اتاقهای مربوط به هتل درخواست شده را فیلتر میکنیم
    rooms = RoomType.objects.filter(hotel_id=hotel_id).order_by('name')
    # لیست اتاقها را به فرمت مناسب برای پاسخ JSON تبدیل میکنیم
    room_list = list(rooms.values('id', 'name'))
    return JsonResponse(room_list, safe=False)


class RoomSearchAPIView(APIView):
    def get(self, request):
        # ۱. دریافت و اعتبارسنجی پارامترهای ورودی از URL
        city_id = request.query_params.get('city_id')
        check_in_str = request.query_params.get('check_in')
        check_out_str = request.query_params.get('check_out')
        adults = request.query_params.get('adults', 1) # مقدار پیشفرض ۱ نفر

        if not all([city_id, check_in_str, check_out_str]):
            return Response(
                {"error": "پارامترهای city_id, check_in و check_out الزامی هستند."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # تبدیل رشته تاریخ شمسی (مثلاً '1404-06-02') به آبجکت تاریخ
            check_in = jdatetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = jdatetime.strptime(check_out_str, '%Y-%m-%d').date()
            adults = int(adults)
            city_id = int(city_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "فرمت پارامترها نامعتبر است. فرمت تاریخ باید YYYY-MM-DD باشد."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ۲. فراخوانی تابع اصلی جستجو که در مرحله قبل ساختیم
        available_rooms = find_available_rooms(
            city_id=city_id,
            check_in_date=check_in,
            check_out_date=check_out,
            adults=adults,
            children=0  # فعلا کودک را صفر در نظر میگیریم
        )

        # ۳. استفاده از سریالایزر برای فرمتدهی خروجی
        serializer = RoomSearchResultSerializer(available_rooms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        

class PriceQuoteAPIView(APIView):
    def post(self, request):
        input_serializer = PriceQuoteInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = input_serializer.validated_data
        try:
            check_in = jdatetime.strptime(data['check_in'], '%Y-%m-%d').date()
            check_out = jdatetime.strptime(data['check_out'], '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "فرمت تاریخ نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        price_details = calculate_booking_price(
            room_type_id=data['room_type_id'],
            check_in_date=check_in,
            check_out_date=check_out,
            adults=data['adults'],
            children=data['children']
        )

        output_serializer = PriceQuoteOutputSerializer(price_details)
        return Response(output_serializer.data, status=status.HTTP_200_OK)