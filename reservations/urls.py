# reservations/urls.py

from django.urls import path
from .views import CreateBookingAPIView, MyBookingsAPIView, BookingRequestAPIView, InitiatePaymentAPIView, VerifyPaymentAPIView
from rest_framework import routers

app_name = 'reservations'

urlpatterns = [
    path('bookings/', CreateBookingAPIView.as_view(), name='create-booking'),
    path('my-bookings/', MyBookingsAPIView.as_view(), name='my-bookings'),
    path('booking-request/', BookingRequestAPIView.as_view(), name='booking-request'),
    path('initiate-payment/', InitiatePaymentAPIView.as_view(), name='initiate-payment'),
    path('verify-payment/', VerifyPaymentAPIView.as_view(), name='verify-payment'),
]
