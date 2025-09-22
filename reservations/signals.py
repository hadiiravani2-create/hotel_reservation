# reservations/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking
from notifications.tasks import send_email_task, send_sms_task
from core.models import SiteSettings

@receiver(post_save, sender=Booking)
def send_booking_notifications(sender, instance, created, **kwargs):
    """
    این سیگنال پس از ذخیره شدن هر رزرو اجرا می‌شود.
    """
    # فقط زمانی اجرا شو که وضعیت 'تایید شده' باشد و قبلاً اطلاع‌رسانی ارسال نشده باشد
    if instance.status == 'confirmed' and not instance.notification_sent:

        site_settings = SiteSettings.objects.first()
        guest = instance.guests.first()

        # آماده‌سازی داده‌ها برای ارسال
        context = {
            "full_name": f"{guest.first_name} {guest.last_name}" if guest else "میهمان گرامی",
            "booking_code": instance.booking_code,
            "hotel_name": instance.room_type.hotel.name,
            "room_name": instance.room_type.name,
            "check_in": instance.check_in,
            "check_out": instance.check_out,
            "total_price": instance.total_price,
            "site_name": site_settings.site_name if site_settings else "سامانه رزرواسیون"
        }

        # ۱. قرار دادن تسک ارسال ایمیل در صف Celery
        if guest and guest.email: # اگر ایمیل وجود داشت
            send_email_task.delay(
                subject=f"تایید رزرو شما با کد {instance.booking_code}",
                text_content=f"رزرو شما با کد {instance.booking_code} با موفقیت تایید شد.",
                html_template_name="notifications/email/booking_confirmation.html",
                recipient_list=[guest.email],
                context=context
            )

        # ۲. قرار دادن تسک ارسال پیامک در صف Celery
        if guest and guest.phone_number: # اگر شماره تماس وجود داشت
            message = f"رزرو شما با کد {instance.booking_code} در {context['hotel_name']} تایید شد. {context['site_name']}"
            send_sms_task.delay(
                recipient_number=guest.phone_number,
                message=message
            )

        # ۳. علامت‌گذاری رزرو برای جلوگیری از ارسال مجدد
        # از .update() استفاده می‌کنیم تا دوباره سیگنال را فعال نکند
        Booking.objects.filter(pk=instance.pk).update(notification_sent=True)
