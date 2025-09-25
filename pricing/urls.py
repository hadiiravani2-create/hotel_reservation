# pricing/urls.py

from django.urls import path
from . import views

app_name = 'pricing'

urlpatterns = [
    # این آدرس برای دریافت لیست اتاقهای یک هتل استفاده میشود
    path('api/get-rooms/<int:hotel_id>/', views.get_rooms_for_hotel, name='get_rooms_for_hotel'),

    # URL برای جستجوی عمومی
    path('api/search/', views.RoomSearchAPIView.as_view(), name='room_search_api'),
    # محاسبه قیمت اتاق (قبلی)
    path('api/calculate-price/', views.PriceQuoteAPIView.as_view(), name='price_quote_api'),
    # URL جدید برای محاسبه قیمت رزرو گروهی از پنل ادمین
    path('api/calculate-multi-price/', views.PriceQuoteMultiRoomAPIView.as_view(), name='price_quote_multi_api'),
]
