# reservations/urls.py

from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    # آدرس برای ایجاد یک رزرو جدید
    path('api/create/', views.CreateBookingAPIView.as_view(), name='create_booking_api'),
    # آدرس برای مشاهده لیست رزروهای کاربر
    path('api/my-bookings/', views.MyBookingsAPIView.as_view(), name='my_bookings_api'),
]