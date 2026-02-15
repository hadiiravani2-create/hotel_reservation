# reservation_system/urls.py
# version: 2.0.0
# FEATURE: Added JWT Authentication endpoints (TokenObtainPairView, TokenRefreshView).
# REFACTOR: Consolidated all auth-related paths under 'api/auth/'.

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

# --- JWT Imports ---
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
# -------------------

# Admin Panel Customization
admin.site.site_header = "پنل مدیریت سامانه رزرو هتل میری سفر"
admin.site.site_title = "مدیریت میری سفر"
admin.site.index_title = "به پنل مدیریت خوش آمدید"

urlpatterns = [
    # 1. Admin Panel
    path('Djadmin/', admin.site.urls),

    # 2. JWT Authentication (Modern Auth)
    # این مسیرها برای لاگین و رفرش توکن ضروری هستند
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 3. Core & Business Logic APIs
    path('pricing/', include('pricing.urls', namespace='pricing')),
    path('reservations/', include('reservations.urls', namespace='reservations')),
    path('', include('core.urls', namespace='core')),
    
    # 4. Hotels & Attractions
    path('api/hotels/', include('hotels.urls', namespace='hotels')),
    path('api/attractions/', include('attractions.urls')),

    # 5. Agencies & Services
    path('agencies/', include('agencies.urls', namespace='agencies')),
    path('api/services/', include('services.urls')),
    path('api/cancellations/', include('cancellations.urls', namespace='cancellations')),
]

# Static & Media files serving in Debug mode
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
