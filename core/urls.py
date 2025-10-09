# hadiiravani2-create/hotel_reservation/hotel_reservation-ad5e9db0ffd7b2bcb0d9a71d3e529d79333b2de0/core/urls.py
# v1.0.2
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # آدرس‌های قبلی برای تنظیمات و ثبت نام کاربر
    path('api/settings/', views.SiteSettingsAPIView.as_view(), name='site_settings_api'),
    path('api/auth/register/', views.UserRegisterAPIView.as_view(), name='user_register_api'),
    
    # CORRECTED: Changed 'MenuAPIView' to 'MenuView' to match the actual class name in views.py.
    # The URL now correctly points to the existing view.
    path('api/menu/<slug:menu_slug>/', views.MenuView.as_view(), name='menu_api'),
]
