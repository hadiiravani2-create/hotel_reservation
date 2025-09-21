# core/urls.py

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # آدرس‌های قبلی برای تنظیمات و منو
    path('api/settings/', views.SiteSettingsAPIView.as_view(), name='site_settings_api'),
    path('api/menu/<slug:menu_slug>/', views.MenuAPIView.as_view(), name='menu_api'),
    
    # آدرس جدید برای ثبت نام کاربر که به اینجا منتقل شد
    path('api/auth/register/', views.UserRegisterAPIView.as_view(), name='user_register_api'),
]