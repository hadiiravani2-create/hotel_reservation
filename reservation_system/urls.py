# reservation_system/urls.py

from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views
from django.conf.urls.static import static
from django.conf import settings 

urlpatterns = [
    path('admin/', admin.site.urls),

    # API های پروژه
    path('pricing/', include('pricing.urls', namespace='pricing')),
    path('reservations/', include('reservations.urls', namespace='reservations')),
    path('', include('core.urls', namespace='core')),

    # API برای لاگین و دریافت توکن
    path('api/auth/login/', views.obtain_auth_token, name='api_token_auth'),
    path('agencies/', include('agencies.urls', namespace='agencies')),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)