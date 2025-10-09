# hotels/admin.py
# version 3
# Fix: Added search_fields to related models for autocomplete functionality.

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    City, Amenity, Hotel, HotelImage, RoomType, RoomImage,
    HotelCategory, BedType, RoomCategory, TouristAttraction, BoardType
)

class HotelImageInline(admin.TabularInline):
    model = HotelImage
    extra = 1

class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'stars', 'manage_rooms_button')
    list_filter = ('city', 'stars', 'hotel_categories')
    search_fields = ('name', 'city__name')
    inlines = [HotelImageInline]
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ('city', 'amenities', 'hotel_categories')

    def manage_rooms_button(self, obj):
        # Creates a link to the RoomType list, filtered by the current hotel.
        url = (
            reverse("admin:hotels_roomtype_changelist")
            + f"?hotel__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}">مدیریت اتاق‌ها</a>', url)
    
    manage_rooms_button.short_description = "مدیریت اتاق‌ها"
    manage_rooms_button.allow_tags = True


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'hotel', 'base_capacity', 'price_per_night', 'manage_availability_button', 'manage_prices_button')
    list_filter = ('hotel', 'room_categories', 'bed_types')
    search_fields = ('name', 'hotel__name')
    inlines = [RoomImageInline]
    autocomplete_fields = ('hotel', 'amenities', 'room_categories', 'bed_types')

    def manage_availability_button(self, obj):
        # Creates a link to the Availability list, filtered by the current room type.
        url = (
            reverse("admin:pricing_availability_changelist")
            + f"?room_type__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}" style="background-color: #28a745;">مدیریت موجودی</a>', url)

    manage_availability_button.short_description = "موجودی"
    manage_availability_button.allow_tags = True
    
    def manage_prices_button(self, obj):
        # Creates a link to the Price list, filtered by the current room type.
        url = (
            reverse("admin:pricing_price_changelist")
            + f"?room_type__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}" style="background-color: #ffc107; color: #212529;">مدیریت قیمت</a>', url)

    manage_prices_button.short_description = "قیمت‌گذاری"
    manage_prices_button.allow_tags = True


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_featured')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(HotelCategory)
class HotelCategoryAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(RoomCategory)
class RoomCategoryAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(BedType)
class BedTypeAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(BoardType)
class BoardTypeAdmin(admin.ModelAdmin):
    search_fields = ('name', 'code')

admin.site.register(TouristAttraction)
