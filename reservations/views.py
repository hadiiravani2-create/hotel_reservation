# reservations/views.py
# version: 2.0.4
# FIX: Restored missing APIView classes (MyBookingsAPIView, BookingRequestAPIView, InitiatePaymentAPIView, VerifyPaymentAPIView) that were omitted in v2.0.3 for brevity, causing ImportError.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.db import transaction
from jdatetime import datetime as jdatetime, timedelta
from decimal import Decimal
from collections import defaultdict
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

# --- Imports ---
from .serializers import CreateBookingAPISerializer, BookingListSerializer
from pricing.selectors import calculate_multi_booking_price
from hotels.models import RoomType, BoardType
from pricing.models import Availability
from .models import Booking, Guest, BookingRoom
from agencies.models import Agency, AgencyTransaction, AgencyUser
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated # ADDED: IsAuthenticated again
from django.utils.decorators import method_decorator

CustomUser = get_user_model()


class CreateBookingAPIView(APIView):
    """API view for creating a booking, supporting both authenticated users and guests."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny] # Allow non-authenticated users (guests) to post

    @transaction.atomic
    def post(self, request):
        serializer = CreateBookingAPISerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        
        # Determine the booking user. Use request.user if authenticated, otherwise None (Guest Booking).
        user = request.user if request.user.is_authenticated else None
        agency = None

        if validated_data.get('agency_id'):
            # Agency booking requires authentication
            if not user:
                 return Response({"error": "برای رزرو آژانسی، ابتدا باید وارد حساب کاربری آژانس شوید."}, status=status.HTTP_403_FORBIDDEN)
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
                raise ValueError("Check-out date must be after check-in date.")
            date_range = [check_in + timedelta(days=i) for i in range(duration)]
        except (ValueError, TypeError):
            return Response({"error": "Invalid date format or date range."}, status=status.HTTP_400_BAD_REQUEST)

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
                    raise ValidationError(f"Availability is insufficient for room '{room_name}' on date {date}.")

            # Calculate total price for all rooms
            price_data = calculate_multi_booking_price(
                validated_data['booking_rooms'], 
                check_in, 
                check_out, 
                user # Pass the determined user (authenticated or None) for pricing calculation
            )
            
            if price_data is None:
                raise ValidationError("Error calculating final price.")

            total_price = price_data['total_price']

            # Create Booking
            booking = Booking.objects.create(
                user=user, # Set to authenticated user or None
                agency=agency,
                check_in=check_in,
                check_out=check_out,
                status='pending',
                total_price=total_price 
            )
            
            # Create BookingRooms and update availability
            for room_data in validated_data['booking_rooms']:
                BookingRoom.objects.create(
                    booking=booking, 
                    room_type_id=room_data['room_type_id'],
                    board_type_id=room_data['board_type_id'],
                    quantity=room_data['quantity'],
                    adults=room_data['adults'],
                    children=room_data['children'],
                    extra_requests=room_data.get('extra_requests') 
                )

                for date in date_range:
                    availability_obj = availability_map[(room_data['room_type_id'], date)]
                    availability_obj.quantity -= room_data['quantity']
                    availability_obj.save()

            # Create Guests
            for guest_data in validated_data['guests']:
                # The 'wants_to_register' field should be popped if it exists, as it's not a model field
                guest_data.pop('wants_to_register', None)
                Guest.objects.create(booking=booking, **guest_data)
                
            # TODO: Handle optional registration if requested by the principal guest (Future Feature)

        except ValidationError as e:
            # Delete the booking object if it was created before the exception
            if 'booking' in locals():
                booking.delete()
            # Clean up Django's built-in ValidationError messages for API response
            error_message = str(e) if isinstance(e, ValidationError) else "خطای ناشناخته در فرآیند رزرو."
            return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(
            {"success": True, "booking_code": booking.booking_code, "total_price": booking.total_price},
            status=status.HTTP_201_CREATED
        )


class MyBookingsAPIView(generics.ListAPIView):
    """API view for authenticated users to list their bookings."""
    serializer_class = BookingListSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        agency_profile = user.agency_profile if hasattr(user, 'agency_profile') else None
        if agency_profile and agency_profile.agency:
            # Return agency bookings if user is linked to an agency
            return Booking.objects.filter(agency=agency_profile.agency)
        # Otherwise, return personal bookings
        return Booking.objects.filter(user=user, agency__isnull=True)


class BookingRequestAPIView(APIView):
    """API view to request cancellation or modification of a booking."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        booking_code = request.data.get('booking_code')
        request_type = request.data.get('request_type')
        
        if not booking_code or request_type not in ['cancellation', 'modification']:
            return Response({"error": "Booking code and request type (cancellation/modification) are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(booking_code=booking_code)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        agency_profile = request.user.agency_profile if hasattr(request.user, 'agency_profile') else None
        # Authorization check: user owns the booking or is an authorized agency user
        if not (booking.user == request.user or (agency_profile and booking.agency == agency_profile.agency)):
            return Response({"error": "You are not authorized to make this request."}, status=status.HTTP_403_FORBIDDEN)
        
        if request_type == 'cancellation':
            booking.status = 'cancellation_requested'
            booking.save()
            return Response({"success": True, "message": "Cancellation request submitted successfully."}, status=status.HTTP_200_OK)

        elif request_type == 'modification':
            booking.status = 'modification_requested'
            booking.save()
            return Response({"success": True, "message": "Modification request submitted successfully."}, status=status.HTTP_200_OK)


class InitiatePaymentAPIView(APIView):
    """API view to initiate payment for a pending booking."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        booking_code = request.data.get('booking_code')
        try:
            booking = Booking.objects.get(booking_code=booking_code, status='pending')
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found or is not pending payment."}, status=status.HTTP_404_NOT_FOUND)

        # In a real system, external payment gateway logic would be here
        return Response({
            "success": True,
            "message": "Payment API ready, but bank gateway connection needs implementation.",
            "redirect_url": "http://example.com/payment-gateway-simulated"
        })

class VerifyPaymentAPIView(APIView):
    """API view to verify payment status and confirm booking."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        status_code = request.data.get('status')
        booking_code = request.data.get('booking_code')
        
        try:
            booking = Booking.objects.get(booking_code=booking_code)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        if status_code == 'success':
            if booking.status != 'pending':
                return Response({"error": "This booking has already been processed."}, status=status.HTTP_400_BAD_REQUEST)

            booking.status = 'confirmed'
            booking.save()
            
            if booking.agency:
                 AgencyTransaction.objects.create(
                    agency=booking.agency,
                    booking=booking, 
                    amount=booking.total_price, 
                    transaction_type='payment',
                    description=f"Online payment for booking code {booking.booking_code}"
                )
            return Response({"success": True, "message": "Payment successful and booking confirmed."}, status=status.HTTP_200_OK)
        else:
            # We assume a failed payment means cancellation
            booking.status = 'cancelled' 
            booking.save()
            return Response({"success": False, "message": "Payment failed. Booking cancelled."}, status=status.HTTP_400_BAD_REQUEST)
