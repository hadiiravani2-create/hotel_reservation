# services/urls.py
# version: 1.0.0
# Initial creation of URL patterns for the services module.

from django.urls import path
from .views import HotelServiceListAPIView

app_name = 'services'

urlpatterns = [
    # URL to get the list of available services for a specific hotel
    # e.g., /api/services/hotel/123/
    path('hotel/<int:hotel_id>/', HotelServiceListAPIView.as_view(), name='hotel-service-list'),
]
