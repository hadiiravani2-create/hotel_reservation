# cancellations/services.py
# version: 1.0.0
# FEATURE: Implemented the core cancellation fee calculation logic.

import datetime
from decimal import Decimal
from reservations.models import Booking  # Assuming Booking model is in reservations app
from core.models import SpecialPeriod   # Import SpecialPeriod from core app
from .models import CancellationRule   # Import CancellationRule from current app

def calculate_cancellation_fee(booking: Booking) -> Decimal:
    """
    Calculates the cancellation fee for a given booking based on hotel policies.

    Args:
        booking: The Booking object to calculate the fee for.

    Returns:
        The calculated cancellation fee as a Decimal, or Decimal(0) if no fee applies.
    """
    if not booking or not booking.check_in_date or not booking.hotel:
        # Cannot calculate without essential booking info
        return Decimal(0)

    # 1. Calculate days difference
    today = datetime.date.today()
    check_in_date = booking.check_in_date
    if today >= check_in_date:
        # Cancellation on or after check-in date usually means full charge or specific hotel policy
        # For simplicity, let's consider it as 0 days before check-in. Handle specific cases if needed.
        days_difference = 0
    else:
        days_difference = (check_in_date - today).days

    # 2. Determine if check-in is during a peak season
    is_peak_season = SpecialPeriod.objects.filter(
        start_date__lte=check_in_date,
        end_date__gte=check_in_date
    ).exists()

    # 3. Select the correct policy from the hotel
    hotel = booking.hotel
    policy = None
    if is_peak_season and hotel.cancellation_policy_peak:
        policy = hotel.cancellation_policy_peak
    elif hotel.cancellation_policy_normal:
        policy = hotel.cancellation_policy_normal

    if not policy:
        # No applicable policy found for the hotel
        return Decimal(0)

    # 4. Find the matching rule within the policy
    # We look for the rule where days_difference falls within its range.
    # Order by min days descending to find the most specific rule first if ranges overlap (though they shouldn't).
    applicable_rule = policy.rules.filter(
        days_before_checkin_min__lte=days_difference,
        days_before_checkin_max__gte=days_difference
    ).order_by('-days_before_checkin_min').first() # Get the most specific matching rule

    if not applicable_rule:
        # No rule covers this number of days (e.g., cancelled very far in advance)
        return Decimal(0)

    # 5. Calculate the penalty based on the rule
    penalty_value = applicable_rule.penalty_value
    penalty_type = applicable_rule.penalty_type
    total_amount = booking.total_amount or Decimal(0)
    duration = (booking.check_out_date - booking.check_in_date).days if booking.check_out_date and booking.check_in_date else 1
    duration = max(1, duration) # Avoid division by zero

    # Calculate approximate price per night for relevant penalty types
    # NOTE: This is an approximation. A more accurate calculation might require
    # summing the actual prices for each night from the 'Price' model if available.
    price_per_night_approx = total_amount / Decimal(duration)

    calculated_fee = Decimal(0)

    if penalty_type == 'PERCENT_TOTAL':
        calculated_fee = total_amount * (penalty_value / Decimal(100))
    elif penalty_type == 'PERCENT_FIRST_NIGHT':
        # Using approximation for first night price
        calculated_fee = price_per_night_approx * (penalty_value / Decimal(100))
    elif penalty_type == 'FIXED_NIGHTS':
        # Using approximation for price per night
        # Ensure penalty_value represents the number of nights
        calculated_fee = price_per_night_approx * penalty_value

    # Ensure fee doesn't exceed total amount
    calculated_fee = min(calculated_fee, total_amount)
    
    # Return the fee rounded to 0 decimal places (or adjust as needed)
    return calculated_fee.quantize(Decimal('1'))
