# reservations/urls.py
# version: 1.1.0
# FIX: Added the URL pattern for the PayWithWalletAPIView to fix the 404 error.
# FEATURE: Added URL for GuestBookingLookupAPIView to allow unregistered users to track confirmed bookings.

from django.urls import path
from .views import (
    CreateBookingAPIView, MyBookingsAPIView, BookingRequestAPIView, InitiatePaymentAPIView, VerifyPaymentAPIView,
    BookingDetailAPIView,
    PayWithWalletAPIView, # <-- View added to imports
    # NEW VIEWS
    OfflineBankListAPIView, PaymentConfirmationAPIView,
    GuestBookingLookupAPIView,
    OperatorBookingConfirmationAPIView,
    CancelBookingAPIView
)
from rest_framework import routers

app_name = 'reservations'

urlpatterns = [
    # Main Booking Flow
    path('bookings/', CreateBookingAPIView.as_view(), name='booking-create'),
    path('bookings/<str:booking_code>/details/', BookingDetailAPIView.as_view(), name='booking-details'),

    # --- FIX: Added path for wallet payment ---
    path('bookings/<str:booking_code>/pay-with-wallet/', PayWithWalletAPIView.as_view(), name='pay-with-wallet'),

    # Guest Tracking Path
    path('guest-lookup/', GuestBookingLookupAPIView.as_view(), name='guest-booking-lookup'),

    # Offline Payment Flow
    path('offline-banks/', OfflineBankListAPIView.as_view(), name='offline-bank-list'),
    path('payment-confirm/', PaymentConfirmationAPIView.as_view(), name='payment-confirmation'),

    # User/Management Actions
    path('my-bookings/', MyBookingsAPIView.as_view(), name='my-bookings'),
    # --- Cancellation URL ---
    path('api/bookings/cancel/', CancelBookingAPIView.as_view(), name='cancel_booking_api'),
    path('booking-request/', BookingRequestAPIView.as_view(), name='booking-request'),

    # Operator Actions
    path('operator/confirm-booking/', OperatorBookingConfirmationAPIView.as_view(), name='operator-booking-confirmation'),

    # Online Payment Gateway Integration Points
    path('initiate-payment/', InitiatePaymentAPIView.as_view(), name='initiate-payment'),
    path('verify-payment/', VerifyPaymentAPIView.as_view(), name='verify-payment'),
]
