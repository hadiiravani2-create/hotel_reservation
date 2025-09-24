# reservations/admin.py
from django.contrib import admin
from .models import Booking, Guest, BookingRoom
from .forms import BookingForm
from agencies.models import AgencyTransaction

class GuestInline(admin.TabularInline):
    model = Guest
    extra = 1
    # یک کلاس CSS به هر ردیف اضافه می‌کنیم تا جاوا اسکریپت ما آن را پیدا کند
    classes = ('dynamic-guests',)

class BookingRoomInline(admin.TabularInline):
    model = BookingRoom
    extra = 1
    readonly_fields = ('room_type', 'quantity')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingForm
    list_display = ('booking_code', 'user', 'total_price', 'status', 'check_in', 'check_out')
    list_filter = ('status', 'check_in', 'booking_rooms__room_type__hotel')
    search_fields = ('booking_code', 'user__username', 'guests__last_name')
    inlines = [GuestInline, BookingRoomInline]
    readonly_fields = ('booking_code', 'total_price',)
    list_editable = ('status',) # اضافه شدن status به فیلدهای قابل ویرایش

    class Media:
        # هر دو فایل استایل و جاوا اسکریپت را اضافه می‌کنیم
        css = {
            'all': ('admin/css/admin_fixes.css',)
        }
        js = ("admin/js/booking_form.js", "admin/js/guest_form.js")

    def get_readonly_fields(self, request, obj=None):
        # اگر کاربر سوپر یوزر نباشد، فیلد user را فقط خواندنی کن
        if not request.user.is_superuser:
            return ('booking_code', 'user', 'total_price',)
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        # بررسی وضعیت رزرو قبلی قبل از ذخیره شدن
        old_obj = None
        if obj.pk:
            old_obj = Booking.objects.get(pk=obj.pk)

        # اگر رزرو جدید بود و کاربر برای آن مشخص نشده بود، کاربر فعلی را قرار بده
        if not obj.pk and not obj.user:
            obj.user = request.user
        
        super().save_model(request, obj, form, change)

        # اگر وضعیت رزرو از 'pending' به 'confirmed' تغییر کرد، تراکنش پرداخت را ثبت کن
        if old_obj and old_obj.status == 'pending' and obj.status == 'confirmed':
            # تراکنش پرداخت دستی را ثبت می‌کند.
            AgencyTransaction.objects.create(
                agency=obj.agency,
                booking=obj,
                amount=obj.total_price,
                transaction_type='payment',
                created_by=request.user,
                description=f"پرداخت دستی رزرو کد {obj.booking_code} توسط ادمین"
            )
