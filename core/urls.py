# core/urls.py
# version: 1.0.5
# FEATURE: Added the API endpoint for initiating a wallet deposit.

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
    
    # Wallet APIs
    path('api/wallet/', views.UserWalletDetailAPIView.as_view(), name='user_wallet_api'),
    path('api/wallet/initiate-deposit/', views.InitiateWalletDepositAPIView.as_view(), name='initiate_wallet_deposit_api'),
]
