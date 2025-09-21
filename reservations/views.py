# reservations/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from jdatetime import datetime as jdatetime
from .serializers import CreateBookingSerializer
from pricing.selectors import calculate_booking_price, find_available_rooms
from .models import Booking, Guest
from rest_framework.permissions import IsAuthenticated 
from rest_framework.authentication import TokenAuthentication
from rest_framework import generics
from .serializers import BookingListSerializer

class CreateBookingAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    @transaction.atomic # تضمین می‌کند که تمام عملیات دیتابیس با هم موفق یا ناموفق شوند
    def post(self, request):
        serializer = CreateBookingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            check_in = jdatetime.strptime(data['check_in'], '%Y-%m-%d').date()
            check_out = jdatetime.strptime(data['check_out'], '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "فرمت تاریخ نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        # ۱. بررسی مجدد موجودی برای جلوگیری از رزرو همزمان
        available_rooms = find_available_rooms(
            city_id=0, # city_id در این مرحله مهم نیست چون room_type_id را داریم
            check_in_date=check_in,
            check_out_date=check_out,
            adults=data['adults'],
            children=data['children']
        )

        room_is_still_available = any(room['room_id'] == data['room_type_id'] for room in available_rooms)
        if not room_is_still_available:
            return Response({"error": "متاسفانه اتاق در تاریخ انتخابی شما دیگر موجود نیست."}, status=status.HTTP_409_CONFLICT) # 409 Conflict

        # ۲. محاسبه مجدد قیمت در سمت سرور برای امنیت
        price_details = calculate_booking_price(
            room_type_id=data['room_type_id'],
            check_in_date=check_in,
            check_out_date=check_out,
            adults=data['adults'],
            children=data['children']
        )

        # ۳. ایجاد رزرو اصلی
        booking = Booking.objects.create(
            room_type_id=data['room_type_id'],
            check_in=check_in,
            check_out=check_out,
            adults=data['adults'],
            children=data['children'],
            total_price=price_details['total_price'],
            status='pending' # وضعیت اولیه: در انتظار پرداخت
        )
        # اگر کاربر لاگین بود، رزرو را به او اختصاص بده
        if request.user.is_authenticated:
            booking.user = request.user
            booking.save()


        # ۴. ایجاد رکوردهای میهمانان
        for guest_data in data['guests']:
            Guest.objects.create(booking=booking, **guest_data)

        # ۵. کاهش موجودی اتاق‌ها (بسیار مهم)
        # این بخش را در آینده برای جلوگیری از رزرو همزمان باید بهینه‌تر کنیم
        # ...

        return Response({
            "success": True,
            "booking_code": booking.booking_code
        }, status=status.HTTP_201_CREATED)



class MyBookingsAPIView(generics.ListAPIView):
    serializer_class = BookingListSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # فقط رزروهای کاربر فعلی که درخواست را ارسال کرده، برگردانده می‌شود
        return Booking.objects.filter(user=self.request.user)