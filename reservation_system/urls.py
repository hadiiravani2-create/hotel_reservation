# reservation_system/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views # این خط را اضافه کنید

urlpatterns = [
    path('admin/', admin.site.urls),

    # API های پروژه
    path('pricing/', include('pricing.urls', namespace='pricing')),
    path('reservations/', include('reservations.urls', namespace='reservations')),
    path('', include('core.urls', namespace='core')),

    # API برای لاگین و دریافت توکن
    path('api/auth/login/', views.obtain_auth_token, name='api_token_auth'),
]