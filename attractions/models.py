# attractions/models.py
# version: 2.0.0
# REFACTOR: Major schema update.
# - Replaced 'suggested_duration' with 'visiting_hours'.
# - Changed 'category' to ManyToMany.
# - Added 'AttractionAudience' and 'AttractionAmenity' models for multi-select features.

from django.db import models
from core.models import ImageMetadata
from hotels.models import City

# --- 1. دسته‌بندی‌ها (تغییر به چند انتخابی در مدل اصلی) ---
class AttractionCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام دسته‌بندی")
    slug = models.SlugField(unique=True, verbose_name="اسلاگ")
    icon_name = models.CharField(
        max_length=100, 
        default='MapPin',
        verbose_name="نام آیکون (Lucide)",
        help_text="نام دقیق آیکون را از وب‌سایت Lucide.dev کپی کنید."
    )
    
    class Meta:
        verbose_name = "دسته‌بندی جاذبه"
        verbose_name_plural = "دسته‌بندی‌های جاذبه"
    def __str__(self):
        return self.name

# --- 2. مخاطبان مناسب (مدل جدید) ---
class AttractionAudience(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="گروه مخاطب")
    # مثال: خانواده، سالمندان، گردشگران خارجی...
    
    class Meta:
        verbose_name = "گروه مخاطب"
        verbose_name_plural = "گروه‌های مخاطب (مناسب برای)"
    def __str__(self):
        return self.name

# --- 3. امکانات رفاهی (مدل جدید) ---
class AttractionAmenity(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="امکان رفاهی")
    icon_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="نام آیکون (اختیاری)")
    # مثال: سرویس بهداشتی، پارکینگ، ویلچر...

    class Meta:
        verbose_name = "امکان رفاهی جاذبه"
        verbose_name_plural = "امکانات رفاهی جاذبه"
    def __str__(self):
        return self.name

# --- 4. مدل اصلی جاذبه (اصلاح شده) ---
class Attraction(models.Model):
    VISIT_TIME_CHOICES = (
        ('morning', 'صبح'),
        ('afternoon', 'بعد از ظهر'),
        ('evening', 'غروب/شب'),
        ('full_day', 'تمام روز'),
    )

    name = models.CharField(max_length=255, verbose_name="نام جاذبه")
    slug = models.SlugField(unique=True, verbose_name="اسلاگ")
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='attractions', verbose_name="شهر")
    
    # REFACTOR: Changed to ManyToManyField for multi-selection
    categories = models.ManyToManyField(AttractionCategory, related_name='attractions', verbose_name="دسته‌بندی‌ها")
    
    description = models.TextField(verbose_name="توضیحات کامل")
    short_description = models.CharField(max_length=300, blank=True, null=True, verbose_name="توضیحات کوتاه")
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="عرض جغرافیایی")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, verbose_name="طول جغرافیایی")
    
    # REFACTOR: Changed from suggested_duration to visiting_hours
    visiting_hours = models.CharField(max_length=255, blank=True, null=True, verbose_name="ساعات بازدید", help_text="مثال: همه روزه از ۹ صبح تا ۱۷ عصر")
    best_visit_time = models.CharField(max_length=20, choices=VISIT_TIME_CHOICES, blank=True, null=True, verbose_name="بهترین زمان بازدید")
    
    entry_fee = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="هزینه ورودی (تومان)", help_text="۰ به معنی رایگان")
    
    # NEW FIELDS: Multi-select relations
    audiences = models.ManyToManyField(AttractionAudience, blank=True, verbose_name="مناسب برای")
    amenities = models.ManyToManyField(AttractionAmenity, blank=True, verbose_name="امکانات رفاهی")

    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0, verbose_name="امتیاز")
    is_featured = models.BooleanField(default=False, verbose_name="جاذبه برجسته")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین ویرایش")

    class Meta:
        verbose_name = "جاذبه گردشگری"
        verbose_name_plural = "جاذبه‌های گردشگری"
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.city.name})"

class AttractionGallery(ImageMetadata):
    attraction = models.ForeignKey(Attraction, on_delete=models.CASCADE, related_name='images', verbose_name="جاذبه")
    image = models.ImageField(upload_to='attraction_images/', verbose_name="تصویر")
    is_cover = models.BooleanField(default=False, verbose_name="تصویر کاور؟")

    class Meta(ImageMetadata.Meta):
        verbose_name = "تصویر جاذبه"
        verbose_name_plural = "گالری تصاویر جاذبه"
