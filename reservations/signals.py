# reservations/signals.py v1
# Update: Fixed signal logic to support multi-room bookings and prevent AttributeError.
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
    if instance.status == 'confirmed' and not instance.notification_sent:

        # --- START: Critical fix for multi-room structure ---
        # Get the first booked room to access hotel and room details
        first_booking_room = instance.booking_rooms.first()
        if not first_booking_room:
            # If there are no rooms in the booking, do not send notifications
            return

        site_settings = SiteSettings.objects.first()
        guest = instance.guests.first()
        hotel_name = first_booking_room.room_type.hotel.name

        # Prepare a list of all booked rooms for the email context
        booked_rooms_details = [
            f"{br.quantity} x {br.room_type.name} ({br.board_type.name})" 
            for br in instance.booking_rooms.all()
        ]
        # --- END: Critical fix for multi-room structure ---

        context = {
            "full_name": f"{guest.first_name} {guest.last_name}" if guest else "میهمان گرامی",
            "booking_code": instance.booking_code,
            # --- START: Use corrected variables ---
            "hotel_name": hotel_name,
            "booked_rooms": booked_rooms_details, # Pass a list of rooms
            # --- END: Use corrected variables ---
            "check_in": instance.check_in,
            "check_out": instance.check_out,
            "total_price": instance.total_price,
            "site_name": site_settings.site_name if site_settings else "سامانه رزرواسیون"
        }
        
        # We assume the email template is updated to loop through `booked_rooms`
        if guest and hasattr(guest, 'email') and guest.email:
            send_email_task.delay(
                subject=f"تایید رزرو شما با کد {instance.booking_code}",
                text_content=f"رزرو شما با کد {instance.booking_code} در هتل {hotel_name} با موفقیت تایید شد.",
                html_template_name="notifications/email/booking_confirmation.html",
                recipient_list=[guest.email],
                context=context
            )

        # For SMS, we keep it simple
        if guest and hasattr(guest, 'phone_number') and guest.phone_number:
            message = f"رزرو شما با کد {instance.booking_code} در هتل {hotel_name} تایید شد. {context['site_name']}"
            send_sms_task.delay(
                recipient_number=guest.phone_number,
                message=message
            )

        Booking.objects.filter(pk=instance.pk).update(notification_sent=True)
