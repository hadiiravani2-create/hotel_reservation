# hotels/models.py
# version: 1.0.1
# FEATURE: Added 'is_suggested' field to Hotel model for homepage display.

from django.db import models
from django.conf import settings


# New abstract model for shared metadata
class ImageMetadata(models.Model):
    """
    Abstract base class for models that require image metadata such as caption and display order.
    Used to implement DRY principle for similar image-related models.
    """
    caption = models.CharField(max_length=255, blank=True, null=True, verbose_name="توضیحات تصویر")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    
    class Meta:
        abstract = True
        ordering = ['order']

# مدل‌های جدید برای دسته‌بندی و ویژگی‌های هتل و اتاق
class TouristAttraction(models.Model):
    # Model for tourist attractions related to a city.
    name = models.CharField(max_length=200, verbose_name="نام جاذبه")
    description = models.TextField(verbose_name="توضیحات", null=True, blank=True)
    city = models.ForeignKey('City', on_delete=models.CASCADE, related_name='attractions', verbose_name="شهر")
    image = models.ImageField(upload_to='attractions/', blank=True, null=True, verbose_name="تصویر")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="عرض جغرافیایی")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="طول جغرافیایی")

    class Meta:
        verbose_name = "جاذبه گردشگری"
        verbose_name_plural = "جاذبه‌های گردشگری"

    def __str__(self):
        return self.name

class HotelCategory(models.Model):
    # Model for categorizing hotels (e.g., Luxury, Budget).
    name = models.CharField(max_length=100, unique=True, verbose_name="نام دسته‌بندی")
    slug = models.SlugField(unique=True, help_text="یکتا و برای آدرس‌دهی مناسب سئو", verbose_name="اسلاگ")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    image = models.ImageField(upload_to='hotel_categories/', blank=True, null=True, verbose_name="تصویر")
    
    class Meta:
        verbose_name = "دسته‌بندی هتل"
        verbose_name_plural = "دسته‌بندی‌های هتل"

    def __str__(self):
        return self.name


class BedType(models.Model):
    # Model for different bed types (e.g., King, Queen, Twin).
    name = models.CharField(max_length=50, unique=True, verbose_name="نوع تخت")
    slug = models.SlugField(unique=True, verbose_name="اسلاگ")

    class Meta:
        verbose_name = "نوع تخت"
        verbose_name_plural = "انواع تخت"

    def __str__(self):
        return self.name

class RoomCategory(models.Model):
    # Model for classifying room types (e.g., Sea View, Balcony).
    name = models.CharField(max_length=100, unique=True, verbose_name="دسته‌بندی اتاق")
    slug = models.SlugField(unique=True, verbose_name="اسلاگ")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    
    class Meta:
        verbose_name = "دسته‌بندی اتاق"
        verbose_name_plural = "دسته‌بندی‌های اتاق"

    def __str__(self):
        return self.name

# مدل‌های اصلی پروژه
class City(models.Model):
    # Main model for representing cities where hotels are located.
    name = models.CharField(max_length=100, unique=True, verbose_name="نام شهر")
    slug = models.SlugField(unique=True, help_text="یکتا و برای آدرس‌دهی مناسب سئو", verbose_name="اسلاگ")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات شهر")
    image = models.ImageField(upload_to='city_landing/', blank=True, null=True, verbose_name="تصویر لندینگ")
    meta_title = models.CharField(max_length=255, blank=True, null=True, verbose_name="عنوان سئو")
    meta_description = models.TextField(blank=True, null=True, verbose_name="توضیحات سئو")
    is_featured = models.BooleanField(default=False, verbose_name="شهر برجسته")
    
    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"

    def __str__(self):
        return self.name


class Amenity(models.Model):
    # Model for hotel and room amenities (e.g., WiFi, Pool).
    name = models.CharField(max_length=100, unique=True, verbose_name="نام امکانات")
    icon = models.ImageField(upload_to='amenity_icons/', blank=True, null=True, verbose_name="آیکون")
    
    class Meta:
        verbose_name = "امکانات رفاهی"
        verbose_name_plural = "امکانات رفاهی"

    def __str__(self):
        return self.name

class Hotel(models.Model):
    # Main hotel model.
    name = models.CharField(max_length=255, verbose_name="نام هتل")
    slug = models.SlugField(unique=True, help_text="یکتا و برای آدرس‌دهی مناسب سئو", verbose_name="اسلاگ")
    stars = models.PositiveSmallIntegerField(default=3, verbose_name="ستاره هتل")
    description = models.TextField(verbose_name="توضیحات هتل", null=True, blank=True)
    address = models.CharField(max_length=500, verbose_name="آدرس")
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="hotels", verbose_name="شهر")
    amenities = models.ManyToManyField(Amenity, blank=True, verbose_name="امکانات رفاهی")
    hotel_categories = models.ManyToManyField(HotelCategory, blank=True, related_name="hotels", verbose_name="دسته‌بندی‌ها")
    is_suggested = models.BooleanField(default=False, verbose_name="هتل پیشنهادی")
    meta_title = models.CharField(max_length=255, blank=True, null=True, verbose_name="عنوان سئو")
    meta_description = models.TextField(blank=True, null=True, verbose_name="توضیحات سئو")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="عرض جغرافیایی")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="طول جغرافیایی")
    check_in_time = models.CharField(max_length=10, blank=True, null=True, verbose_name="زمان ورود")
    check_out_time = models.CharField(max_length=10, blank=True, null=True, verbose_name="زمان خروج")
    contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="شماره تماس")
    contact_email = models.EmailField(blank=True, null=True, verbose_name="ایمیل")
    rules = models.TextField(blank=True, null=True, verbose_name="قوانین هتل")

    # vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hotels") # Todo uncomment

    class Meta:
        verbose_name = "هتل"
        verbose_name_plural = "هتل‌ها"
        unique_together = ('name', 'city') # unique

    def __str__(self):
        return self.name


class RoomType(models.Model):
    # Model defining a specific type of room within a hotel.
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="room_types", verbose_name="هتل")
    name = models.CharField(max_length=100, verbose_name="نام نوع اتاق")
    code = models.CharField(max_length=20, unique=True, verbose_name="کد نوع اتاق")
    description = models.TextField(verbose_name="توضیحات نوع اتاق", null=True, blank=True)
    base_capacity = models.PositiveSmallIntegerField(default=2, verbose_name="ظرفیت پایه (نفر)")
    price_per_night = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="قیمت پایه هر شب (تومان)")

    extra_capacity = models.PositiveSmallIntegerField(default=0, verbose_name="ظرفیت نفر اضافه")
    child_capacity = models.PositiveSmallIntegerField(default=0, verbose_name="ظرفیت کودک")

    extra_person_price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="قیمت هر نفر اضافه (تومان)")
    child_price = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="قیمت هر کودک (تومان)")
    amenities = models.ManyToManyField(Amenity, blank=True, related_name="room_types", verbose_name="امکانات اختصاصی اتاق")
    
    room_categories = models.ManyToManyField(RoomCategory, blank=True, related_name="room_types", verbose_name="دسته‌بندی‌های اتاق")
    bed_types = models.ManyToManyField(BedType, blank=True, related_name="room_types", verbose_name="نوع تخت‌ها")
    
    class Meta:
        verbose_name = "نوع اتاق"
        verbose_name_plural = "انواع اتاق"
        unique_together = ('hotel', 'name') # Enforce unique room type name per hotel

    def __str__(self):
        return f"{self.name} - {self.hotel.name}"

class BoardType(models.Model):
    # Model for meal/board plans (e.g., Breakfast Included (BB), Full Board (FB)).
    name = models.CharField(max_length=100, unique=True, verbose_name="نام سرویس")
    code = models.CharField(max_length=10, unique=True, verbose_name="کد اختصاری (مثلا: BB, FB)")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    class Meta:
        verbose_name = "نوع سرویس"
        verbose_name_plural = "انواع سرویس"

    def __str__(self):
        return self.name

class HotelImage(ImageMetadata):
    # Model for storing images related to a specific hotel. Inherits metadata from ImageMetadata.
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="images", verbose_name="هتل")
    image = models.ImageField(upload_to='hotel_images/', verbose_name="تصویر")
    
    class Meta(ImageMetadata.Meta):
        verbose_name = "تصویر هتل"
        verbose_name_plural = "تصاویر هتل"
        # ordering is inherited from ImageMetadata

class RoomImage(ImageMetadata):
    # Model for storing images related to a specific room type. Inherits metadata from ImageMetadata.
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name="images", verbose_name="نوع اتاق")
    image = models.ImageField(upload_to='room_images/', verbose_name="تصویر")
    
    class Meta(ImageMetadata.Meta):
        verbose_name = "تصویر اتاق"
        verbose_name_plural = "تصاویر اتاق"
        # ordering is inherited from ImageMetadata
