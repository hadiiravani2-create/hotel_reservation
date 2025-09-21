# reservations/admin.py
from django.contrib import admin
from .models import Booking, Guest
from .forms import BookingForm

class GuestInline(admin.TabularInline):
    model = Guest
    extra = 1
    # یک کلاس CSS به هر ردیف اضافه می‌کنیم تا جاوا اسکریپت ما آن را پیدا کند
    classes = ('dynamic-guests',)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingForm
    list_display = ('booking_code', 'user', 'room_type', 'check_in', 'check_out', 'status', 'total_price')
    list_filter = ('status', 'check_in', 'room_type__hotel')
    search_fields = ('booking_code', 'user__username', 'guests__last_name')
    inlines = [GuestInline]
    readonly_fields = ('booking_code',)

    class Media:
        # هر دو فایل استایل و جاوا اسکریپت را اضافه می‌کنیم
        css = {
            'all': ('admin/css/admin_fixes.css',)
        }
        js = ("admin/js/booking_form.js", "admin/js/guest_form.js")

    def get_readonly_fields(self, request, obj=None):
        # اگر کاربر سوپر یوزر نباشد، فیلد user را فقط خواندنی کن
        if not request.user.is_superuser:
            return ('booking_code', 'user',)
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        # اگر رزرو جدید بود و کاربر برای آن مشخص نشده بود، کاربر فعلی را قرار بده
        if not obj.pk and not obj.user:
            obj.user = request.user
        super().save_model(request, obj, form, change)