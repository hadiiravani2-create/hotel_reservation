# hotels/urls.py
# version: 1.0.4
# REFACTOR: Removed all prefixes (api/, hotels/) as they are now handled in the root URLconf.

from django.urls import path
from . import views

app_name = 'hotels'

urlpatterns = [
    # Paths are now relative to /api/hotels/
    path('cities/', views.CityListAPIView.as_view(), name='city-list'),
    path('amenities/', views.AmenityListAPIView.as_view(), name='amenity-list'),
    path('suggested/', views.SuggestedHotelListAPIView.as_view(), name='suggested-hotel-list'),
    path('board-types/', views.BoardTypeListAPIView.as_view(), name='board-type-list'),
    path('<int:hotel_id>/rooms/', views.RoomTypeListAPIView.as_view(), name='room-type-list'),
    path('<int:pk>/', views.HotelDetailPKView.as_view(), name='hotel-detail-pk'),
    path('<slug:slug>/', views.HotelViewSet.as_view({'get': 'retrieve'}), name='hotel-detail'),
    path('<int:hotel_id>/rooms/', views.RoomTypeListAPIView.as_view(), name='room-type-list'),
    
    # Kept the generic list view for hotels if needed, though it's less common with slug-based details
    path('', views.HotelListAPIView.as_view(), name='hotel-list'), 
]
