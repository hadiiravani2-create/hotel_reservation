# core/urls.py
# version: 1.0.3
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # آدرس‌های قبلی برای تنظیمات و ثبت نام کاربر
    path('api/settings/', views.SiteSettingsAPIView.as_view(), name='site_settings_api'),
    path('api/auth/register/', views.UserRegisterAPIView.as_view(), name='user_register_api'),
    # NEW: API URL for User Login
    path('api/auth/login/', views.UserLoginAPIView.as_view(), name='user_login_api'), # ADDED: Login API path
    
    # CORRECTED: Changed 'MenuAPIView' to 'MenuView' to match the actual class name in views.py.
    # The URL now correctly points to the existing view.
    path('api/menu/<slug:menu_slug>/', views.MenuView.as_view(), name='menu_api'),
]
