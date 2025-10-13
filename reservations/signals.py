# reservations/signals.py v1.1
# Update: Added try-except block around Celery task calls to prevent Admin transaction failure 
#         due to Celery/Kombu Redis initialization errors ('NoneType' object has no attribute 'Redis').

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking
from notifications.tasks import send_email_task, send_sms_task
from core.models import SiteSettings
import logging 

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Booking)
def send_booking_notifications(sender, instance, created, **kwargs):
    """
    این سیگنال پس از ذخیره شدن هر رزرو اجرا می‌شود.
    Sends confirmation notifications via email and SMS if the booking is confirmed.
    """
    # Check if status changed to confirmed and notifications haven't been sent yet
    if instance.status == 'confirmed' and not instance.notification_sent:

        # --- Get necessary data ---
        # Get the first booked room to access hotel and room details
        first_booking_room = instance.booking_rooms.first()
        if not first_booking_room:
            # If there are no rooms in the booking, do not send notifications
            logger.warning(f"Booking {instance.booking_code} confirmed but has no rooms.")
            return

        site_settings = SiteSettings.objects.first()
        guest = instance.guests.first()
        hotel_name = first_booking_room.room_type.hotel.name

        # Prepare a list of all booked rooms for the email context
        booked_rooms_details = [
            f"{br.quantity} x {br.room_type.name} ({br.board_type.name})" 
            for br in instance.booking_rooms.all()
        ]
        
        context = {
            "full_name": f"{guest.first_name} {guest.last_name}" if guest else "میهمان گرامی",
            "booking_code": instance.booking_code,
            "hotel_name": hotel_name,
            "booked_rooms": booked_rooms_details, 
            "check_in": instance.check_in,
            "check_out": instance.check_out,
            "total_price": instance.total_price,
            "site_name": site_settings.site_name if site_settings else "سامانه رزرواسیون"
        }
        
        try:
            # Attempt to send Email
            if guest and hasattr(guest, 'email') and guest.email:
                send_email_task.delay(
                    subject=f"تایید رزرو شما با کد {instance.booking_code}",
                    text_content=f"رزرو شما با کد {instance.booking_code} در هتل {hotel_name} با موفقیت تایید شد.",
                    html_template_name="notifications/email/booking_confirmation.html",
                    recipient_list=[guest.email],
                    context=context
                )

            # Attempt to send SMS
            if guest and hasattr(guest, 'phone_number') and guest.phone_number:
                message = f"رزرو شما با کد {instance.booking_code} در هتل {hotel_name} تایید شد. {context['site_name']}"
                send_sms_task.delay(
                    recipient_number=guest.phone_number,
                    message=message
                )
            
            # If task submissions succeeded, update notification_sent to prevent repeated submissions.
            Booking.objects.filter(pk=instance.pk).update(notification_sent=True)

        except Exception as e:
            # CRITICAL FIX: Catch any exception (including the AttributeError related to Redis) 
            # and log it. This allows the Django Admin save operation to complete successfully.
            logger.error(f"Failed to submit notification tasks for booking {instance.booking_code}. Admin save allowed to proceed: {e}")
            # notification_sent remains False, allowing an external monitor/retry mechanism to handle it later.
            pass
