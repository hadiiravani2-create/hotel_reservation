# core/views.py
# version: 1.0.3
# FEATURE: Added InitiateWalletDepositAPIView to create pending deposit transactions.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, serializers, viewsets
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from .models import SiteSettings, Menu, CustomUser, Wallet, WalletTransaction, SpecialPeriod
from .serializers import (
    SiteSettingsSerializer, MenuItemSerializer, UserRegisterSerializer, 
    UserLoginSerializer, UserAuthSerializer, MenuSerializer, WalletSerializer,SpecialPeriodSerializer
)

# ... (SiteSettingsAPIView, MenuView, UserRegisterAPIView, UserLoginAPIView remain unchanged) ...
class SiteSettingsAPIView(APIView):
    def get(self, request):
        settings = SiteSettings.objects.first()
        if not settings:
            return Response({"error": "تنظیمات سایت هنوز پیکربندی نشده است."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SiteSettingsSerializer(settings)
        return Response(serializer.data, status=status.HTTP_200_OK)
class MenuView(APIView):
    def get(self, request, menu_slug):
        menu = get_object_or_404(Menu, slug=menu_slug)
        menu_items = menu.items.all()
        serializer = MenuItemSerializer(menu_items, many=True)
        return Response(serializer.data)
class UserRegisterAPIView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        user = serializer.instance 
        token, created = Token.objects.get_or_create(user=user)
        user_data = serializer.data
        return Response({'token': token.key,'user': user_data,}, status=status.HTTP_201_CREATED)
class UserLoginAPIView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        user_data = UserAuthSerializer(user).data
        return Response({'token': token.key,'user': user_data,}, status=status.HTTP_200_OK)


class UserWalletDetailAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)

# --- NEW: Wallet Deposit Views ---

class InitiateWalletDepositSerializer(serializers.Serializer):
    """Serializer to validate the amount for a new deposit request."""
    amount = serializers.DecimalField(max_digits=20, decimal_places=0, min_value=1000, help_text="مبلغ شارژ (حداقل ۱۰۰۰ تومان)")

class InitiateWalletDepositAPIView(APIView):
    """
    API view for an authenticated user to initiate a wallet deposit.
    Creates a 'pending' transaction and returns its ID for the user to confirm payment.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiateWalletDepositSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount = serializer.validated_data['amount']
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        # Create a pending transaction
        transaction = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type='deposit',
            amount=amount,
            status='pending',
            description=f"درخواست شارژ آفلاین به مبلغ {amount}"
        )

        return Response({
            'success': True,
            'message': 'درخواست شارژ با موفقیت ثبت شد. لطفا اطلاعات واریز را ثبت کنید.',
            'transaction_id': transaction.transaction_id
        }, status=status.HTTP_201_CREATED)


class SpecialPeriodViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows SpecialPeriods (e.g., peak seasons)
    to be viewed or edited.
    """
    queryset = SpecialPeriod.objects.all()
    serializer_class = SpecialPeriodSerializer
    # Add permissions later if needed, e.g., [IsAdminUser]
