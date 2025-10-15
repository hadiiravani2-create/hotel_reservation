# reservation_system/urls.py
# version: 1.0.2
# REFACTOR: Standardized API URL for 'hotels' app under a consistent '/api/hotels/' prefix.

from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),

    # Project APIs
    path('pricing/', include('pricing.urls', namespace='pricing')),
    path('reservations/', include('reservations.urls', namespace='reservations')),
    path('', include('core.urls', namespace='core')),
    # Correctly prefix all hotel-related APIs with /api/hotels/
    path('api/hotels/', include('hotels.urls', namespace='hotels')),

    # API for login and token retrieval
    path('api/auth/login/', views.obtain_auth_token, name='api_token_auth'),
    path('agencies/', include('agencies.urls', namespace='agencies')),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
