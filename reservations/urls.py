# reservations/urls.py
# version: 1.0.3
# Feature: Added URLs for offline payment flow (bank list and confirmation submission).

from django.urls import path
from .views import (
    CreateBookingAPIView, MyBookingsAPIView, BookingRequestAPIView, InitiatePaymentAPIView, VerifyPaymentAPIView, 
    BookingDetailAPIView,
    # NEW VIEWS
    OfflineBankListAPIView, PaymentConfirmationAPIView 
)
from rest_framework import routers

app_name = 'reservations'

urlpatterns = [
    # Main Booking Flow
    path('bookings/', CreateBookingAPIView.as_view(), name='booking-create'),
    path('bookings/<str:booking_code>/details/', BookingDetailAPIView.as_view(), name='booking-details'),
    
    # NEW OFFLINE PAYMENT FLOW
    path('offline-banks/', OfflineBankListAPIView.as_view(), name='offline-bank-list'),
    path('payment-confirm/', PaymentConfirmationAPIView.as_view(), name='payment-confirmation'),

    # User/Management Actions
    path('my-bookings/', MyBookingsAPIView.as_view(), name='my-bookings'),
    path('booking-request/', BookingRequestAPIView.as_view(), name='booking-request'),
    
    # Online Payment Gateway Integration Points
    path('initiate-payment/', InitiatePaymentAPIView.as_view(), name='initiate-payment'),
    path('verify-payment/', VerifyPaymentAPIView.as_view(), name='verify-payment'),
]
