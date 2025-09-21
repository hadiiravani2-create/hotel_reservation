# core/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404

# ایمپورت‌های مدل‌ها از فایل models.py در همین اپلیکیشن (core)
from .models import SiteSettings, Menu, CustomUser 

# ایمپورت سریالایزرها از فایل serializers.py در همین اپلیکیشن (core)
from .serializers import SiteSettingsSerializer, MenuSerializer, UserRegisterSerializer


class SiteSettingsAPIView(APIView):
    def get(self, request):
        settings = SiteSettings.objects.first()
        if not settings:
            return Response({"error": "تنظیمات سایت هنوز پیکربندی نشده است."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SiteSettingsSerializer(settings)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MenuAPIView(APIView):
    def get(self, request, menu_slug):
        menu = get_object_or_404(Menu, slug=menu_slug)
        serializer = MenuSerializer(menu)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRegisterAPIView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # پس از ثبت نام موفق، یک توکن برای کاربر جدید ایجاد و برمی‌گردانیم
        user = CustomUser.objects.get(username=response.data['username'])
        token, created = Token.objects.get_or_create(user=user)
        response.data['token'] = token.key
        return response