# reservations/views.py
# version: 2.0.9
# FIX: Aligned CreateBookingAPIView with new serializer fields (extra_adults, children_count)
#      and added logic to process and save 'selected_services'.

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
from django.http import HttpResponse # Import HttpResponse
import traceback # <-- IMPORT TRACEBACK
from rest_framework.exceptions import PermissionDenied 
from django.db.models import ObjectDoesNotExist, Q # Added Q for OR logic in queryset filtering
from .serializers import BookingStatusUpdateSerializer
# --- Imports ---
from .serializers import (
    CreateBookingAPISerializer, BookingListSerializer, BookingDetailSerializer,
    OfflineBankSerializer, PaymentConfirmationSerializer
)
from pricing.selectors import calculate_multi_booking_price
from hotels.models import RoomType, BoardType
from pricing.models import Availability
from core.models import WalletTransaction,Wallet
from .models import Booking, Guest, BookingRoom, OfflineBank, PaymentConfirmation 
from .pdf_utils import generate_booking_confirmation_pdf
from agencies.models import Agency, AgencyTransaction, AgencyUser
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated 
from django.utils.decorators import method_decorator
from django.apps import apps
from cancellations.services import calculate_cancellation_fee

CustomUser = get_user_model()

# --- Conditionally import services models ---
if apps.is_installed('services'):
    try:
        from services.models import HotelService, BookedService
        SERVICES_APP_ENABLED = True
    except ImportError:
        SERVICES_APP_ENABLED = False
else:
    SERVICES_APP_ENABLED = False



# --- CancelBookingAPIView  ---
class CancelBookingAPIView(APIView):
    """
    Handles the cancellation of a booking by an authenticated user.
    Calculates the cancellation fee, updates booking status, and processes the refund to the user's wallet.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic # Ensure all database operations succeed or fail together
    def post(self, request):
        booking_code = request.data.get('booking_code')
        if not booking_code:
            return Response({"error": "شناسه رزرو (booking_code) الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve the booking, ensuring it belongs to the user and is in a cancellable state
            booking = get_object_or_404(
                Booking,
                booking_code=booking_code,
                user=request.user
            )

            # Define cancellable statuses (adjust as needed based on your business logic)
            CANCELLABLE_STATUSES = ['confirmed', 'pending', 'awaiting_confirmation']
            if booking.status not in CANCELLABLE_STATUSES:
                return Response(
                    {"error": f"رزرو در وضعیت '{booking.get_status_display()}' قابل لغو نیست."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 1. Calculate Cancellation Fee
            cancellation_fee = calculate_cancellation_fee(booking)
            refund_amount = (booking.total_amount or Decimal(0)) - cancellation_fee
            refund_amount = max(Decimal(0), refund_amount) # Ensure refund is not negative

            # 2. Update Booking Status
            booking.status = 'cancelled'
            booking.save(update_fields=['status'])

            # 3. Process Refund to Wallet (if applicable)
            if refund_amount > 0:
                try:
                    wallet = Wallet.objects.get(user=request.user)
                    # Use F() expression for safe concurrent update
                    wallet.balance = F('balance') + refund_amount
                    wallet.save(update_fields=['balance'])

                    # 4. Create Refund Transaction Record
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='refund',
                        amount=refund_amount, # Positive amount for refund
                        status='completed',
                        booking=booking,
                        description=f"بازگشت وجه لغو رزرو {booking.booking_code} (جریمه: {cancellation_fee})"
                    )
                except Wallet.DoesNotExist:
                    # Handle case where user might not have a wallet (though ideally they should)
                    # Log this situation? For now, we proceed with cancellation but skip refund.
                    pass # Or return an error specific to wallet issue

            # 5. Return Success Response
            return Response({
                "success": True,
                "message": f"رزرو با موفقیت لغو شد. مبلغ جریمه: {cancellation_fee} تومان. مبلغ بازگشتی به کیف پول: {refund_amount} تومان.",
                "booking_code": booking.booking_code,
                "cancellation_fee": cancellation_fee,
                "refund_amount": refund_amount
            }, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
             return Response({"error": "رزروی با این شناسه یافت نشد یا به شما تعلق ندارد."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Generic error handler for unexpected issues
            # Log the error e
            return Response({"error": "خطایی در فرآیند لغو رزرو رخ داد."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        booking.paid_amount = booking.total_price
        booking.save(update_fields=['status', 'paid_amount'])
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
                total_room_price=total_price,
                total_service_price=Decimal(0),
                total_vat=Decimal(0), # Assuming VAT is included in total_price for now
                paid_amount=Decimal(0)
            )
            
            # Create BookingRooms and update availability
            first_room_data = validated_data['booking_rooms'][0]
            for room_data in validated_data['booking_rooms']:
                try:
                    room_type = RoomType.objects.get(pk=room_data['room_type_id'])
                except RoomType.DoesNotExist:
                    raise ValidationError(f"اتاقی با شناسه {room_data['room_type_id']} یافت نشد.")
                room_type_id = room_data['room_type_id']
                board_type_id = room_data['board_type_id']

                # Find the price details calculated by the selector
                room_price_details = next(
                    (p for p in price_data.get('room_specific_prices', [])
                     if p.get('room_type_id') == room_type_id and p.get('board_type_id') == board_type_id),
                    None
                )
                room_total_price = room_price_details['total_price'] if room_price_details else Decimal(0)

                # --- START: Modified logic to read new field names ---
                extra_adults_for_model = room_data.get('extra_adults', 0)
                children_for_model = room_data.get('children_count', 0)
                room_total_price = Decimal(0)
                if room_data == first_room_data:
                    room_total_price = booking.total_room_price
                
                BookingRoom.objects.create(
                    booking=booking, 
                    room_type_id=room_data['room_type_id'],
                    board_type_id=room_data['board_type_id'],
                    quantity=room_data['quantity'],
                    adults=extra_adults_for_model, # Use new field
                    children=children_for_model, # Use new field
                    extra_requests=room_data.get('extra_requests'), 
                    total_price=room_total_price
                )
                # --- END: Modified logic ---

                current_room_type_id = room_data['room_type_id']
                for date in date_range:
                    availability_obj = availability_map[(current_room_type_id, date)]
                    availability_obj.quantity -= room_data['quantity']
                    availability_obj.save()

            # Create Guests
            for guest_data in validated_data['guests']:
                # The 'wants_to_register' field should be popped if it exists, as it's not a model field
                guest_data.pop('wants_to_register', None)
                Guest.objects.create(booking=booking, **guest_data)
                
            # --- START: New logic to save selected services ---
            if SERVICES_APP_ENABLED and 'selected_services' in validated_data:
                for service_data in validated_data['selected_services']:
                    try:
                        service_id = service_data.get('id')
                        quantity = service_data.get('quantity', 1)
                        service = HotelService.objects.get(id=service_id, hotel=hotel)
                        
                        # Calculate price based on service model
                        price = 0
                        if service.pricing_model == 'PERSON':
                            price = service.price * quantity
                        elif service.pricing_model == 'BOOKING':
                            price = service.price
                            quantity = 1 # Enforce quantity 1 for per-booking
                        # FREE services have price 0

                        BookedService.objects.create(
                            booking=booking,
                            hotel_service=service,
                            quantity=quantity,
                            total_price=price,
                            details=service_data.get('details', {})
                        )
                        
                        # Add service price to booking total price
                        booking.total_price += price
                        booking.total_service_price += price

                    except HotelService.DoesNotExist:
                        pass # Skip invalid services
            
            # Save the booking again to update total_price with services
            booking.save(update_fields=['total_price', 'total_service_price'])
            # --- END: New logic to save selected services ---
                
            # TODO: Handle optional registration if requested by the principal guest (Future Feature)

        except ValidationError as e:
            # Delete the booking object if it was created before the exception
            if 'booking' in locals():
                booking.delete()
            # Clean up Django's built-in ValidationError messages for API response
            error_message = str(e) if isinstance(e, ValidationError) else "خطای ناشناخته در فرآیند رزرو."
            return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(
            {
                "success": True, 
                "booking_code": booking.booking_code, 
                "total_price": booking.total_price,
                # Logic: If hotel is online -> 'online' (User goes to payment page)
                #        If hotel is offline -> 'offline' (User goes to success/tracking page)
                "payment_type": 'online' if hotel.is_online else 'offline'
            },
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
    Updated to search in BOTH national_id and passport_number.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # دریافت مستقیم پارامترها از بدنه درخواست
        booking_code = request.data.get('booking_code')
        # فرانت‌اند ممکن است مقدار را در national_id یا passport_number بفرستد
        # ما آن را به عنوان یک "Search term" در نظر می‌گیریم
        search_id = request.data.get('national_id') or request.data.get('passport_number')

        if not booking_code or not search_id:
            return Response(
                {'non_field_errors': ['کد رزرو و کد ملی/پاسپورت الزامی است.']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # منطق جدید جستجو با استفاده از Q objects
        # شرط: کد رزرو دقیق باشد + (کد ملی مهمان برابر باشد با ورودی OR شماره پاسپورت مهمان برابر باشد با ورودی)
        booking = Booking.objects.filter(
            booking_code=booking_code
        ).filter(
            Q(guests__national_id=search_id) | Q(guests__passport_number=search_id)
        ).distinct().first()
        
        if not booking:
            return Response(
                {'non_field_errors': ['رزروی با این مشخصات یافت نشد.']}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # در صورت پیدا شدن، اطلاعات رزرو را برمی‌گردانیم
        detail_serializer = BookingDetailSerializer(booking)
        return Response(detail_serializer.data, status=status.HTTP_200_OK)


class BookingConfirmationPDFView(APIView):
    """
    Generates and returns the booking confirmation PDF.
    - GET: Authenticated users (owner or agency) can download.
    - POST: Guests can download by providing their ID code (National ID / Passport).
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny] # Permissions are checked manually inside methods

    def get(self, request, booking_code):
        """
        Handles PDF download for AUTHENTICATED users (e.g., from profile panel).
        """
        if not request.user.is_authenticated:
            raise PermissionDenied("برای دانلود این فایل، ابتدا باید وارد حساب کاربری خود شوید.")
        
        booking = get_object_or_404(Booking, booking_code=booking_code)

        # Check authorization for authenticated user
        is_owner = (booking.user == request.user)
        is_agency_member = False
        if booking.agency:
            # Use 'profiles' as per the fix in BookingDetailAPIView
            is_agency_member = booking.agency.profiles.filter(user=request.user).exists() 

        if not is_owner and not is_agency_member:
            raise PermissionDenied("شما اجازه دسترسی به این رزرو را ندارید.")
        
        # --- Generate and Return PDF ---
        return self.generate_pdf_response(booking)

    def post(self, request, booking_code):
        """
        Handles PDF download for GUEST users (e.g., from track-booking page).
        Requires 'guest_id_code' (National ID or Passport) in the POST body.
        """
        booking = get_object_or_404(Booking, booking_code=booking_code)
        guest_id_code = request.data.get('guest_id_code')

        if not guest_id_code:
            return Response({"error": "کد شناسایی میهمان (کد ملی یا شماره پاسپورت) الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate against the principal guest (assuming first guest)
        principal_guest = booking.guests.first()
        
        # Assuming Guest model has 'national_id' and 'passport_id' fields
        if not principal_guest or \
           (principal_guest.national_id != guest_id_code and principal_guest.passport_id != guest_id_code):
            
            raise PermissionDenied("اطلاعات شناسایی میهمان با این رزرو مطابقت ندارد.")

        # --- Generate and Return PDF ---
        return self.generate_pdf_response(booking)

    def generate_pdf_response(self, booking: Booking):
        """
        Helper method to generate the PDF response.
        """
        try:
            pdf_bytes = generate_booking_confirmation_pdf(booking)
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            # 'inline' suggests the browser should try to display it, rather than force download
            response['Content-Disposition'] = f'inline; filename="booking_{booking.booking_code}.pdf"'
            return response
        except Exception as e:
            # --- START: CRITICAL DEBUGGING ---
            # Print the full exception traceback to the console
            print("--- PDF Generation Error ---")
            print(f"Failed to generate PDF for booking {booking.booking_code}.")
            print(f"Exception Type: {type(e)}")
            print(f"Exception Details: {e}")
            traceback.print_exc() # This prints the full traceback
            print("-----------------------------")
            # --- END: CRITICAL DEBUGGING ---
            # Log the error (e.g., logging.error(f"Error generating PDF: {e}"))
            return Response({"error": f"خطا در تولید فایل PDF رخ داد."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- NEW OFFLINE PAYMENT VIEWS ---

class OfflineBankListAPIView(generics.ListAPIView):
    """
    API view to list active offline bank accounts for reference.
    Filters banks based on a 'hotel_id' query parameter.
    - If hotel_id is provided: Returns accounts for that hotel + general accounts (hotel=None).
    - If hotel_id is NOT provided: Returns only general accounts (hotel=None).
    """
    serializer_class = OfflineBankSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Overrides the default queryset to implement custom filtering."""
        hotel_id = self.request.query_params.get('hotel_id')
        
        # Base query for all active accounts
        base_query = OfflineBank.objects.filter(is_active=True)
        
        if hotel_id:
            try:
                # Filter for the specific hotel OR general accounts
                hotel_id_int = int(hotel_id)
                return base_query.filter(
                    Q(hotel_id=hotel_id_int) | Q(hotel__isnull=True)
                )
            except (ValueError, TypeError):
                # Fallback for invalid hotel_id: only general accounts
                return base_query.filter(hotel__isnull=True)
        else:
            # If no hotel is specified (e.g., wallet charging), only show general accounts
            return base_query.filter(hotel__isnull=True)

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
            booking.paid_amount = booking.total_price
            booking.save(update_fields=['status', 'paid_amount'])
            
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
            if booking.status == 'confirmed':
                booking.paid_amount = booking.total_price
                booking.save(update_fields=['paid_amount'])
            return Response(
                {"success": True, "message": f"وضعیت رزرو {booking.booking_code} با موفقیت به '{booking.get_status_display()}' تغییر یافت."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
