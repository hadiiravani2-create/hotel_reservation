# reservations/views.py
# version: 2.0.8
# CRITICAL FIX: Implemented user assignment logic for unauthenticated users (Guest/Registration) 
#               to prevent downstream 500 errors caused by booking.user=None dependencies.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.db import transaction
from jdatetime import datetime as jdatetime, timedelta
from decimal import Decimal
from collections import defaultdict
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404 
from rest_framework.exceptions import PermissionDenied 
from django.db.models import ObjectDoesNotExist, Q # Added Q for OR logic in queryset filtering
from .serializers import BookingStatusUpdateSerializer
# --- Imports ---
from .serializers import (
    CreateBookingAPISerializer, BookingListSerializer, BookingDetailSerializer,
    OfflineBankSerializer, PaymentConfirmationSerializer,
    GuestBookingLookupSerializer
)
from pricing.selectors import calculate_multi_booking_price
from hotels.models import RoomType, BoardType
from pricing.models import Availability
from core.models import WalletTransaction,Wallet
from .models import Booking, Guest, BookingRoom, OfflineBank, PaymentConfirmation 
from agencies.models import Agency, AgencyTransaction, AgencyUser
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated 
from django.utils.decorators import method_decorator

CustomUser = get_user_model()

class PayWithWalletAPIView(APIView):
    """
    Handles payment for a booking using the user's wallet balance.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, booking_code):
        try:
            booking = Booking.objects.get(booking_code=booking_code, user=request.user, status='pending')
        except Booking.DoesNotExist:
            return Response({"error": "رزرو یافت نشد یا در وضعیت مناسب برای پرداخت نیست."}, status=status.HTTP_404_NOT_FOUND)

        wallet = get_object_or_404(Wallet, user=request.user)

        if wallet.balance < booking.total_price:
            return Response({"error": "موجودی کیف پول شما برای پرداخت این رزرو کافی نیست."}, status=status.HTTP_400_BAD_REQUEST)

        # Create a wallet transaction for the payment
        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='payment',
            amount=-booking.total_price,  # Negative amount for payment
            status='completed',
            booking=booking,
            description=f"پرداخت هزینه رزرو شماره {booking.booking_code}"
        )

        # Update booking status to confirmed
        booking.status = 'confirmed'
        booking.save(update_fields=['status'])

        return Response({"success": True, "message": "پرداخت با موفقیت انجام شد و رزرو شما تایید گردید."}, status=status.HTTP_200_OK)

class CreateBookingAPIView(APIView):
    """API view for creating a booking, supporting both authenticated users and guests."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny] 

    @transaction.atomic
    def post(self, request):
        serializer = CreateBookingAPISerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        
        # Determine the booking user. Use request.user if authenticated, otherwise None (Guest Booking).
        user = request.user if request.user.is_authenticated else None
        agency = None
        principal_guest_data = validated_data['guests'][0] # Principal guest data

        # --- CRITICAL USER ASSIGNMENT LOGIC ---
        if not user:
            
            # 1. SCENARIO: Guest Checkout with Registration Request (wants_to_register)
            if principal_guest_data.get('wants_to_register'):
                # Creating an inactive user (Ghost User) linked to the booking data. User sets password later.
                try:
                    # Assuming 'phone_number' is used as the unique username
                    user_phone = principal_guest_data.get('phone_number')
                    if user_phone:
                         user = CustomUser.objects.create_user(
                            username=user_phone,
                            email=principal_guest_data.get('email', f"{user_phone}@guest.com"),
                            first_name=principal_guest_data.get('first_name'),
                            last_name=principal_guest_data.get('last_name'),
                            is_active=False, # User must set password/confirm details to activate
                            password=CustomUser.objects.make_random_password() # Placeholder password
                        )
                    # If phone is missing, registration is deferred or falls through to guest user.
                except Exception:
                    # If user creation fails (e.g., username already exists), fall through.
                    pass
                    
            # 2. SCENARIO: Pure Guest Checkout or Failed Registration (user=None after attempt)
            if not user:
                try:
                    # Fallback to a single, dedicated GUEST_USER account to prevent downstream 500 errors 
                    # Note: You must ensure a user with username='guest_user' exists in the database.
                    user = CustomUser.objects.get(username='guest_user')
                except CustomUser.DoesNotExist:
                    # If guest_user doesn't exist, final fallback is to user=None (model allows it).
                    user = None
        # --- END USER ASSIGNMENT LOGIC ---

        if validated_data.get('agency_id'):
            # Agency booking requires authentication
            if not user or user.username == 'guest_user': # Disallow guest user to book for an agency
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
                user # Pass the determined user (authenticated or None/guest_user) for pricing calculation
            )
            
            if price_data is None:
                raise ValidationError("Error calculating final price.")

            total_price = price_data['total_price']


            # Create Booking
            first_room_type_id = validated_data['booking_rooms'][0]['room_type_id']
            hotel = RoomType.objects.get(pk=first_room_type_id).hotel

            # Determine the initial status based on the hotel's booking process type.
            initial_status = 'pending' if hotel.is_online else 'awaiting_confirmation'

            # Create Booking with the dynamically determined status.
            booking = Booking.objects.create(
                user=user,
                agency=agency,
                check_in=check_in,
                check_out=check_out,
                status=initial_status, # <-- The new dynamic status is used here
                total_price=total_price,
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
                    availability_obj = availability_map[(room_type_id, date)]
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

class BookingDetailAPIView(APIView):
    """Retrieves details of a single booking by booking_code for payment/review page."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, booking_code):
        booking = get_object_or_404(Booking, booking_code=booking_code)
        
        # Authorization check: 
        is_owner_or_agency = False
        if request.user.is_authenticated:
            is_owner_or_agency = (booking.user == request.user)
            if booking.agency:
                # FIX: Corrected related_name from agency_users to profiles for AgencyUser model lookup
                agency_user = booking.agency.profiles.filter(user=request.user).exists()
                is_owner_or_agency = is_owner_or_agency or agency_user
        
        if booking.status != 'pending' and not is_owner_or_agency:
             raise PermissionDenied("شما اجازه دسترسی به جزئیات این رزرو را ندارید.")
        
        serializer = BookingDetailSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)

class GuestBookingLookupAPIView(APIView):
    """
    Allows unregistered guests to securely look up their booking using the booking code and principal guest ID/Passport.
    This bypasses the strict authorization check in BookingDetailAPIView for confirmed bookings.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = GuestBookingLookupSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        booking = serializer.validated_data['booking']
        
        # Now that the user is authenticated via code + ID, return the details.
        # Note: We do not need the full authorization check here because validation already confirmed identity.
        detail_serializer = BookingDetailSerializer(booking)
        
        return Response(detail_serializer.data, status=status.HTTP_200_OK)

# --- NEW OFFLINE PAYMENT VIEWS ---

class OfflineBankListAPIView(generics.ListAPIView):
    """API view to list active offline bank accounts for reference."""
    queryset = OfflineBank.objects.filter(is_active=True)
    serializer_class = OfflineBankSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

class PaymentConfirmationAPIView(APIView):
    """API view for submitting payment confirmation details."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PaymentConfirmationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        confirmation = serializer.save()
        
        # --- START: New logic to enrich transaction description ---
        # Check if the related object is a WalletTransaction
        if isinstance(confirmation.content_object, WalletTransaction):
            transaction = confirmation.content_object
            bank_name = confirmation.offline_bank.bank_name
            payment_time = confirmation.payment_date.strftime('%H:%M')
            payment_date_jalali = jdatetime.fromgregorian(date=confirmation.payment_date).strftime('%Y/%m/%d')

            # Create a rich, descriptive string
            new_description = (
                f"واریز به حساب بانک {bank_name} "
                f"در تاریخ {payment_date_jalali} ساعت {payment_time}. "
                f"شماره پیگیری: {confirmation.tracking_code}"
            )
            
            # Update the transaction's description
            transaction.description = new_description
            transaction.save(update_fields=['description'])
        # --- END: New logic ---
        
        return Response({
            "success": True, 
            "message": "اطلاعات پرداخت شما با موفقیت ثبت شد و در حال بررسی است.", 
            "confirmation_id": confirmation.id
        }, status=status.HTTP_201_CREATED)


class MyBookingsAPIView(generics.ListAPIView):
    """API view for authenticated users to list their bookings."""
    serializer_class = BookingListSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        agency_profile = user.agency_profile if hasattr(user, 'agency_profile') else None
        
        # FIX: Ensure agency users also see their personal bookings (user=user)
        if agency_profile and agency_profile.agency:
            # Agency users see bookings they created OR all bookings for their agency
            agency = agency_profile.agency
            # Filter for bookings where the user is the creator (user=user) 
            # OR the booking belongs to their agency (agency=agency)
            return Booking.objects.filter(
                Q(user=user) | Q(agency=agency)
            ).distinct()
            
        # Otherwise, return personal bookings (made by this user, without an agency association)
        # The agency__isnull=True filter is kept for consistency with the original logic for non-agency users.
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
class OperatorBookingConfirmationAPIView(APIView):
    """
    API view for operators to list and manage bookings awaiting confirmation.
    Requires operator-level permissions.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated] # TODO: Replace with a custom operator permission

    def get(self, request):
        """
        Lists all bookings that are awaiting manual confirmation.
        """
        # TODO: Add permission check to ensure user is an operator/staff
        bookings = Booking.objects.filter(status='awaiting_confirmation')
        serializer = BookingListSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Updates the status of a specific booking.
        """
        # TODO: Add permission check
        serializer = BookingStatusUpdateSerializer(data=request.data)
        if serializer.is_valid():
            booking = serializer.save()
            return Response(
                {"success": True, "message": f"وضعیت رزرو {booking.booking_code} با موفقیت به '{booking.get_status_display()}' تغییر یافت."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


