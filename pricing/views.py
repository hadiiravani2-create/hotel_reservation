# pricing/views.py v1.1.0
# Fix: Renamed calculate_booking_price to calculate_multi_booking_price following renaming in pricing.selectors,
#      to resolve ImportError.

from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from jdatetime import datetime as jdatetime, timedelta

from hotels.models import RoomType
from .selectors import find_available_hotels, calculate_multi_booking_price # <--- FIX: Renamed import
from .serializers import HotelSearchResultSerializer, PriceQuoteInputSerializer, PriceQuoteOutputSerializer 
from reservations.serializers import PriceQuoteMultiRoomInputSerializer 
from core.models import CustomUser

def get_rooms_for_hotel(request, hotel_id):
    rooms = RoomType.objects.filter(hotel_id=hotel_id).order_by('name')
    room_list = list(rooms.values('id', 'name'))
    return JsonResponse(room_list, safe=False)

class HotelSearchAPIView(APIView):
    authentication_classes = []
    permission_classes = []
     
    def get(self, request):
       city_id = request.query_params.get('city_id')
       check_in_str = request.query_params.get('check_in')
       duration_str = request.query_params.get('duration')
       
       min_price = request.query_params.get('min_price')
       max_price = request.query_params.get('max_price')
       stars = request.query_params.get('stars')
       amenities = request.query_params.get('amenities')

       if not all([city_id, check_in_str, duration_str]):
           return Response({"error": "پارامترهای city_id, check_in و duration الزامی هستند."}, status=status.HTTP_400_BAD_REQUEST)
           
       try:
           check_in = jdatetime.strptime(check_in_str, '%Y-%m-%d').date()
           duration = int(duration_str)
           if duration <= 0:
               raise ValueError("Duration must be positive")
           check_out = check_in + timedelta(days=duration)
           
           city_id = int(city_id)
           
       except (ValueError, TypeError):
           return Response({"error": "فرمت پارامترها نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

       available_hotels = find_available_hotels(
           city_id=city_id, check_in_date=check_in, check_out_date=check_out,
           user=request.user
           # سایر فیلترها در آینده می‌توانند اینجا اضافه شوند
       )
       
       serializer = HotelSearchResultSerializer(available_hotels, many=True)
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
        
        price_details = calculate_multi_booking_price( # <--- FIX: Renamed function call
            room_type_id=data['room_type_id'],
            board_type_id=data['board_type_id'],
            check_in_date=check_in, check_out_date=check_out,
            extra_adults=data.get('extra_adults', 0), 
            children=data.get('children', 0), 
            user=request.user
        )

        if price_details is None:
            return Response({"error": "قیمت برای تمام روزهای انتخابی یافت نشد."}, status=status.HTTP_400_BAD_REQUEST)
            
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

        user = request.user 
        if data.get('user_id'):
            try:
                user = CustomUser.objects.get(id=data['user_id'])
            except CustomUser.DoesNotExist:
                 return Response({"error": "کاربر مورد نظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        total_final_price = 0
        
        for room_data in data['booking_rooms']:
            price_details = calculate_multi_booking_price( # <--- FIX: Renamed function call
                room_type_id=room_data['room_type_id'],
                board_type_id=room_data['board_type_id'],
                check_in_date=check_in, 
                check_out_date=check_out, 
                extra_adults=room_data['extra_adults'],
                children=room_data['children_count'], 
                user=user
            )
            if price_details is None:
                return Response({"error": "قیمت برای اتاق مورد نظر یافت نشد."}, status=status.HTTP_400_BAD_REQUEST)
            
            total_final_price += price_details['total_price'] * room_data['quantity']

        return Response({"total_price": total_final_price}, status=status.HTTP_200_OK)
