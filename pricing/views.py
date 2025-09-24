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

       if not all([city_id, check_in_str, check_out_str]):
           return Response({"error": "پارامترهای city_id, check_in و check_out الزامی هستند."}, status=status.HTTP_400_BAD_REQUEST)
           
       try:
           check_in = jdatetime.strptime(check_in_str, '%Y-%m-%d').date()
           check_out = jdatetime.strptime(check_out_str, '%Y-%m-%d').date()
           adults = int(adults)
           children = int(children)
           city_id = int(city_id)
       except (ValueError, TypeError):
           return Response({"error": "فرمت پارامترها نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

       available_rooms = find_available_rooms(
           city_id=city_id, check_in_date=check_in, check_out_date=check_out,
           adults=adults, children=children, user=request.user
       )
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

        price_details = calculate_booking_price(
            room_type_id=data['room_type_id'],
            board_type_id=data['board_type_id'],
            check_in_date=check_in, check_out_date=check_out,
            adults=data['adults'], children=data['children'], user=request.user
        )

        if price_details is None:
            return Response({"error": "قیمت برای تمام روزهای انتخابی یافت نشد یا سرویس در این تاریخ ارائه نمی‌شود."}, status=status.HTTP_400_BAD_REQUEST)
            
        output_serializer = PriceQuoteOutputSerializer(price_details)
        return Response(output_serializer.data)
    
   
