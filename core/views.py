# core/views.py
# version: 1.0.2
# FEATURE: Added UserWalletDetailAPIView to fetch user wallet information.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

# ایمپورت‌های مدل‌ها
from .models import SiteSettings, Menu, CustomUser, Wallet

# ایمپورت سریالایزرها
from .serializers import (
    SiteSettingsSerializer, MenuItemSerializer, UserRegisterSerializer, 
    UserLoginSerializer, UserAuthSerializer, MenuSerializer, WalletSerializer
)

class SiteSettingsAPIView(APIView):
    """API view to fetch site settings."""
    def get(self, request):
        settings = SiteSettings.objects.first()
        if not settings:
            return Response({"error": "تنظیمات سایت هنوز پیکربندی نشده است."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SiteSettingsSerializer(settings)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MenuView(APIView):
    """API view to fetch a specific menu and its nested items."""
    def get(self, request, menu_slug):
        menu = get_object_or_404(Menu, slug=menu_slug)
        menu_items = menu.items.all()
        serializer = MenuItemSerializer(menu_items, many=True)
        return Response(serializer.data)


class UserRegisterAPIView(generics.CreateAPIView):
    """API view for user registration."""
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        user = serializer.instance 
        token, created = Token.objects.get_or_create(user=user)
        user_data = serializer.data
        
        return Response({
            'token': token.key,
            'user': user_data,
        }, status=status.HTTP_201_CREATED)


class UserLoginAPIView(APIView):
    """API view for user login and returning token."""
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        user_data = UserAuthSerializer(user).data
        
        return Response({
            'token': token.key,
            'user': user_data,
        }, status=status.HTTP_200_OK)


# --- NEW: Wallet API View ---

class UserWalletDetailAPIView(APIView):
    """
    API view for retrieving the authenticated user's wallet details.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Retrieve the wallet for the authenticated user.
        # The create_user_wallet signal ensures the wallet exists, but get_or_create is safer.
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        
        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)
