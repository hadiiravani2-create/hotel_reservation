# pricing/views.py

from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from jdatetime import datetime as jdatetime

from hotels.models import RoomType
from .selectors import find_available_rooms, calculate_booking_price
from .serializers import RoomSearchResultSerializer, PriceQuoteInputSerializer, PriceQuoteOutputSerializer

def get_rooms_for_hotel(request, hotel_id):
    """
    این ویو برای پنل ادمین و پر کردن داینامیک لیست اتاق‌ها استفاده می‌شود.
    """
    rooms = RoomType.objects.filter(hotel_id=hotel_id).order_by('name')
    room_list = list(rooms.values('id', 'name'))
    return JsonResponse(room_list, safe=False)


class RoomSearchAPIView(APIView):
    """
    API عمومی برای جستجوی اتاق‌های موجود.
    این API قیمت‌ها را بر اساس کاربر (عادی یا آژانس) محاسبه می‌کند.
    """
    # این API عمومی است و نیازی به توکن ندارد.
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        # ۱. دریافت و اعتبارسنجی پارامترهای ورودی از URL
        city_id = request.query_params.get('city_id')
        check_in_str = request.query_params.get('check_in')
        check_out_str = request.query_params.get('check_out')
        adults = request.query_params.get('adults', 1)

        if not all([city_id, check_in_str, check_out_str]):
            return Response(
                {"error": "پارامترهای city_id, check_in و check_out الزامی هستند."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            check_in = jdatetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = jdatetime.strptime(check_out_str, '%Y-%m-%d').date()
            adults = int(adults)
            city_id = int(city_id)
        except (ValueError, TypeError):
            return Response(
                {"error": "فرمت پارامترها نامعتبر است. فرمت تاریخ باید YYYY-MM-DD باشد."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ۲. فراخوانی تابع اصلی جستجو با پاس دادن request.user
        available_rooms = find_available_rooms(
            city_id=city_id,
            check_in_date=check_in,
            check_out_date=check_out,
            adults=adults,
            children=0,
            user=request.user # کاربر برای بررسی قراردادها ارسال می‌شود
        )

        # ۳. استفاده از سریالایزر برای فرمت‌دهی خروجی
        serializer = RoomSearchResultSerializer(available_rooms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PriceQuoteAPIView(APIView):
    """
    API برای محاسبه قیمت نهایی یک رزرو خاص قبل از ثبت نهایی.
    این API نیز قیمت‌ها را بر اساس نوع کاربر محاسبه می‌کند.
    """
    # این API هم می‌تواند عمومی باشد و نیازی به توکن ندارد.
    authentication_classes = []
    permission_classes = []

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
            children=data['children'],
            user=request.user # کاربر برای بررسی قراردادها ارسال می‌شود
        )
        
        output_serializer = PriceQuoteOutputSerializer(price_details)
        return Response(output_serializer.data, status=status.HTTP_200_OK)