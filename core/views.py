# core/views.py
# version: 1.0.1
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404

# ایمپورت‌های مدل‌ها
from .models import SiteSettings, Menu, CustomUser 

# ایمپورت سریالایزرها
from .serializers import SiteSettingsSerializer, MenuItemSerializer, UserRegisterSerializer, UserLoginSerializer, UserAuthSerializer, MenuSerializer # ADDED: UserLoginSerializer, UserAuthSerializer

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
        # Find the menu by its slug
        menu = get_object_or_404(Menu, slug=menu_slug)
        
        # Get all related items for that menu
        menu_items = menu.items.all()
        
        # Serialize the list of items directly
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
        
        # UserAuthSerializer is implicitly called inside UserRegisterSerializer.to_representation
        user_data = serializer.data
        
        return Response({
            'token': token.key,
            'user': user_data,
        }, status=status.HTTP_201_CREATED)

# NEW CLASS: API view for user login
class UserLoginAPIView(APIView):
    """API view for user login and returning token."""
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        # The validated user object is stored in serializer.validated_data['user']
        user = serializer.validated_data['user']
        
        # Get or create token for the authenticated user
        token, created = Token.objects.get_or_create(user=user)
        
        # Serialize user data using the dedicated Auth serializer
        user_data = UserAuthSerializer(user).data
        
        return Response({
            'token': token.key,
            'user': user_data,
        }, status=status.HTTP_200_OK)
