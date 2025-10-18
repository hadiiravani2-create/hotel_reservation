# In services/signals.py
from django.dispatch import receiver
from reservations.signals import post_booking_creation
from .models import HotelService, BookedService
from decimal import Decimal

@receiver(post_booking_creation)
def handle_selected_services(sender, **kwargs):
    booking = kwargs.get('booking')
    request_data = kwargs.get('request_data')
    selected_services = request_data.get('selected_services', [])

    if not selected_services:
        return

    total_services_price = Decimal(0)

    for service_data in selected_services:
        service_id = service_data.get('id')
        quantity = service_data.get('quantity', 1)
        details = service_data.get('details')

        try:
            hotel_service = HotelService.objects.get(id=service_id, hotel=booking.booking_rooms.first().room_type.hotel)

            # Price calculation logic
            price = hotel_service.price * quantity # Simplified logic

            BookedService.objects.create(
                booking=booking,
                hotel_service=hotel_service,
                quantity=quantity,
                total_price=price,
                details=details
            )
            total_services_price += price
        except HotelService.DoesNotExist:
            continue # Or log an error

    # Atomically update the booking's total price
    if total_services_price > 0:
        booking.total_price += total_services_price
        booking.save(update_fields=['total_price'])
