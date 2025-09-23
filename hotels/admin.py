# hotels/admin.py

from django.contrib import admin
from .models import (
    City, HotelCategory, Hotel, HotelImage, Amenity,
    RoomCategory, BedType, BoardType, RoomType, RoomImage
)

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    # با نوشتن نام، اسلاگ به صورت خودکار پر می‌شود
    prepopulated_fields = {'slug': ('name',)}

# ثبت مدل‌های ساده
admin.site.register(HotelCategory)
admin.site.register(Amenity)
admin.site.register(RoomCategory)
admin.site.register(BedType)
admin.site.register(BoardType)

# کلاس‌های Inline برای مدیریت گالری تصاویر در همان صفحه هتل/اتاق
class HotelImageInline(admin.TabularInline):
    model = HotelImage
    extra = 1 # تعداد فرم‌های خالی برای آپلود تصویر جدید

class RoomImageInline(admin.TabularInline):
    model = RoomImage
    extra = 1

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'category', 'stars')
    list_filter = ('city', 'category', 'stars')
    search_fields = ('name', 'city__name')
    # گالری تصاویر را به صفحه ویرایش/افزودن هتل اضافه می‌کنیم
    inlines = [HotelImageInline]

@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'hotel', 'category', 'base_capacity')
    list_filter = ('hotel__city', 'hotel', 'category')
    search_fields = ('name', 'hotel__name')
    # ویجت بهتری برای فیلدهای چندانتخابه
    filter_horizontal = ('bed_types',)
    # گالری تصاویر را به صفحه ویرایش/افزودن اتاق اضافه می‌کنیم
    inlines = [RoomImageInline]
