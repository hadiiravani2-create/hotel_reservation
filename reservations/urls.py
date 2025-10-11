# reservations/urls.py
# version: 1.0.2
# FIX: Added BookingDetailAPIView to explicit imports and removed the invalid 'views.' prefix to resolve NameError.

from django.urls import path
# CRITICAL FIX: Added BookingDetailAPIView to explicit imports
from .views import CreateBookingAPIView, MyBookingsAPIView, BookingRequestAPIView, InitiatePaymentAPIView, VerifyPaymentAPIView, BookingDetailAPIView 
from rest_framework import routers # Note: routers import seems unused, but maintained for structural integrity.

app_name = 'reservations'

urlpatterns = [
    path('bookings/', CreateBookingAPIView.as_view(), name='create-booking'),
    path('my-bookings/', MyBookingsAPIView.as_view(), name='my-bookings'),
    path('booking-request/', BookingRequestAPIView.as_view(), name='booking-request'),
    path('initiate-payment/', InitiatePaymentAPIView.as_view(), name='initiate-payment'),
    path('verify-payment/', VerifyPaymentAPIView.as_view(), name='verify-payment'),
    # FIX: Removed 'views.' prefix
    path('bookings/<str:booking_code>/details/', BookingDetailAPIView.as_view(), name='booking-details'),
]
