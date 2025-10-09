# hadiiravani2-create/hotel_reservation/hotel_reservation-ad5e9db0ffd7b2bcb0d9a71d3e529d79333b2de0/core/views.py
# v1.0.0
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404

# ایمپورت‌های مدل‌ها
from .models import SiteSettings, Menu, CustomUser 

# ایمپورت سریالایزرها
# FIX: Importing MenuItemSerializer as it's needed by MenuView.
from .serializers import SiteSettingsSerializer, MenuItemSerializer, UserRegisterSerializer, MenuSerializer

class SiteSettingsAPIView(APIView):
    def get(self, request):
        settings = SiteSettings.objects.first()
        if not settings:
            return Response({"error": "تنظیمات سایت هنوز پیکربندی نشده است."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SiteSettingsSerializer(settings)
        return Response(serializer.data, status=status.HTTP_200_OK)

# CORRECTED: Renamed class from MenuAPIView to MenuView to match urls.py
# and changed logic to return a list of menu items as the frontend expects.
class MenuView(APIView):
    def get(self, request, menu_slug):
        # Find the menu by its slug
        menu = get_object_or_404(Menu, slug=menu_slug)
        
        # Get all related items for that menu
        menu_items = menu.items.all()
        
        # Serialize the list of items directly
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
        
        return Response({
            'token': token.key,
            'user': user_data,
        }, status=status.HTTP_201_CREATED)
