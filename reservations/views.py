# reservations/views.py v2.0.2
# FIX: Replaced calculate_booking_price with calculate_multi_booking_price for proper price calculation.
# Feature: Added extra_requests saving to BookingRoom creation.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.db import transaction
from jdatetime import datetime as jdatetime, timedelta
from decimal import Decimal
from collections import defaultdict
from django.core.exceptions import ValidationError

# --- ایمپورت‌های مربوط به ratelimit حذف شد ---
from .serializers import CreateBookingAPISerializer, BookingListSerializer
from pricing.selectors import calculate_multi_booking_price
from hotels.models import RoomType, BoardType
from pricing.models import Availability
from .models import Booking, Guest, BookingRoom
from agencies.models import Agency, AgencyTransaction, AgencyUser
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator


class CreateBookingAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # --- دکوریتور ratelimit حذف شد ---
    @transaction.atomic
    def post(self, request):
        serializer = CreateBookingAPISerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        user = request.user
        agency = None

        if validated_data.get('agency_id'):
            try:
                agency = Agency.objects.get(id=validated_data['agency_id'])
                if not AgencyUser.objects.filter(user=user, agency=agency).exists():
                    # If agency_id is provided, ensure the user is an authorized user of that agency.
                    raise Agency.DoesNotExist
            except Agency.DoesNotExist:
                return Response({"error": "آژانس مشخص شده معتبر نیست یا شما به آن دسترسی ندارید."}, status=status.HTTP_403_FORBIDDEN)

        try:
            check_in = jdatetime.strptime(validated_data['check_in'], '%Y-%m-%d').date()
            check_out = jdatetime.strptime(validated_data['check_out'], '%Y-%m-%d').date()
            duration = (check_out - check_in).days
            if duration <= 0:
                raise ValueError("تاریخ خروج باید بعد از تاریخ ورود باشد.")
            date_range = [check_in + timedelta(days=i) for i in range(duration)]
        except (ValueError, TypeError):
            return Response({"error": "فرمت تاریخ نامعتبر است یا بازه زمانی اشتباه است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            availability_requirements = defaultdict(int)
            for room_data in validated_data['booking_rooms']:
                for date in date_range:
                    # Sum up required quantity for each room type on each date
                    availability_requirements[(room_data['room_type_id'], date)] += room_data['quantity']
            
            # Lock the availability rows for update
            availabilities_to_lock = Availability.objects.select_for_update().filter(
                room_type_id__in=[k[0] for k in availability_requirements.keys()],
                date__in=[k[1] for k in availability_requirements.keys()]
            )
            
            availability_map = {(a.room_type_id, a.date): a for a in availabilities_to_lock}

            # Check and confirm availability
            for (room_type_id, date), required_quantity in availability_requirements.items():
                availability_obj = availability_map.get((room_type_id, date))
                if not availability_obj or availability_obj.quantity < required_quantity:
                    room_name = RoomType.objects.get(id=room_type_id).name
                    raise ValidationError(f"ظرفیت برای اتاق '{room_name}' در تاریخ {date} کافی نیست.")

            # Calculate total price for all rooms in one go (Fixing NameError)
            price_data = calculate_multi_booking_price(
                validated_data['booking_rooms'], 
                check_in, 
                check_out, 
                user
            )
            
            if price_data is None:
                raise ValidationError("خطا در محاسبه قیمت نهایی.")

            total_price = price_data['total_price']

            # Create Booking
            booking = Booking.objects.create(
                user=user,
                agency=agency,
                check_in=check_in,
                check_out=check_out,
                status='pending',
                total_price=total_price # Set total price here
            )
            
            # Create BookingRooms and update availability
            for room_data in validated_data['booking_rooms']:
                # The total price calculation is now handled centrally by calculate_multi_booking_price
                BookingRoom.objects.create(
                    booking=booking, 
                    room_type_id=room_data['room_type_id'],
                    board_type_id=room_data['board_type_id'],
                    quantity=room_data['quantity'],
                    adults=room_data['adults'],
                    children=room_data['children'],
                    extra_requests=room_data.get('extra_requests') # Save extra requests
                )

                for date in date_range:
                    availability_obj = availability_map[(room_data['room_type_id'], date)]
                    availability_obj.quantity -= room_data['quantity']
                    availability_obj.save()

            # Create Guests
            for guest_data in validated_data['guests']:
                Guest.objects.create(booking=booking, **guest_data)
                
        except ValidationError as e:
            # Delete the booking object if it was created before the exception
            if 'booking' in locals():
                booking.delete()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(
            {"success": True, "booking_code": booking.booking_code, "total_price": booking.total_price},
            status=status.HTTP_201_CREATED
        )

# ... (بقیه کلاس‌های View بدون تغییر باقی می‌مانند) ...

class MyBookingsAPIView(generics.ListAPIView):
    serializer_class = BookingListSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        agency_profile = user.agency_profile if hasattr(user, 'agency_profile') else None
        if agency_profile and agency_profile.agency:
            return Booking.objects.filter(agency=agency_profile.agency)
        return Booking.objects.filter(user=user, agency__isnull=True)


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

        agency_profile = request.user.agency_profile if hasattr(request.user, 'agency_profile') else None
        if not (booking.user == request.user or (agency_profile and booking.agency == agency_profile.agency)):
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
            if booking.status != 'pending':
                return Response({"error": "این رزرو قبلا پردازش شده است."}, status=status.HTTP_400_BAD_REQUEST)

            booking.status = 'confirmed'
            booking.save()
            
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
            # We assume a failed payment means cancellation
            booking.status = 'cancelled' 
            booking.save()
            return Response({"success": False, "message": "پرداخت ناموفق بود. رزرو لغو شد."}, status=status.HTTP_400_BAD_REQUEST)
