# agencies/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from .serializers import AgencyReportSerializer
from reservations.models import Booking

class AgencyReportAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'agency') or not user.agency:
            return Response(
                {"error": "شما کاربر آژانسی نیستید."},
                status=status.HTTP_403_FORBIDDEN
            )

        agency = user.agency

        # دریافت ۲۰ رزرو آخر مربوط به تمام کاربران این آژانس
        bookings = Booking.objects.filter(user__agency=agency).order_by('-created_at')[:20]

        # دریافت ۲۰ تراکنش آخر این آژانس
        transactions = agency.transactions.order_by('-created_at')[:20]

        # آماده‌سازی داده‌ها برای سریالایزر
        report_data = {
            'agency': agency,
            'bookings': bookings,
            'transactions': transactions
        }

        serializer = AgencyReportSerializer(report_data)
        return Response(serializer.data, status=status.HTTP_200_OK)