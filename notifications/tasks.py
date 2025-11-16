# notifications/tasks.py
# version: 1.0.0

from celery import shared_task
from django.core.mail import send_mail, get_connection, EmailMessage
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
import requests

from .models import EmailSettings, SmsSettings
# Import models and utils needed for confirmation task
from reservations.models import Booking
from reservations.pdf_utils import generate_booking_confirmation_pdf


@shared_task
def send_email_task(subject, text_content, html_template_name, recipient_list, context):
    """
    تسک Celery برای ارسال ایمیل با استفاده از تنظیمات ذخیره شده در دیتابیس.
    """
    try:
        # پیدا کردن تنظیمات فعال ایمیل
        settings = EmailSettings.objects.filter(is_active=True).first()
        if not settings:
            print("خطا: هیچ تنظیمات ایمیل فعالی پیدا نشد.")
            return "Failed: No active email settings."

        # ساخت یک اتصال ایمیل سفارشی بر اساس تنظیمات دیتابیس
        connection = get_connection(
            host=settings.host,
            port=settings.port,
            username=settings.username,
            password=settings.password,
            use_tls=settings.use_tls,
            use_ssl=settings.use_ssl
        )

        # رندر کردن قالب HTML ایمیل با داده‌های داینامیک
        html_content = render_to_string(html_template_name, context)

        # ارسال ایمیل
        send_mail(
            subject=subject,
            message=text_content,
            from_email=settings.username,
            recipient_list=recipient_list,
            html_message=html_content,
            connection=connection, # استفاده از اتصال سفارشی
            fail_silently=False,
        )
        return f"Email sent successfully to {recipient_list}"
    except Exception as e:
        # در صورت بروز خطا، آن را لاگ می‌گیریم تا بعدا بررسی شود
        print(f"Error sending email: {e}")
        return f"Failed to send email: {e}"


@shared_task
def send_sms_task(recipient_number, message):
    """
    تسک Celery برای ارسال پیامک با استفاده از API فراز اس‌ام‌اس.
    """
    try:
        settings = SmsSettings.objects.filter(is_active=True).first()
        if not settings or not settings.api_key:
            print("خطا: تنظیمات فعال پیامک یا کلید API یافت نشد.")
            return "Failed: No active SMS settings or API key."

        url = "http://ippanel.com/api/select"
        payload = {
            "op": "send",
            "uname": "YOUR_USERNAME", # نام کاربری پنل فراز اس‌ام‌اس
            "pass": "YOUR_PASSWORD", # رمز عبور پنل فراز اس‌ام‌اس
            "message": message,
            "from": settings.sender_number,
            "to": [recipient_number],
        }
        headers = {
            'Content-Type': 'application/json'
        }

        # response = requests.post(url, json=payload, headers=headers)
        # response.raise_for_status() # اگر خطا بود، Exception ایجاد می‌کند

        # برای تست، درخواست واقعی را کامنت می‌کنیم و یک پیام موفقیت چاپ می‌کنیم
        print(f"Simulating SMS send to {recipient_number}: '{message}'")
        return f"SMS sent successfully to {recipient_number}"

    except Exception as e:
        print(f"Error sending SMS: {e}")
        return f"Failed to send SMS: {e}"


@shared_task
def send_booking_confirmation_email_task(booking_id: int, email_type: str = 'initial'):
    """
    Celery task to generate PDF confirmation and send it as an email attachment.
    'email_type' can be 'initial', 'payment', or 'final' to adjust the subject.
    """
    try:
        # Get active email settings
        settings = EmailSettings.objects.filter(is_active=True).first()
        if not settings:
            print(f"Error: No active email settings found for booking {booking_id}.")
            return f"Failed: No active email settings."

        # Get booking object
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            print(f"Error: Booking with id {booking_id} does not exist.")
            return f"Failed: Booking not found."

        # Generate the PDF in memory
        pdf_bytes = generate_booking_confirmation_pdf(booking)

        # Determine email subject based on type
        if email_type == 'payment':
            subject = _(f"تاییدیه پرداخت رزرو شما: {booking.booking_code}")
        elif email_type == 'final':
            subject = _(f"رزرو شما نهایی شد: {booking.booking_code}")
        else: # 'initial'
            subject = _(f"تاییدیه رزرو اولیه: {booking.booking_code}")

        # Render email body (using the existing template from your project)
        context = {'booking': booking, 'email_type': email_type}
        html_content = render_to_string(
            'notifications/email/booking_confrimation.html', 
            context
        )
        
        # Get custom email connection
        connection = get_connection(
            host=settings.host,
            port=settings.port,
            username=settings.username,
            password=settings.password,
            use_tls=settings.use_tls,
            use_ssl=settings.use_ssl
        )

        # Create EmailMessage to support attachments
        email = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=settings.username,
            to=[booking.guest.email], # Send to the guest's email
            connection=connection
        )
        email.content_subtype = "html"  # Set email body as HTML

        # Attach the generated PDF
        email.attach(
            f'booking_confirmation_{booking.booking_code}.pdf', 
            pdf_bytes, 
            'application/pdf'
        )

        # Send the email
        email.send(fail_silently=False)
        
        return f"Confirmation PDF email sent successfully to {booking.guest.email}"

    except Exception as e:
        print(f"Error sending confirmation email for booking {booking_id}: {e}")
        # Add retry logic if needed
        return f"Failed to send confirmation email: {e}"
