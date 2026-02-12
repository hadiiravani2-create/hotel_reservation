# FILE: reservations/signals.py
# version: 1.4.1
# FIX: Restored 'post_booking_creation' signal definition to resolve ImportError.
# FEATURE: Includes both Notification logic and Financial Reconciliation State Machine.

import django.dispatch
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType
import logging

from .models import Booking, PaymentConfirmation
from core.models import SiteSettings, WalletTransaction
from notifications.tasks import send_booking_confirmation_email_task, send_sms_task

# --- 1. Define Custom Signal (This fixed the error) ---
post_booking_creation = django.dispatch.Signal()

logger = logging.getLogger(__name__)

# --- 2. Notification Logic ---
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
            # A. Send Confirmation PDF Email
            if hasattr(guest, 'email') and guest.email:
                send_booking_confirmation_email_task.delay(
                    booking_id=instance.id,
                    email_type='confirmed'
                )
            else:
                logger.warning(f"Booking {instance.booking_code} confirmed, but guest has no email address.")

            # B. Send Confirmation SMS
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

# --- 3. Financial Reconciliation & State Machine Logic ---
@receiver(post_save, sender=PaymentConfirmation)
def handle_payment_verification(sender, instance, **kwargs):
    """
    Smart signal for handling booking status based on financial transactions.
    Triggered after any PaymentConfirmation save/update.
    """
    if not instance.content_object:
        return

    related_object = instance.content_object

    # --- Scenario: Booking Payment ---
    if isinstance(related_object, Booking):
        booking = related_object
        content_type = ContentType.objects.get_for_model(Booking)

        # A. Calculate total 'Verified' payments
        total_verified = PaymentConfirmation.objects.filter(
            content_type=content_type,
            object_id=booking.id,
            is_verified=True
        ).aggregate(
            total=Coalesce(Sum('payment_amount'), Decimal(0))
        )['total']

        # B. Check for 'Pending Review' receipts (Verified=False)
        has_pending_receipts = PaymentConfirmation.objects.filter(
            content_type=content_type,
            object_id=booking.id,
            is_verified=False
        ).exists()

        # Update actual paid amount in DB
        if booking.paid_amount != total_verified:
            booking.paid_amount = total_verified
            booking.save(update_fields=['paid_amount'])

        # --- State Machine Logic ---
        previous_status = booking.status
        new_status = previous_status

        # State 1: Fully Paid -> Confirmed
        if total_verified >= booking.total_price:
            new_status = 'confirmed'
        
        # State 2: Partial/No Payment + Has Pending Receipt -> Awaiting Confirmation
        elif has_pending_receipts:
            new_status = 'awaiting_confirmation'
            
        # State 3: Partial/No Payment + No Pending Receipts
        else:
            if total_verified > 0:
                # Partial payment verified, but still debt remaining -> Awaiting Completion
                # Note: Ensure 'awaiting_completion' is added to STATUS_CHOICES in models.py, 
                # otherwise use 'pending' or 'awaiting_confirmation'.
                # For now, defaulting to 'awaiting_confirmation' if 'awaiting_completion' isn't in model yet.
                new_status = 'awaiting_confirmation' 
            else:
                # No payment, no pending receipts -> Pending
                new_status = 'pending'

        # Apply Status Change
        if new_status != previous_status:
            # Prevent changing status of finalized bookings (cancelled/checked_out)
            if previous_status not in ['cancelled', 'checked_out', 'expired', 'no_capacity']:
                booking.status = new_status
                booking.save(update_fields=['status'])
                logger.info(f"Booking {booking.booking_code} status changed: {previous_status} -> {new_status}")

                # If status became confirmed here, the send_booking_notifications signal will handle the email/sms automatically.

    # --- Scenario: Wallet Transaction ---
    elif isinstance(related_object, WalletTransaction):
        if instance.is_verified and related_object.status == 'pending':
            related_object.status = 'completed'
            related_object.save(update_fields=['status'])
