# reservations/admin.py
from django.contrib import admin
from .models import Booking, Guest, BookingRoom
from .forms import BookingForm
from agencies.models import AgencyTransaction
from django.db.models import Sum
from pricing.selectors import calculate_booking_price
from hotels.models import RoomType, BoardType

class GuestInline(admin.TabularInline):
    model = Guest
    extra = 1
    classes = ('dynamic-guests',)

class BookingRoomInline(admin.TabularInline):
    model = BookingRoom
    extra = 1

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingForm
    list_display = ('booking_code', 'user', 'total_price', 'status', 'check_in', 'check_out')
    list_filter = ('status', 'check_in', 'booking_rooms__room_type__hotel')
    search_fields = ('booking_code', 'user__username', 'guests__last_name')
    inlines = [GuestInline, BookingRoomInline]
    readonly_fields = ('booking_code', 'total_price',)
    list_editable = ('status',)

    class Media:
        css = {
            'all': ('admin/css/admin_fixes.css',)
        }
        js = ("admin/js/booking_form.js", "admin/js/guest_form.js")
    
    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return ('booking_code', 'user', 'total_price',)
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        old_obj = None
        if obj.pk:
            old_obj = Booking.objects.get(pk=obj.pk)

        if not obj.pk and not obj.user:
            obj.user = request.user

        # محاسبه قیمت کل رزرو قبل از ذخیره
        if not obj.pk: # فقط برای رزروهای جدید
            total_price = 0
            
            # دریافت داده‌های rooms از فرم
            booking_rooms = form.cleaned_data.get('booking_rooms', [])
            
            # اطمینان از وجود داده‌های rooms قبل از محاسبه
            if booking_rooms:
                adults = form.cleaned_data.get('adults', 0)
                children = form.cleaned_data.get('children', 0)
                
                # محاسبه قیمت برای هر اتاق
                for room_data in booking_rooms:
                    room_type = RoomType.objects.get(id=room_data['room_type'].id)
                    board_type = BoardType.objects.get(id=room_data['board_type'].id)
                    
                    price_details = calculate_booking_price(
                        room_type_id=room_type.id,
                        board_type_id=board_type.id,
                        check_in_date=form.cleaned_data['check_in'],
                        check_out_date=form.cleaned_data['check_out'],
                        adults=adults,
                        children=children,
                        user=request.user
                    )
                    if price_details:
                        total_price += price_details['total_price'] * room_data['quantity']
                obj.total_price = total_price
            
        super().save_model(request, obj, form, change)

        if old_obj and old_obj.status == 'pending' and obj.status == 'confirmed':
            AgencyTransaction.objects.create(
                agency=obj.agency,
                booking=obj,
                amount=obj.total_price,
                transaction_type='payment',
                created_by=request.user,
                description=f"پرداخت دستی رزرو کد {obj.booking_code} توسط ادمین"
            )

