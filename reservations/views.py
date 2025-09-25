
# reservations/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.db import transaction
from jdatetime import datetime as jdatetime
from .serializers import CreateBookingSerializer, BookingListSerializer
from pricing.selectors import calculate_booking_price
from hotels.models import RoomType, BoardType
from .models import Booking, Guest, BookingRoom
from agencies.models import Contract, AgencyTransaction
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
import requests

class CreateBookingAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        # NOTE: این تابع نیاز به بازبینی منطق رزرو API دارد زیرا مدل Booking و BookingRoom تغییر کرده است.
        return Response({"error": "این تابع نیاز به بازبینی منطق رزرو API دارد زیرا مدل Booking و BookingRoom تغییر کرده است."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyBookingsAPIView(generics.ListAPIView):
    serializer_class = BookingListSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if hasattr(self.request.user, 'agency') and self.request.user.agency:
            return Booking.objects.filter(agency=self.request.user.agency)
        return Booking.objects.filter(user=self.request.user)


class BookingRequestAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        booking_code = request.data.get('booking_code')
        request_type = request.data.get('request_type')
        
        if not booking_code or request_type not in ['cancellation', 'modification']:
            return Response({"error": "کد رزرو و نوع درخواست (cancellation/modification) الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(booking_code=booking_code)
        except Booking.DoesNotExist:
            return Response({"error": "رزرو مورد نظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        if not (booking.user == request.user or (hasattr(request.user, 'agency') and booking.agency == request.user.agency)):
            return Response({"error": "شما مجوز انجام این درخواست را ندارید."}, status=status.HTTP_403_FORBIDDEN)
        
        if request_type == 'cancellation':
            booking.status = 'cancellation_requested'
            booking.save()
            return Response({"success": True, "message": "درخواست لغو رزرو با موفقیت ثبت شد."}, status=status.HTTP_200_OK)

        elif request_type == 'modification':
            booking.status = 'modification_requested'
            booking.save()
            return Response({"success": True, "message": "درخواست ویرایش رزرو با موفقیت ثبت شد."}, status=status.HTTP_200_OK)


class InitiatePaymentAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        booking_code = request.data.get('booking_code')
        try:
            booking = Booking.objects.get(booking_code=booking_code, status='pending')
        except Booking.DoesNotExist:
            return Response({"error": "رزرو مورد نظر یافت نشد یا در وضعیت 'در انتظار پرداخت' نیست."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "success": True,
            "message": "API پرداخت آماده است، اما اتصال به درگاه بانکی باید پیاده‌سازی شود.",
            "redirect_url": "http://example.com/payment-gateway-simulated"
        })

class VerifyPaymentAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        status_code = request.data.get('status')
        booking_code = request.data.get('booking_code')
        
        try:
            booking = Booking.objects.get(booking_code=booking_code)
        except Booking.DoesNotExist:
            return Response({"error": "رزرو مورد نظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        if status_code == 'success':
            booking.status = 'confirmed'
            booking.save()
            AgencyTransaction.objects.create(
                agency=booking.agency,
                booking=booking, 
                amount=booking.total_price, 
                transaction_type='payment',
                description=f"پرداخت آنلاین رزرو کد {booking.booking_code}"
            )
            return Response({"success": True, "message": "پرداخت با موفقیت انجام شد و رزرو شما تایید گردید."}, status=status.HTTP_200_OK)
        else:
            booking.status = 'cancelled'
            booking.save()
            return Response({"success": False, "message": "پرداخت ناموفق بود. رزرو لغو شد."}, status=status.HTTP_400_BAD_REQUEST)
