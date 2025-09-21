# your_project/urls.py

from django.contrib import admin
from django.urls import path
from django.conf import settings          # این import را چک کنید
from django.conf.urls.static import static  # این import را هم چک کنید

urlpatterns = [
    path('admin/', admin.site.urls),
    # ... سایر آدرس‌های شما
]

# این قسمت بسیار مهم است 👇
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)