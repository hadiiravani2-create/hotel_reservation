# reservation_system/urls.py

from django.contrib import admin
from django.urls import path, include # `include` را اضافه کنید

urlpatterns = [
    path('admin/', admin.site.urls),
    path('pricing/', include('pricing.urls', namespace='pricing')), # این خط را اضافه کنید
]