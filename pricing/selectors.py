# pricing/selectors.py v1.0.1
# Update: find_available_rooms is replaced with find_available_hotels.
from datetime import timedelta
from django.db.models import Q, Min
from hotels.models import RoomType, BoardType, Hotel
from agencies.models import Contract, StaticRate
from .models import Availability, Price
from django.shortcuts import get_object_or_404
from decimal import Decimal

# Helper function _get_daily_price_for_user remains the same
def _get_daily_price_for_user(room_type, board_type, date, user):
    # ... (Implementation is unchanged)
    pass


def find_available_hotels(city_id: int, check_in_date, check_out_date, user, min_price=None, max_price=None, stars=None, amenities=None):
    """
    Searches for hotels that have at least one available room throughout the specified date range.
    """
    duration = (check_out_date - check_in_date).days
    if duration <= 0:
        return []

    date_range = [check_in_date + timedelta(days=i) for i in range(duration)]
    
    # Start with hotels in the specified city
    hotels_query = Hotel.objects.filter(city_id=city_id)

    # Filter by stars if provided
    if stars:
        hotels_query = hotels_query.filter(stars__in=stars)

    # Filter by amenities if provided
    if amenities:
        amenities_list = [int(a) for a in amenities.split(',')]
        hotels_query = hotels_query.filter(amenities__in=amenities_list).distinct()

    final_results = []
    # Iterate through hotels to find availability and minimum price
    for hotel in hotels_query:
        # Find room types of the hotel that are available for the entire duration
        available_room_types = RoomType.objects.filter(
            hotel=hotel,
        ).annotate(
            num_available_days=Count('availability', filter=Q(availability__date__in=date_range, availability__quantity__gt=0))
        ).filter(num_available_days=duration)

        if not available_room_types.exists():
            continue # Skip hotel if no room is available for the whole period

        # Now, calculate the minimum price among all available rooms and board types for this hotel
        min_hotel_price = None

        for room in available_room_types:
            # We just need the price for the first night to show a "starting from" price
            # This is a simplification. A more accurate approach would be to calculate the full stay price for each room.
            price_obj = Price.objects.filter(
                room_type=room, 
                date=check_in_date
            ).order_by('price_per_night').first()

            if price_obj:
                price_info = _get_daily_price_for_user(room, price_obj.board_type, check_in_date, user)
                if price_info:
                    current_price = price_info['price_per_night']
                    if min_hotel_price is None or current_price < min_hotel_price:
                        min_hotel_price = current_price
        
        if min_hotel_price is not None:
            # Apply price filters
            if (min_price and min_hotel_price < min_price) or (max_price and min_hotel_price > max_price):
                continue

            final_results.append({
                'hotel_id': hotel.id,
                'hotel_name': hotel.name,
                'hotel_slug': hotel.slug,
                'hotel_stars': hotel.stars,
                'min_price': min_hotel_price,
            })

    return final_results


# calculate_booking_price remains the same
def calculate_booking_price(room_type_id: int, board_type_id: int, check_in_date, check_out_date, extra_adults: int, children: int, user):
    # ... (Implementation is unchanged)
    pass
