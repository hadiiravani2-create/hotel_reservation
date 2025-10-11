# pricing/views.py
# version: 1.1.1
# FIX: Corrected argument passing to calculate_multi_booking_price in PriceQuoteAPIView and PriceQuoteMultiRoomAPIView 
#      to match the new multi-room selector signature (booking_rooms list format), resolving the TypeError.

from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from jdatetime import datetime as jdatetime, timedelta

from hotels.models import RoomType
from .selectors import find_available_hotels, calculate_multi_booking_price 
from .serializers import HotelSearchResultSerializer, PriceQuoteInputSerializer, PriceQuoteOutputSerializer 
from reservations.serializers import PriceQuoteMultiRoomInputSerializer 
from core.models import CustomUser

def get_rooms_for_hotel(request, hotel_id):
    # ... (Omitted)
    rooms = RoomType.objects.filter(hotel_id=hotel_id).order_by('name')
    room_list = list(rooms.values('id', 'name'))
    return JsonResponse(room_list, safe=False)

class HotelSearchAPIView(APIView):
    authentication_classes = []
    permission_classes = []
     
    def get(self, request):
       # ... (Omitted)
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
        
        # Prepare single room data to match the multi-room selector format
        single_room_data = {
            'room_type_id': data['room_type_id'],
            'board_type_id': data['board_type_id'],
            # NOTE: PriceQuoteInputSerializer uses 'adults' and 'children' at root, mapping to selector's internal keys
            'adults': data.get('adults', 0), 
            'children': data.get('children', 0), 
            'quantity': 1 # Assuming 1 room for a single quote
        }

        # Call the multi-room selector (now the only pricing function)
        price_data = calculate_multi_booking_price( 
            [single_room_data], # Pass list of one room
            check_in, check_out,
            user=request.user
        )

        if price_data is None or 'total_price' not in price_data:
            return Response({"error": "قیمت برای تمام روزهای انتخابی یافت نشد."}, status=status.HTTP_400_BAD_REQUEST)
        
        # NOTE: Returning only total_price for consistency with the simplified multi-room selector output
        return Response({"total_price": price_data['total_price']}, status=status.HTTP_200_OK)


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
                # Use CustomUser model imported from core
                user = CustomUser.objects.get(id=data['user_id']) 
            except CustomUser.DoesNotExist:
                 return Response({"error": "کاربر مورد نظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        
        # CORRECT CALL: Call the multi-room selector ONCE with the entire list of rooms.
        # This replaces the entire problematic loop in the original code.
        price_data = calculate_multi_booking_price(
            data['booking_rooms'], # Pass the list of rooms directly
            check_in, 
            check_out, 
            user # Pass the determined user
        )

        if price_data is None or 'total_price' not in price_data:
            return Response({"error": "قیمت برای اتاق‌های مورد نظر یافت نشد."}, status=status.HTTP_400_BAD_REQUEST)

        total_final_price = price_data['total_price']

        return Response({"total_price": total_final_price}, status=status.HTTP_200_OK)
