# reservations/admin.py
from django.contrib import admin
from .models import Booking, Guest, BookingRoom
from .forms import BookingForm
from agencies.models import AgencyTransaction
from django.db.models import Sum
from pricing.selectors import calculate_booking_price
from hotels.models import RoomType, BoardType
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory 
from django.urls import path 
from django.shortcuts import redirect 
from django.contrib import messages # استفاده از Messages Framework


class GuestInline(admin.TabularInline):
    model = Guest
    extra = 1
    classes = ('dynamic-guests',)

class BookingRoomInline(admin.TabularInline):
    model = BookingRoom
    extra = 1
    fields = ('room_type', 'board_type', 'quantity', 'adults', 'children')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    form = BookingForm
    list_display = ('booking_code', 'user', 'total_price', 'status', 'check_in', 'check_out')
    list_filter = ('status', 'check_in', 'booking_rooms__room_type__hotel')
    search_fields = ('booking_code', 'user__username', 'guests__last_name')
    inlines = [GuestInline, BookingRoomInline]
    readonly_fields = ('booking_code', 'total_price') 
    list_editable = ('status',)
    
    class Media:
        css = {
            'all': ('admin/css/admin_fixes.css',)
        }
        js = ("admin/js/guest_form.js",) 
    
    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return ('booking_code', 'user', 'total_price') 
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        old_obj = None
        if obj.pk:
            old_obj = Booking.objects.get(pk=obj.pk)

        if not obj.pk and not obj.user:
            obj.user = request.user
            
        if not change:
            try:
                total_price = 0
                
                BookingRoomFormSet = inlineformset_factory(Booking, BookingRoom, fields=('room_type', 'board_type', 'quantity', 'adults', 'children'), extra=1)
                formset = BookingRoomFormSet(request.POST, instance=obj)
                
                if not formset.is_valid():
                    # اگر فرمست اصلی معتبر نبود، Django پیام‌های خطای فیلد را نمایش می‌دهد.
                    raise ValidationError("خطا در ورودی اتاق‌های رزرو شده. لطفاً اطلاعات را بررسی کنید.")
                
                total_guests_count = 0
                
                for inline_form in formset:
                    if inline_form.cleaned_data and not inline_form.cleaned_data.get('DELETE'):
                        room_data = inline_form.cleaned_data
                        room_type = room_data['room_type']
                        board_type = room_data['board_type']
                        quantity = room_data['quantity']
                        extra_adults = room_data['adults'] 
                        children_count = room_data['children']

                        # اعتبارسنجی ظرفیت و محاسبه قیمت
                        max_extra_adults = room_type.extra_capacity * quantity
                        max_children_count = room_type.child_capacity * quantity
                        
                        if extra_adults > max_extra_adults:
                            raise ValidationError(f"تعداد نفرات اضافی ({extra_adults}) برای اتاق {room_type.name} بیشتر از ظرفیت مجاز ({max_extra_adults}) است.")
                        
                        if children_count > max_children_count:
                            raise ValidationError(f"تعداد کودکان ({children_count}) برای اتاق {room_type.name} بیشتر از ظرفیت مجاز ({max_children_count}) است.")

                        total_guests_count += (room_type.base_capacity * quantity) + extra_adults + children_count

                        price_details = calculate_booking_price(
                            room_type_id=room_type.id, board_type_id=board_type.id,
                            check_in_date=form.cleaned_data['check_in'], check_out_date=form.cleaned_data['check_out'],
                            extra_adults=extra_adults, children=children_count, user=request.user
                        )
                        if price_details:
                            total_price += price_details['total_price'] * quantity
                        else:
                            raise ValidationError("قیمت‌گذاری برای یک یا چند اتاق/سرویس در تاریخ‌های انتخابی تعریف نشده است.")
                
                # اعتبارسنجی نهایی تعداد میهمانان
                GuestInlineFormSet = inlineformset_factory(Booking, Guest, fields=('first_name', 'last_name', 'is_foreign', 'national_id', 'passport_number', 'phone_number', 'nationality'), extra=1)
                guest_formset = GuestInlineFormSet(request.POST, instance=obj)
                
                if not guest_formset.is_valid():
                    raise ValidationError("خطا در ورودی‌های میهمانان. لطفاً فیلدهای الزامی را پر کرده و صحت اطلاعات را بررسی کنید.")
                
                valid_guests_count = sum(1 for guest_form in guest_formset if guest_form.cleaned_data and not guest_form.cleaned_data.get('DELETE'))
                
                if valid_guests_count != total_guests_count:
                    raise ValidationError(f"تعداد میهمانان ({valid_guests_count}) باید با ظرفیت کل اتاق‌های رزرو شده ({total_guests_count}) برابر باشد.")
                    
                obj.total_price = total_price
                
            except ValidationError as e:
                # پیام خطا را به کاربر نشان داده و اجرای متد را متوقف می‌کنیم.
                messages.error(request, str(e))
                return # از اجرای super().save_model جلوگیری می‌کند
            
            except Exception as e:
                # برای خطاهای ناشناخته سیستمی (مانند خطای دیتابیس)
                messages.error(request, "خطای سیستمی ناشناخته در محاسبه رزرو. لطفاً با پشتیبانی تماس بگیرید.")
                return # از اجرای super().save_model جلوگیری می‌کند
        
        # اجرای save_model اصلی فقط در صورت عدم وجود خطا
        super().save_model(request, obj, form, change)
        
        # Status Change Logic
        if obj.pk and old_obj and old_obj.status == 'pending' and obj.status == 'confirmed':
             AgencyTransaction.objects.create(
                agency=obj.agency,
                booking=obj,
                amount=obj.total_price,
                transaction_type='payment',
                created_by=request.user,
                description=f"پرداخت دستی رزرو کد {obj.booking_code} توسط ادمین"
            )

    def save_formset(self, request, form, formset, change):
        # این متد باید برای ذخیره واقعی فرمست‌ها فراخوانی شود
        formset.save()
