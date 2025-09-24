# reservations/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.db import transaction
from jdatetime import datetime as jdatetime
from .serializers import CreateBookingSerializer, BookingListSerializer
from pricing.selectors import calculate_booking_price, find_available_rooms
from hotels.models import RoomType
from .models import Booking, Guest
from agencies.models import Contract, AgencyTransaction
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

class CreateBookingAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CreateBookingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = request.user

        try:
            check_in = jdatetime.strptime(data['check_in'], '%Y-%m-%d').date()
            check_out = jdatetime.strptime(data['check_out'], '%Y-%m-%d').date()
            room_type = RoomType.objects.get(id=data['room_type_id'])
        except (ValueError, TypeError):
            return Response({"error": "فرمت تاریخ یا شناسه اتاق نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
        except RoomType.DoesNotExist:
            return Response({"error": "اتاق مورد نظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        price_details = calculate_booking_price(
            room_type_id=data['room_type_id'], check_in_date=check_in,
            check_out_date=check_out, adults=data['adults'],
            children=data['children'], user=user
        )
        final_price = price_details['total_price']

        if data['payment_method'] == 'credit':
            if not hasattr(user, 'agency') or not user.agency:
                return Response({"error": "شما کاربر آژانسی نیستید و نمی‌توانید از اعتبار استفاده کنید."}, status=status.HTTP_403_FORBIDDEN)

            agency = user.agency

            # اصلاح منطق: لیست سیاه اعتباری باید مستقل از وجود قرارداد بررسی شود.
            if agency.credit_blacklist_hotels.filter(id=room_type.hotel.id).exists():
                return Response({"error": "استفاده از اعتبار برای این هتل مجاز نیست."}, status=status.HTTP_403_FORBIDDEN)

            if (agency.current_balance + final_price) > agency.credit_limit:
                return Response({"error": "اعتبار آژانس برای این رزرو کافی نیست."}, status=status.HTTP_400_BAD_REQUEST)

            booking_status = 'confirmed'
        else:
            booking_status = 'pending'

        booking = Booking.objects.create(
            user=user, room_type=room_type, check_in=check_in, check_out=check_out,
            adults=data['adults'], children=data['children'], total_price=final_price, status=booking_status
        )

        if data['payment_method'] == 'credit':
            AgencyTransaction.objects.create(
                agency=user.agency, booking=booking, amount=final_price,
                transaction_type='booking', created_by=user,
                description=f"رزرو اعتباری کد {booking.booking_code}"
            )

        for guest_data in data['guests']:
            Guest.objects.create(booking=booking, **guest_data)

        return Response({"success": True, "booking_code": booking.booking_code}, status=status.HTTP_201_CREATED)


class MyBookingsAPIView(generics.ListAPIView):
    serializer_class = BookingListSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # فیلتر رزروها بر اساس آژانس کاربر برای کاربران آژانسی
        if hasattr(self.request.user, 'agency') and self.request.user.agency:
            return Booking.objects.filter(agency=self.request.user.agency)
        # فیلتر رزروها بر اساس کاربر برای کاربران عادی
        return Booking.objects.filter(user=self.request.user)


class BookingRequestAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        booking_code = request.data.get('booking_code')
        request_type = request.data.get('request_type') # 'cancellation' or 'modification'
        
        if not booking_code or request_type not in ['cancellation', 'modification']:
            return Response({"error": "کد رزرو و نوع درخواست (cancellation/modification) الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(booking_code=booking_code)
        except Booking.DoesNotExist:
            return Response({"error": "رزرو مورد نظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        # اطمینان از اینکه کاربر فقط می‌تواند برای رزروهای خود درخواست ارسال کند
        if not (booking.user == request.user or (hasattr(request.user, 'agency') and booking.agency == request.user.agency)):
            return Response({"error": "شما مجوز انجام این درخواست را ندارید."}, status=status.HTTP_403_FORBIDDEN)
        
        if request_type == 'cancellation':
            # تغییر وضعیت رزرو به "در انتظار لغو"
            booking.status = 'cancellation_requested'
            booking.save()
            # Note: این وضعیت جدید باید به مدل Booking اضافه شود.
            return Response({"success": True, "message": "درخواست لغو رزرو با موفقیت ثبت شد."}, status=status.HTTP_200_OK)

        elif request_type == 'modification':
            # تغییر وضعیت رزرو به "در انتظار ویرایش"
            booking.status = 'modification_requested'
            booking.save()
            # Note: این وضعیت جدید نیز باید به مدل Booking اضافه شود.
            return Response({"success": True, "message": "درخواست ویرایش رزرو با موفقیت ثبت شد."}, status=status.HTTP_200_OK)
