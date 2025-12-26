# pricing/urls.py v1.0.1
# Update: Changed the search URL to point to the new HotelSearchAPIView.
from django.urls import path
from . import views

app_name = 'pricing'

urlpatterns = [
    path('api/get-rooms/<int:hotel_id>/', views.get_rooms_for_hotel, name='get_rooms_for_hotel'),

    # URL جستجو اکنون به View جدید اشاره می‌کند
    path('api/search/', views.HotelSearchAPIView.as_view(), name='hotel_search_api'),
    
    path('api/calculate-price/', views.PriceQuoteAPIView.as_view(), name='price_quote_api'),
    path('api/calculate-multi-price/', views.PriceQuoteMultiRoomAPIView.as_view(), name='price_quote_multi_api'),
    path('admin/calendar-pricing/', views.calendar_pricing_view, name='calendar_pricing'),
    path('api/room-calendar/<int:room_id>/', views.get_room_calendar, name='room_calendar_api'),
]
