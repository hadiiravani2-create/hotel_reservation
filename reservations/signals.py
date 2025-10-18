# reservations/signals.py
# version: 1.2.0
# FEATURE: Added signal to handle automated status updates after payment verification.
# CLEANUP: Corrected unreadable Persian comments and strings.

from django.db.models.signals import post_save
from django.dispatch import receiver
import django.dispatch
from .models import Booking, PaymentConfirmation
from notifications.tasks import send_email_task, send_sms_task
from core.models import SiteSettings, WalletTransaction
import logging

post_booking_creation = django.dispatch.Signal()

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Booking)
def send_booking_notifications(sender, instance, created, **kwargs):
    """
    این سیگنال پس از ذخیره شدن هر رزرو اجرا می‌شود.
    Sends confirmation notifications via email and SMS if the booking is confirmed.
    """
    if instance.status == 'confirmed' and not instance.notification_sent:
        first_booking_room = instance.booking_rooms.first()
        if not first_booking_room:
            logger.warning(f"Booking {instance.booking_code} confirmed but has no rooms.")
            return

        site_settings = SiteSettings.objects.first()
        guest = instance.guests.first()
        hotel_name = first_booking_room.room_type.hotel.name

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
            if guest and hasattr(guest, 'email') and guest.email:
                send_email_task.delay(
                    subject=f"تایید رزرو شما با کد {instance.booking_code}",
                    text_content=f"رزرو شما با کد {instance.booking_code} در هتل {hotel_name} با موفقیت تایید شد.",
                    html_template_name="notifications/email/booking_confirmation.html",
                    recipient_list=[guest.email],
                    context=context
                )

            if guest and hasattr(guest, 'phone_number') and guest.phone_number:
                message = f"رزرو شما با کد {instance.booking_code} در هتل {hotel_name} تایید شد. {context['site_name']}"
                send_sms_task.delay(
                    recipient_number=guest.phone_number,
                    message=message
                )
            
            Booking.objects.filter(pk=instance.pk).update(notification_sent=True)
        except Exception as e:
            logger.error(f"Failed to submit notification tasks for booking {instance.booking_code}: {e}")
            pass

@receiver(post_save, sender=PaymentConfirmation)
def handle_payment_verification(sender, instance, **kwargs):
    """
    Signal handler that triggers after a PaymentConfirmation is saved.
    If 'is_verified' is True, it updates the status of the related object.
    """
    # Proceed only if the payment has been marked as verified and has a related object
    if instance.is_verified and instance.content_object:
        related_object = instance.content_object

        # Case 1: The payment is for a Booking
        if isinstance(related_object, Booking):
            # Update booking status if it's in a state that can be confirmed by payment.
            # This covers both online bookings ('pending') and offline ones approved by an operator.
            if related_object.status == 'pending':
                related_object.status = 'confirmed'
                related_object.save(update_fields=['status'])

        # Case 2: The payment is for a WalletTransaction (deposit)
        elif isinstance(related_object, WalletTransaction):
            # Update transaction status if it's currently pending
            if related_object.status == 'pending':
                related_object.status = 'completed'
                related_object.save(update_fields=['status'])
