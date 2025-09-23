# hotels/models.py

from django.db import models

class City(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام شهر")
    slug = models.SlugField(unique=True, allow_unicode=True, verbose_name="اسلاگ (URL)")
    hero_image = models.ImageField(upload_to='city_hero/', blank=True, null=True, verbose_name="تصویر اصلی صفحه")
    intro_text = models.TextField(blank=True, null=True, verbose_name="متن معرفی شهر")
    seo_title = models.CharField(max_length=255, blank=True, null=True, verbose_name="عنوان سئو")
    meta_description = models.TextField(blank=True, null=True, verbose_name="توضیحات متا (سئو)")
    
    class Meta:
        verbose_name = "شهر"
        verbose_name_plural = "شهرها"

    def __str__(self): 
        return self.name

class HotelCategory(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="نام دسته‌بندی") # هتل، متل، ...
    
    class Meta:
        verbose_name = "دسته‌بندی هتل"
        verbose_name_plural = "دسته‌بندی‌های هتل"

    def __str__(self): 
        return self.name

class Hotel(models.Model):
    name = models.CharField(max_length=255, verbose_name="نام هتل")
    category = models.ForeignKey(HotelCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="دسته‌بندی هتل")
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="hotels", verbose_name="شهر")
    stars = models.PositiveSmallIntegerField(default=3, verbose_name="ستاره")
    address = models.TextField(verbose_name="آدرس")
    
    class Meta:
        verbose_name = "هتل"
        verbose_name_plural = "هتل‌ها"

    def __str__(self): 
        return self.name

class HotelImage(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="gallery")
    image = models.ImageField(upload_to='hotel_gallery/')
    caption = models.CharField(max_length=200, blank=True)
    
    class Meta:
        verbose_name = "تصویر هتل"
        verbose_name_plural = "گالری تصاویر هتل"

class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام امکانات")
    icon_class = models.CharField(max_length=50, blank=True, null=True, verbose_name="کلاس آیکون")
    
    class Meta:
        verbose_name = "امکانات رفاهی"
        verbose_name_plural = "امکانات رفاهی"
        
    def __str__(self): 
        return self.name

class RoomCategory(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="نام دسته‌بندی اتاق") # استاندارد، سوئیت، ...
    
    class Meta:
        verbose_name = "دسته‌بندی اتاق"
        verbose_name_plural = "دسته‌بندی‌های اتاق"

    def __str__(self): 
        return self.name

class BedType(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="نوع تخت") # سینگل، دبل، ...
    
    class Meta:
        verbose_name = "نوع تخت"
        verbose_name_plural = "انواع تخت"

    def __str__(self): 
        return self.name

class BoardType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="نام سرویس")
    code = models.CharField(max_length=10, unique=True, verbose_name="کد اختصاری (مثلا: BB, FB)")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")

    class Meta:
        verbose_name = "نوع سرویس"
        verbose_name_plural = "انواع سرویس"

    def __str__(self):
        return self.name
        
class RoomType(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="room_types", verbose_name="هتل")
    name = models.CharField(max_length=100, verbose_name="نام نوع اتاق")
    main_image = models.ImageField(upload_to='room_main_images/', blank=True, null=True, verbose_name="تصویر اصلی اتاق")
    category = models.ForeignKey(RoomCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="دسته‌بندی اتاق")
    bed_types = models.ManyToManyField(BedType, blank=True, verbose_name="انواع تخت")
    base_capacity = models.PositiveSmallIntegerField(default=2, verbose_name="ظرفیت پایه")
    extra_capacity = models.PositiveSmallIntegerField(default=0, verbose_name="ظرفیت نفر اضافه")
    
    class Meta:
        verbose_name = "نوع اتاق"
        verbose_name_plural = "انواع اتاق"
        
    def __str__(self): 
        return f"{self.name} - {self.hotel.name}"
            
class RoomImage(models.Model):
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name="gallery")
    image = models.ImageField(upload_to='room_gallery/')
    
    class Meta:
        verbose_name = "تصویر اتاق"
        verbose_name_plural = "گالری تصاویر اتاق"
