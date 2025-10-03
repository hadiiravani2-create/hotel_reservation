# hadiiravani2-create/hotel_reservation/hotel_reservation-ad5e9db0ffd7b2bcb0d9a71d3e529d79333b2de0/hotels/views.py
# v1.0.2
# hotels/views.py

from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import (
    City, Hotel, Amenity, RoomType, BoardType,
    TouristAttraction, HotelCategory, BedType, RoomCategory
)
from .serializers import (
    CitySerializer, HotelSerializer, AmenitySerializer,
    RoomTypeSerializer, TouristAttractionSerializer,
    HotelCategorySerializer, BedTypeSerializer, RoomCategorySerializer
)
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

# --- API Views required by hotels/urls.py ---

class CityListAPIView(generics.ListAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer

class AmenityListAPIView(generics.ListAPIView):
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer

class HotelListAPIView(generics.ListAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer

class HotelDetailAPIView(generics.RetrieveAPIView):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    lookup_field = 'hotel_id' # Corresponds to <int:hotel_id> in URL

class RoomTypeListAPIView(generics.ListAPIView):
    serializer_class = RoomTypeSerializer
    def get_queryset(self):
        hotel_id = self.kwargs['hotel_id']
        return RoomType.objects.filter(hotel_id=hotel_id)

class RoomTypeDetailAPIView(generics.RetrieveAPIView):
    queryset = RoomType.objects.all()
    serializer_class = RoomTypeSerializer
    lookup_field = 'room_type_id' # Corresponds to <int:room_type_id> in URL


# --- Existing ViewSets (can be used for full CRUD with routers) ---

class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    lookup_field = 'slug'
    
class TouristAttractionViewSet(viewsets.ModelViewSet):
    queryset = TouristAttraction.objects.all()
    serializer_class = TouristAttractionSerializer
    
class HotelCategoryViewSet(viewsets.ModelViewSet):
    queryset = HotelCategory.objects.all()
    serializer_class = HotelCategorySerializer
    lookup_field = 'slug'

class BedTypeViewSet(viewsets.ModelViewSet):
    queryset = BedType.objects.all()
    serializer_class = BedTypeSerializer
    lookup_field = 'slug'

class RoomCategoryViewSet(viewsets.ModelViewSet):
    queryset = RoomCategory.objects.all()
    serializer_class = RoomCategorySerializer
    lookup_field = 'slug'


class HotelViewSet(viewsets.ModelViewSet):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    lookup_field = 'slug'

class AmenityViewSet(viewsets.ModelViewSet):
    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer

class RoomTypeViewSet(viewsets.ModelViewSet):
    queryset = RoomType.objects.all()
    serializer_class = RoomTypeSerializer
    
@api_view(['GET'])
def get_rooms_by_hotel_slug(request, hotel_slug):
    hotel = get_object_or_404(Hotel, slug=hotel_slug)
    rooms = RoomType.objects.filter(hotel=hotel)
    serializer = RoomTypeSerializer(rooms, many=True)
    return Response(serializer.data)
