# hotel_reservation/urls.py
# Version: 1

from django.contrib import admin
from django.urls import path, include
from django.conf import settings  # Import settings
from django.conf.urls.static import static  # Import static helper

urlpatterns = [
    # Jazzmin and admin URLs
    path('admin/', admin.site.urls),
    # Your project URLs
    # path('', include('your_app.urls')),
]

# ******* BEGIN FIX FOR SERVING STATIC/MEDIA FILES IN DEVELOPMENT *******
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # If you also have media files:
    # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# ******* END FIX FOR SERVING STATIC/MEDIA FILES IN DEVELOPMENT *******
