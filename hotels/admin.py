# hotels/admin.py

from django.contrib import admin
from .models import (
    City, Amenity, Hotel, RoomType, BoardType,
    TouristAttraction, HotelCategory, BedType, RoomCategory,
    HotelImage, RoomImage
)

# Inlines برای مدیریت تصاویر
class HotelImageInline(admin.TabularInline):
    model = HotelImage
    extra = 1

class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1

# ثبت مدل‌های جدید
@admin.register(TouristAttraction)
class TouristAttractionAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'latitude', 'longitude')
    list_filter = ('city',)
    search_fields = ('name', 'description')

@admin.register(HotelCategory)
class HotelCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(BedType)
class BedTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(RoomCategory)
class RoomCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

# به‌روزرسانی مدیریت مدل‌های موجود
@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_featured')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'stars', 'contact_phone')
    search_fields = ('name', 'address', 'city__name')
    list_filter = ('city', 'stars', 'hotel_categories')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [HotelImageInline]
    filter_horizontal = ('amenities', 'hotel_categories',)

@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'hotel', 'base_capacity', 'extra_capacity', 'child_capacity')
    search_fields = ('name', 'hotel__name')
    list_filter = ('hotel', 'hotel__city')
    inlines = [RoomImageInline]
    filter_horizontal = ('amenities', 'room_categories', 'bed_types',)

@admin.register(BoardType)
class BoardTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
