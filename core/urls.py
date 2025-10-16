# core/urls.py
# version: 1.0.4
# FEATURE: Added the API endpoint for fetching user wallet details.

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Site and Menu APIs
    path('api/settings/', views.SiteSettingsAPIView.as_view(), name='site_settings_api'),
    path('api/menu/<slug:menu_slug>/', views.MenuView.as_view(), name='menu_api'),
    
    # Auth APIs
    path('api/auth/register/', views.UserRegisterAPIView.as_view(), name='user_register_api'),
    path('api/auth/login/', views.UserLoginAPIView.as_view(), name='user_login_api'),
    
    # NEW: Wallet API
    path('api/wallet/', views.UserWalletDetailAPIView.as_view(), name='user_wallet_api'),
]
