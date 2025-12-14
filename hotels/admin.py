# hotels/admin.py
# version: 3.0.1
# FIX: Replaced autocomplete with filter_horizontal for better ManyToMany UX in HotelAdmin.
# FEATURE: Added 'is_suggested' field to HotelAdmin for homepage management.

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import (
    City, Amenity, Hotel, HotelImage, RoomType, RoomImage,
    HotelCategory, BedType, RoomCategory, BoardType
)
from services.models import HotelService

class HotelImageInline(admin.TabularInline):
    model = HotelImage
    extra = 1
    # Provides a read-only thumbnail of the image in the admin inline view.
    readonly_fields = ('image_thumbnail',)
    
    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.image.url)
        return "No Image"
    image_thumbnail.short_description = 'Thumbnail'


class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'stars','is_online', 'is_suggested', 'manage_rooms_button')
    list_filter = ('is_online','city', 'stars', 'hotel_categories', 'is_suggested')
    search_fields = ('name', 'city__name')
    inlines = [HotelImageInline]
    prepopulated_fields = {'slug': ('name',)}
    
    # Use autocomplete for ForeignKey with many options
    autocomplete_fields = ('city',) 
    
    # Use filter_horizontal for a better ManyToMany selection interface
    filter_horizontal = ('amenities', 'hotel_categories',)

    def manage_rooms_button(self, obj):
        # Creates a link to the RoomType list, filtered by the current hotel.
        url = (
            reverse("admin:hotels_roomtype_changelist")
            + f"?hotel__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}">مدیریت اتاق‌ها</a>', url)
    
    manage_rooms_button.short_description = "اتاق‌ها"

class HotelServiceInline(admin.TabularInline):
    """
    Allows managing hotel services directly from the hotel's admin page.
    """
    model = HotelService
    extra = 1 # Number of empty forms to display
    autocomplete_fields = ('service_type',) # If you have many service types


class HotelAdmin(admin.ModelAdmin):
    # ... your existing list_display, search_fields, etc.
    
    # --- 3. Add the inline to the HotelAdmin ---
    inlines = [
        # ... any other inlines you might have,
        HotelServiceInline
    ]

@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'hotel', 'base_capacity', 'price_per_night', 'manage_availability_button', 'manage_prices_button')
    list_filter = ('hotel', 'room_categories', 'bed_types')
    search_fields = ('name', 'hotel__name')
    inlines = [RoomImageInline]
    
    autocomplete_fields = ('hotel',)
    filter_horizontal = ('amenities', 'room_categories', 'bed_types',)

    def manage_availability_button(self, obj):
        # Creates a link to the Availability list, filtered by the current room type.
        url = (
            reverse("admin:pricing_availability_changelist")
            + f"?room_type__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}" style="background-color: #28a745;">موجودی</a>', url)

    manage_availability_button.short_description = "موجودی"
    
    def manage_prices_button(self, obj):
        # Creates a link to the Price list, filtered by the current room type.
        url = (
            reverse("admin:pricing_price_changelist")
            + f"?room_type__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}" style="background-color: #ffc107; color: #212529;">قیمت‌گذاری</a>', url)

    manage_prices_button.short_description = "قیمت‌گذاری"


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    # Updated list_display to show coordinates
    list_display = ('name', 'is_featured', 'latitude', 'longitude')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    
    # Optional: Organize fields
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'is_featured')
        }),
        ('محتوا', {
            'fields': ('description', 'image')
        }),
        ('موقعیت مکانی', {
            'fields': ('latitude', 'longitude'),
            'description': 'مرکز نقشه در صفحه شهر روی این مختصات تنظیم می‌شود.'
        }),
        ('سئو', {
            'fields': ('meta_title', 'meta_description')
        }),
    )

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

admin.site.register(HotelImage)
admin.site.register(RoomImage)
