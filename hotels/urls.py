# hotels/urls.py
# version 2

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# ایجاد روتر و ثبت ویوست‌ها
router = DefaultRouter()
router.register(r'cities', views.CityViewSet, basename='city')
router.register(r'attractions', views.TouristAttractionViewSet, basename='tourist-attraction')
router.register(r'hotels', views.HotelViewSet, basename='hotel')
router.register(r'amenities', views.AmenityViewSet, basename='amenity')
router.register(r'hotel-categories', views.HotelCategoryViewSet, basename='hotel-category')
router.register(r'bed-types', views.BedTypeViewSet, basename='bed-type')
router.register(r'room-categories', views.RoomCategoryViewSet, basename='room-category')
router.register(r'room-types', views.RoomTypeViewSet, basename='room-type')


app_name = 'hotels'

urlpatterns = [
    # آدرس‌های API از روتر
    # CHANGED: Removed redundant 'api/' prefix. Final URL will be /api/cities/
    path('', include(router.urls)),

    # آدرس URL برای دریافت اتاق‌های یک هتل خاص بر اساس slug
    # CHANGED: Removed redundant 'api/' prefix. Final URL will be /api/hotel/<slug:hotel_slug>/rooms/
    path('hotel/<slug:hotel_slug>/rooms/', views.get_rooms_by_hotel_slug, name='hotel_rooms'),
    
]
