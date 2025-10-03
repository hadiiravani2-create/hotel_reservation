# hadiiravani2-create/hotel_reservation/hotel_reservation-ad5e9db0ffd7b2bcb0d9a71d3e529d79333b2de0/hotels/urls.py
# v1.0.1
# hotels/urls.py
from django.urls import path
from . import views  # FIX: Import the entire views module to prevent circular dependency.

app_name = 'hotels'

urlpatterns = [
    # FIX: Reference views via the module namespace (e.g., views.CityListAPIView).
    path('api/cities/', views.CityListAPIView.as_view(), name='city-list'),
    path('api/amenities/', views.AmenityListAPIView.as_view(), name='amenity-list'),
    path('api/hotels/', views.HotelListAPIView.as_view(), name='hotel-list'),
    path('api/hotels/<int:hotel_id>/', views.HotelDetailAPIView.as_view(), name='hotel-detail'),
    path('api/hotels/<int:hotel_id>/rooms/', views.RoomTypeListAPIView.as_view(), name='room-type-list'),
    path('api/room-types/<int:room_type_id>/', views.RoomTypeDetailAPIView.as_view(), name='room-type-detail'),
]
