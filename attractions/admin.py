# attractions/admin.py
# version: 2.0.0
# FEATURE: Updated admin for new M2M relations (Audience, Amenity) and categories.

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Attraction, AttractionCategory, AttractionGallery,
    AttractionAudience, AttractionAmenity
)

# --- Inlines ---

class AttractionGalleryInline(admin.TabularInline):
    model = AttractionGallery
    extra = 1
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.image.url)
        return "No Image"
    image_preview.short_description = "پیش‌نمایش"

# --- Admins ---

@admin.register(AttractionCategory)
class AttractionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon_name')
    search_fields = ('name', 'icon_name')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(AttractionAudience)
class AttractionAudienceAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(AttractionAmenity)
class AttractionAmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_name')
    search_fields = ('name', 'icon_name')

@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'best_visit_time', 'rating', 'is_featured')
    list_filter = ('city', 'categories', 'best_visit_time', 'is_featured', 'audiences')
    search_fields = ('name', 'city__name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ('city',)
    
    # FIX: Use filter_horizontal for easy multi-selection
    filter_horizontal = ('categories', 'audiences', 'amenities')
    
    inlines = [AttractionGalleryInline]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'slug', 'city', 'categories', 'is_featured')
        }),
        ('محتوا و زمان‌بندی', {
            'fields': ('description', 'short_description', 'visiting_hours', 'best_visit_time', 'entry_fee', 'rating')
        }),
        ('ویژگی‌ها و امکانات', {
            'fields': ('audiences', 'amenities')
        }),
        ('موقعیت مکانی', {
            'fields': ('latitude', 'longitude'),
            'description': 'لطفاً مختصات دقیق را وارد کنید تا روی نقشه نمایش داده شود.'
        }),
    )
