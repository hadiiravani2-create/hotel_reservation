# reservations/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.db import transaction
from jdatetime import datetime as jdatetime
from .serializers import CreateBookingSerializer, BookingListSerializer
from pricing.selectors import calculate_booking_price, find_available_rooms
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
        serializer = CreateBookingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user = request.user

        try:
            check_in = jdatetime.strptime(data['check_in'], '%Y-%m-%d').date()
            check_out = jdatetime.strptime(data['check_out'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return Response({"error": "فرمت تاریخ نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
        
        # محاسبه قیمت نهایی برای کل رزرو
        total_final_price = 0
        booking_rooms_data = data['booking_rooms']
        
        for room_data in booking_rooms_data:
            price_details = calculate_booking_price(
                room_type_id=room_data['room_type_id'],
                board_type_id=room_data['board_type_id'],
                check_in_date=check_in, 
                check_out_date=check_out, 
                adults=data['adults'],
                children=data['children'], 
                user=user
            )
            if price_details is None:
                return Response({"error": "قیمت برای یکی از اتاق‌ها یافت نشد یا سرویس در این تاریخ ارائه نمی‌شود."}, status=status.HTTP_400_BAD_REQUEST)
            total_final_price += price_details['total_price'] * room_data['quantity']


        if data['payment_method'] == 'credit':
            if not hasattr(user, 'agency') or not user.agency:
                return Response({"error": "شما کاربر آژانسی نیستید و نمی‌توانید از اعتبار استفاده کنید."}, status=status.HTTP_403_FORBIDDEN)

            agency = user.agency
            
            # بررسی لیست سیاه برای هر هتل در رزرو
            for room_data in booking_rooms_data:
                try:
                    room_type = RoomType.objects.get(id=room_data['room_type_id'])
                except RoomType.DoesNotExist:
                    return Response({"error": "اتاق مورد نظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
                if agency.credit_blacklist_hotels.filter(id=room_type.hotel.id).exists():
                    return Response({"error": f"استفاده از اعتبار برای هتل {room_type.hotel.name} مجاز نیست."}, status=status.HTTP_403_FORBIDDEN)

            if (agency.current_balance + total_final_price) > agency.credit_limit:
                return Response({"error": "اعتبار آژانس برای این رزرو کافی نیست."}, status=status.HTTP_400_BAD_REQUEST)

            booking_status = 'confirmed'
        else:
            booking_status = 'pending'

        booking = Booking.objects.create(
            user=user, 
            check_in=check_in, 
            check_out=check_out,
            adults=data['adults'], 
            children=data['children'], 
            total_price=total_final_price, 
            status=booking_status
        )
        
        # ایجاد مدل‌های BookingRoom
        for room_data in booking_rooms_data:
            room_type = RoomType.objects.get(id=room_data['room_type_id'])
            board_type = BoardType.objects.get(id=room_data['board_type_id'])
            BookingRoom.objects.create(
                booking=booking,
                room_type=room_type,
                board_type=board_type,
                quantity=room_data['quantity']
            )

        if data['payment_method'] == 'credit':
            AgencyTransaction.objects.create(
                agency=user.agency, booking=booking, amount=total_final_price,
                transaction_type='booking', created_by=user,
                description=f"رزرو اعتباری کد {booking.booking_code}"
            )
        else:
            # برای پرداخت آنلاین، نیازی به تراکنش در این مرحله نیست.
            # برای پرداخت دستی، رزرو ایجاد شده و منتظر تایید می‌ماند.
            pass

        for guest_data in data['guests']:
            Guest.objects.create(booking=booking, **guest_data)

        # ارسال پاسخ نهایی
        response_data = {"success": True, "booking_code": booking.booking_code}
        if booking_status == 'pending':
            response_data['message'] = 'رزرو شما با موفقیت ثبت شد و در انتظار پرداخت است.'
        elif booking_status == 'confirmed':
            response_data['message'] = 'رزرو شما با موفقیت تایید شد.'
            
        return Response(response_data, status=status.HTTP_201_CREATED)


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
            return Response({"success": True, "message": "درخواست لغو رزرو با موفقیت ثبت شد."}, status=status.HTTP_200_OK)

        elif request_type == 'modification':
            # تغییر وضعیت رزرو به "در انتظار ویرایش"
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

        # TODO: پیاده‌سازی منطق اتصال به درگاه پرداخت
        # این بخش باید با استفاده از کتابخانه‌های مخصوص درگاه (مثل زرین‌پال یا آیدی‌پی) پیاده‌سازی شود.
        # یک کد نمونه برای شبیه‌سازی:
        amount = booking.total_price
        callback_url = "https://yourdomain.com/reservations/api/verify-payment/" # آدرس callback
        
        # این بخش فقط یک نمونه شبیه‌سازی شده است.
        # response = requests.post("URL_درگاه_پرداخت", data={...})
        # if response.status_code == 200:
        #     return Response({"success": True, "redirect_url": response.json()['redirect_url']})
        # else:
        #     return Response({"error": "خطا در اتصال به درگاه پرداخت."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        # TODO: پیاده‌سازی منطق تایید پرداخت از درگاه
        # این بخش اطلاعات برگشتی از درگاه را دریافت و تایید می‌کند.
        # یک کد نمونه برای شبیه‌سازی:
        status_code = request.data.get('status')
        booking_code = request.data.get('booking_code')
        
        try:
            booking = Booking.objects.get(booking_code=booking_code)
        except Booking.DoesNotExist:
            return Response({"error": "رزرو مورد نظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        # اگر پرداخت موفق بود
        if status_code == 'success':
            booking.status = 'confirmed'
            booking.save()
            # ثبت تراکنش پرداخت
            AgencyTransaction.objects.create(
                agency=booking.agency, # اگر رزرو از طریق آژانس بود
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
