# reservations/views.py v1
# Update: Implemented and activated the CreateBookingAPIView for user-facing bookings.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.db import transaction
from jdatetime import datetime as jdatetime
from decimal import Decimal

# --- Use the renamed and corrected serializer ---
from .serializers import CreateBookingAPISerializer, BookingListSerializer 
from pricing.selectors import calculate_booking_price
from hotels.models import RoomType, BoardType
from .models import Booking, Guest, BookingRoom
from agencies.models import Agency, AgencyTransaction
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
import requests

class CreateBookingAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CreateBookingAPISerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        user = request.user
        agency = None

        # Check for agency booking
        if validated_data.get('agency_id'):
            try:
                # Ensure the user is associated with the agency they are booking for
                agency = Agency.objects.get(id=validated_data['agency_id'], users=user)
            except Agency.DoesNotExist:
                return Response({"error": "آژانس مشخص شده معتبر نیست یا شما به آن دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)

        try:
            check_in_date = jdatetime.strptime(validated_data['check_in'], '%Y-%m-%d').date()
            check_out_date = jdatetime.strptime(validated_data['check_out'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return Response({"error": "فرمت تاریخ نامعتبر است. باید YYYY-MM-DD باشد."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Create the main Booking instance
        booking = Booking.objects.create(
            user=user,
            agency=agency,
            check_in=check_in_date,
            check_out=check_out_date,
            status='pending' # Default status
        )

        total_price = Decimal(0)

        # 2. Loop through rooms, calculate price, and create BookingRoom instances
        for room_data in validated_data['booking_rooms']:
            price_details = calculate_booking_price(
                room_type_id=room_data['room_type_id'],
                board_type_id=room_data['board_type_id'],
                check_in_date=check_in_date,
                check_out_date=check_out_date,
                extra_adults=room_data['adults'],
                children=room_data['children'],
                user=user # Pass user for agency-specific pricing in the future
            )

            if price_details is None:
                # This would mean pricing is not available for a given day
                raise serializers.ValidationError(f"قیمت برای اتاق با شناسه {room_data['room_type_id']} در تاریخ‌های انتخابی یافت نشد.")

            total_price += price_details['total_price'] * room_data['quantity']

            BookingRoom.objects.create(
                booking=booking,
                room_type_id=room_data['room_type_id'],
                board_type_id=room_data['board_type_id'],
                quantity=room_data['quantity'],
                adults=room_data['adults'],
                children=room_data['children']
            )

        # 3. Create Guest instances
        for guest_data in validated_data['guests']:
            Guest.objects.create(booking=booking, **guest_data)

        # 4. Finalize total price and save the booking
        booking.total_price = total_price
        booking.save()
        
        # Here you might initiate payment based on `payment_method`
        # For now, we return the booking code
        
        return Response(
            {"success": True, "booking_code": booking.booking_code, "total_price": booking.total_price},
            status=status.HTTP_201_CREATED
        )


class MyBookingsAPIView(generics.ListAPIView):
    serializer_class = BookingListSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Check if the user is linked to an agency via AgencyUser model
        agency_user = user.agency_profiles.first()
        if agency_user and agency_user.agency:
            return Booking.objects.filter(agency=agency_user.agency)
        return Booking.objects.filter(user=user, agency__isnull=True) # Only show personal bookings

# ... (Rest of the file remains unchanged) ...
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
            # This transaction should only be for agency credit payments, not online payments
            # Logic needs refinement based on payment method
            if booking.agency:
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
