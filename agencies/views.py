# agencies/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from .serializers import AgencyReportSerializer
from reservations.models import Booking
from core.models import CustomUser, AgencyUserRole
from core.serializers import AgencySubUserSerializer, AgencyUserRoleSerializer

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
        
        # بررسی سطح دسترسی بر اساس نقش کاربر
        if user.agency_role.name not in ['admin', 'finance_manager', 'viewer']:
            return Response(
                {"error": "شما مجوز مشاهده گزارش مالی را ندارید."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        agency = user.agency

        # دریافت ۲۰ رزرو آخر مربوط به تمام کاربران این آژانس
        bookings = Booking.objects.filter(agency=agency).order_by('-created_at')[:20]

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


class AgencyUserManagementViewSet(viewsets.ModelViewSet):
    serializer_class = AgencySubUserSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # فقط مدیر آژانس می‌تواند کاربران زیرمجموعه را ببیند
        if self.request.user.agency_role.name == 'admin':
            return CustomUser.objects.filter(agency=self.request.user.agency)
        return CustomUser.objects.none()

    def perform_create(self, serializer):
        # بررسی اینکه کاربر فعلی مدیر آژانس است
        if self.request.user.agency_role.name != 'admin':
            return Response(
                {"error": "شما مجوز ایجاد کاربر جدید را ندارید."},
                status=status.HTTP_403_FORBIDDEN
            )
        # کاربر جدید را به آژانس کاربر فعلی متصل می‌کند
        serializer.save(agency=self.request.user.agency)

    def perform_update(self, serializer):
        if self.request.user.agency_role.name != 'admin':
            return Response(
                {"error": "شما مجوز ویرایش کاربر را ندارید."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.agency_role.name != 'admin':
            return Response(
                {"error": "شما مجوز حذف کاربر را ندارید."},
                status=status.HTTP_403_FORBIDDEN
            )
        instance.delete()


class AgencyUserRoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgencyUserRole.objects.all()
    serializer_class = AgencyUserRoleSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
