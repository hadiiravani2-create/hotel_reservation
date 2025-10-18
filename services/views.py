# In services/views.py (and register the URL in services/urls.py)
from rest_framework import generics
from .models import HotelService
from .serializers import HotelServiceSerializer

class HotelServiceListAPIView(generics.ListAPIView):
    serializer_class = HotelServiceSerializer

    def get_queryset(self):
        hotel_id = self.kwargs.get('hotel_id')
        return HotelService.objects.filter(hotel_id=hotel_id)
