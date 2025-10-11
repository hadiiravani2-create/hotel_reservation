# pricing/selectors.py
# version: 6.0.4
# CRITICAL FIX: Implemented robust key access in calculate_multi_booking_price using .get() with fallback 
#               to handle the key mismatch between 'adults'/'children' (from BookingRoomSerializer) and 
#               'extra_adults'/'children_count' (from PriceQuoteMultiRoomInputSerializer), resolving the KeyError.

from datetime import timedelta
from django.db.models import Count
from hotels.models import RoomType, BoardType, Hotel
from agencies.models import Contract, StaticRate
from .models import Price
from django.shortcuts import get_object_or_404
from decimal import Decimal
from collections import defaultdict

def _get_daily_price_for_user(room_type: RoomType, board_type: BoardType, date, user):
    """
    Calculates the price for a single room on a specific day for a given user.
    CRITICAL FIX: Removed fallback to RoomType base price. If a daily price (Price object)
    is not defined for this specific (room_type, board_type, date) combination, 
    it means this board type is NOT priced for this day, so return None.
    """
    public_price_obj = Price.objects.filter(room_type=room_type, board_type=board_type, date=date).first()

    if not public_price_obj:
        # If no specific price is set for this day and this board type, 
        # it means this combination is not valid/priced for booking.
        return None
    
    # A daily price is defined, use it.
    final_price = {
        'price_per_night': public_price_obj.price_per_night,
        'extra_person_price': public_price_obj.extra_person_price,
        'child_price': public_price_obj.child_price,
    }

    agency_user = user.agency_profile if hasattr(user, 'agency_profile') else None
    if not user.is_authenticated or not agency_user:
        return final_price

    contract = Contract.objects.filter(
        agency=agency_user.agency,
        start_date__lte=date,
        end_date__gte=date,
        hotel=room_type.hotel,
        is_active=True
    ).order_by('-priority').first()

    if not contract:
        return final_price

    static_rate = StaticRate.objects.filter(contract=contract, room_type=room_type).first()
    if static_rate:
        final_price['price_per_night'] = static_rate.price_per_night
        final_price['extra_person_price'] = static_rate.extra_person_price
        final_price['child_price'] = static_rate.child_price
        return final_price

    if contract.contract_type == 'dynamic' and contract.discount_percentage > 0:
        discount = final_price['price_per_night'] * (contract.discount_percentage / Decimal(100))
        final_price['price_per_night'] -= discount

    return final_price

def find_available_hotels(city_id: int, check_in_date, check_out_date, user, **filters):
    """
    A robust and performant search function using a pre-fetching strategy.
    Solves both the hardcoded BoardType and N+1 performance issues.
    """
    duration = (check_out_date - check_in_date).days
    if duration <= 0:
        return []

    date_range = [check_in_date + timedelta(days=i) for i in range(duration)]

    # Step 1: Get all physically available RoomType IDs. This is a fast query.
    available_room_ids = RoomType.objects.filter(
        hotel__city_id=city_id,
        availabilities__date__in=date_range,
        availabilities__quantity__gt=0
    ).annotate(
        num_available_days=Count('availabilities__date', distinct=True)
    ).filter(
        num_available_days=duration
    ).values_list('id', flat=True)

    if not available_room_ids:
        return []

    # Step 2: Pre-fetch all necessary data in bulk to avoid N+1 queries.
    all_prices = Price.objects.filter(
        room_type_id__in=available_room_ids,
        date__in=date_range
    ).select_related('room_type__hotel', 'board_type').order_by('date')
    
    prices_map = defaultdict(lambda: defaultdict(list))
    for price in all_prices:
        prices_map[price.room_type_id][price.date].append(price)

    # Step 3: In Python, iterate through rooms and calculate the cheapest valid stay price.
    hotel_min_prices = defaultdict(lambda: float('inf'))
    hotel_details = {}

    for room_id in available_room_ids:
        min_room_total_price = float('inf')
        
        # Find all board types available for this room across the ENTIRE stay
        # A board type is valid only if it has a price for EVERY day of the stay.
        board_type_day_counts = defaultdict(int)
        for date in date_range:
            for price_obj in prices_map[room_id][date]:
                board_type_day_counts[price_obj.board_type_id] += 1
        
        valid_board_type_ids = [bt_id for bt_id, count in board_type_day_counts.items() if count == duration]

        if not valid_board_type_ids:
            continue # This room has no consistent pricing (in the Price model) for the whole duration

        # Calculate total price for each valid board type
        for bt_id in valid_board_type_ids:
            current_board_total_price = Decimal(0)
            is_valid_stay = True
            
            # This is a fast loop in memory
            for date in date_range:
                # Find the correct price object from our pre-fetched map
                price_obj_for_day = next((p for p in prices_map[room_id][date] if p.board_type_id == bt_id), None)
                if price_obj_for_day is None: # Should not happen due to our check, but as a safeguard
                    is_valid_stay = False
                    break
                
                # We can reuse _get_daily_price_for_user, but it will re-query.
                price_info = _get_daily_price_for_user(price_obj_for_day.room_type, price_obj_for_day.board_type, date, user)
                
                # START FIX
                if price_info is None: 
                    is_valid_stay = False # Price calculation failed (e.g., due to logic in _get_daily_price_for_user returning None)
                    break # Skip this board type for this room
                # END FIX
                
                current_board_total_price += price_info['price_per_night']

            if is_valid_stay and current_board_total_price < min_room_total_price:
                min_room_total_price = current_board_total_price

        if min_room_total_price == float('inf') or min_room_total_price <= 0: # Ensure minimum price is valid and positive
            continue
            
        avg_price = min_room_total_price / Decimal(duration)
        hotel = all_prices.filter(room_type_id=room_id).first().room_type.hotel
        hotel_id = hotel.id

        if avg_price < hotel_min_prices[hotel_id]:
            hotel_min_prices[hotel_id] = avg_price
            hotel_details[hotel_id] = {'id': hotel_id, 'name': hotel.name, 'slug': hotel.slug, 'stars': hotel.stars}

    # Step 4: Build and filter the final results.
    results = []
    for hotel_id, info in hotel_details.items():
        min_price = hotel_min_prices[hotel_id]
        
        if (filters.get('min_price') and min_price < filters['min_price']) or \
           (filters.get('max_price') and min_price > filters['max_price']):
            continue

        results.append({
            'hotel_id': info['id'],
            'hotel_name': info['name'],
            'hotel_slug': info['slug'],
            'hotel_stars': info['stars'],
            'min_price': min_price,
        })
        
    return results


def calculate_multi_booking_price(booking_rooms, check_in_date, check_out_date, user):
    """
    Calculates the final price for a list of multiple room bookings across the entire stay duration.
    This function processes the list of room data (including extra adults/children) passed by the CreateBookingAPIView.
    """
    # Find RoomType and BoardType once per room/board combination
    room_types_map = {rt.id: rt for rt in RoomType.objects.filter(id__in=[r['room_type_id'] for r in booking_rooms])}
    board_types_map = {bt.id: bt for bt in BoardType.objects.filter(id__in=[r['board_type_id'] for r in booking_rooms])}
    
    duration = (check_out_date - check_in_date).days
    if duration <= 0: return None

    total_booking_price = Decimal(0)
    
    for room_data in booking_rooms:
        # Get room-specific parameters from the list element
        room_type_id = room_data['room_type_id']
        board_type_id = room_data['board_type_id']
        quantity = room_data['quantity']
        
        # CRITICAL FIX: Using .get() with fallbacks to handle both:
        # 1. Booking Flow (keys: 'adults', 'children') - used by reservations/views.py
        # 2. Price Quote Flow (keys: 'extra_adults', 'children_count') - used by pricing/views.py
        extra_adults = room_data.get('adults') or room_data.get('extra_adults') or 0
        children = room_data.get('children') or room_data.get('children_count') or 0

        room_type = room_types_map.get(room_type_id)
        board_type = board_types_map.get(board_type_id)

        if not room_type or not board_type:
            # Should be caught by serializer, but as a safeguard
            return None 

        # Calculate price for this single room selection (all nights, all quantities, all extras)
        room_selection_price = Decimal(0)
        
        for i in range(duration):
            current_date = check_in_date + timedelta(days=i)
            price_info = _get_daily_price_for_user(room_type, board_type, current_date, user)
            
            if price_info is None:
                # If any day is unpriced, the whole booking is invalid
                return None

            # Calculate daily total price for ALL quantities and ALL extras for THIS room type
            # Must ensure extra_adults/children are cast to Decimal if they come as int (which they should)
            daily_base_price_total = price_info['price_per_night'] * quantity
            # Ensure multiplication is safe (though extra_adults/children should be numbers)
            daily_extra_adults_cost = Decimal(extra_adults) * price_info['extra_person_price'] * quantity
            daily_children_cost = Decimal(children) * price_info['child_price'] * quantity
            
            room_selection_price += daily_base_price_total + daily_extra_adults_cost + daily_children_cost

        # Add the total price for this room selection to the overall booking total
        total_booking_price += room_selection_price

    return {
        # The view only requires total_price from this multi-room calculation
        "total_price": total_booking_price
    }
