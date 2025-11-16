# reservations/signals.py
# version: 1.2.0
# FEATURE: Added signal to handle automated status updates after payment verification.
# CLEANUP: Corrected unreadable Persian comments and strings.

from django.db.models.signals import post_save
from django.dispatch import receiver
import django.dispatch
from .models import Booking, PaymentConfirmation
from notifications.tasks import send_booking_confirmation_email_task, send_sms_task
from core.models import SiteSettings, WalletTransaction
import logging

post_booking_creation = django.dispatch.Signal()

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Booking)
def send_booking_notifications(sender, instance, created, **kwargs):
    """
    Sends confirmation notifications via Email (with PDF) and SMS 
    only when the booking status is changed to 'confirmed'.
    """
    
    # Fire notifications only when status is 'confirmed' and it hasn't been sent before
    if instance.status == 'confirmed' and not instance.notification_sent:
        
        guest = instance.guests.first()
        if not guest:
            logger.warning(f"Booking {instance.booking_code} confirmed but has no guest. Skipping notifications.")
            return

        try:
            # --- 1. Send Confirmation PDF Email ---
            if hasattr(guest, 'email') and guest.email:
                send_booking_confirmation_email_task.delay(
                    booking_id=instance.id,
                    email_type='confirmed' # This will set the subject to 'تاییدیه پرداخت...'
                )
            else:
                logger.warning(f"Booking {instance.booking_code} confirmed, but guest has no email address.")

            # --- 2. Send Confirmation SMS (Existing Logic) ---
            if hasattr(guest, 'phone_number') and guest.phone_number:
                first_booking_room = instance.booking_rooms.first()
                hotel_name = first_booking_room.room_type.hotel.name if first_booking_room else ""
                site_settings = SiteSettings.objects.first()
                site_name = site_settings.site_name if site_settings else "سامانه رزرواسیون"
                
                message = f"رزرو شما با کد {instance.booking_code} در هتل {hotel_name} تایید شد. {site_name}"
                send_sms_task.delay(
                    recipient_number=guest.phone_number,
                    message=message
                )
            
            # Mark as notified to prevent duplicate sends
            Booking.objects.filter(pk=instance.pk).update(notification_sent=True)
            logger.info(f"Submitted 'confirmed' notification tasks for booking {instance.booking_code}")

        except Exception as e:
            logger.error(f"Failed to submit notification tasks for booking {instance.booking_code}: {e}")
            pass

@receiver(post_save, sender=PaymentConfirmation)
def handle_payment_verification(sender, instance, **kwargs):
    """
    Signal handler that triggers after a PaymentConfirmation is saved.
    If 'is_verified' is True, it updates the status AND paid_amount of the related object.
    """
    # Proceed only if the payment has been marked as verified and has a related object
    if instance.is_verified and instance.content_object:
        related_object = instance.content_object

        # Case 1: The payment is for a Booking
        if isinstance(related_object, Booking):
            # Update booking status if it's in a state that can be confirmed by payment.
            # This covers both 'pending' (online) and 'awaiting_confirmation' (offline)
            if related_object.status == 'pending' or related_object.status == 'awaiting_confirmation':
                related_object.status = 'confirmed'
                
                # --- START: PDF Data Fix (Save Paid Amount) ---
                # Set the paid_amount from the verified payment amount
                if instance.payment_amount and instance.payment_amount > 0:
                    related_object.paid_amount = instance.payment_amount
                else:
                    # Fallback if payment_amount wasn't entered by operator
                    related_object.paid_amount = related_object.total_price 
                
                related_object.save(update_fields=['status', 'paid_amount'])
                # --- END: PDF Data Fix ---

        # Case 2: The payment is for a WalletTransaction (deposit)
        elif isinstance(related_object, WalletTransaction):
            # Update transaction status if it's currently pending
            if related_object.status == 'pending':
                related_object.status = 'completed'
                related_object.save(update_fields=['status'])
