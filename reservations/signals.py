# FILE: reservations/signals.py
# version: 1.3.0
# FEATURE: Implemented Reconciliation logic. Booking is confirmed only if total verified payments >= total price.
# REFACTOR: Handles multiple offline payments for a single booking.

from django.db.models.signals import post_save
from django.dispatch import receiver
import django.dispatch
from django.db.models import Sum
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType

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
    It recalculates the total paid amount and updates the status based on reconciliation logic.
    """
    # فقط اگر موجودیت مرتبط وجود داشته باشد ادامه بده
    if not instance.content_object:
        return

    related_object = instance.content_object

    # --- Case 1: The payment is for a Booking (Reconciliation Logic) ---
    if isinstance(related_object, Booking):
        booking = related_object
        
        # محاسبه مجموع تمام پرداخت‌های تایید شده برای این رزرو
        # از filter روی خود مدل PaymentConfirmation استفاده می‌کنیم تا به GenericRelation در مدل Booking وابسته نباشیم (برای اطمینان)
        content_type = ContentType.objects.get_for_model(Booking)
        total_verified_paid = PaymentConfirmation.objects.filter(
            content_type=content_type,
            object_id=booking.id,
            is_verified=True
        ).aggregate(
            total=Coalesce(Sum('payment_amount'), Decimal(0))
        )['total']

        # به روز رسانی مبلغ پرداخت شده در رزرو
        if booking.paid_amount != total_verified_paid:
            booking.paid_amount = total_verified_paid
            # فعلاً فقط مبلغ را ذخیره می‌کنیم، وضعیت را در ادامه بررسی می‌کنیم
            booking.save(update_fields=['paid_amount'])

        # --- ماشین وضعیت (State Machine) ---
        
        # 1. اگر کل مبلغ (یا بیشتر) پرداخت شده است -> تایید نهایی
        if booking.paid_amount >= booking.total_price:
            if booking.status != 'confirmed':
                booking.status = 'confirmed'
                booking.save(update_fields=['status'])
                # سیگنال send_booking_notifications به طور خودکار اجرا خواهد شد
        
        # 2. اگر بخشی از مبلغ پرداخت شده اما هنوز بدهکار است -> منتظر تایید (یا منتظر پرداخت مابقی)
        elif booking.paid_amount > 0:
            if booking.status == 'pending':
                booking.status = 'awaiting_confirmation'
                booking.save(update_fields=['status'])
                
        # نکته: اگر پرداخت رد شد (Verified=False) و مجموع پرداختی صفر شد، وضعیت تغییری نمی‌کند
        # تا کاربر بتواند مجدداً تلاش کند یا با همان وضعیت قبل بماند.

    # --- Case 2: The payment is for a WalletTransaction (deposit) ---
    elif isinstance(related_object, WalletTransaction):
        # برای کیف پول منطق ساده‌تر است: اگر تایید شد، وضعیت تراکنش تکمیل می‌شود
        if instance.is_verified and related_object.status == 'pending':
            related_object.status = 'completed'
            related_object.save(update_fields=['status'])
            
            # موجودی کیف پول هم باید آپدیت شود (معمولاً در سیگنالِ خودِ تراکنش هندل می‌شود، اما اینجا هم می‌توان تریگر کرد)
            # فرض بر این است که سیگنال post_save روی WalletTransaction موجودی را اضافه می‌کند
            # یا متدی برای اعمال تراکنش وجود دارد.
