# pricing/urls.py

from django.urls import path
from . import views

app_name = 'pricing'

urlpatterns = [
    # این آدرس برای دریافت لیست اتاق‌های یک هتل استفاده می‌شود
    path('api/get-rooms/<int:hotel_id>/', views.get_rooms_for_hotel, name='get_rooms_for_hotel'),
]