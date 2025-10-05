# pricing/tests.py v1.5
# This file is correct and correctly identifies the bug in the selector.
from django.test import TestCase
from jdatetime import date as jdate
from decimal import Decimal
from datetime import timedelta

from core.models import CustomUser
from hotels.models import City, Hotel, RoomType, BoardType
from agencies.models import Agency, Contract, AgencyUser
from .models import Availability, Price
from .selectors import find_available_hotels, _get_daily_price_for_user

class PricingSelectorTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        cls.normal_user = CustomUser.objects.create_user(username='normaluser', password='password')
        cls.agency_user = CustomUser.objects.create_user(username='agencyuser', password='password')

        cls.city = City.objects.create(name="Test City", slug="test-city")
        cls.hotel = Hotel.objects.create(name="Test Hotel", slug="test-hotel", city=cls.city, stars=5)
        cls.board_type = BoardType.objects.create(name="Bed and Breakfast", code="BB")

        cls.room_type = RoomType.objects.create(
            hotel=cls.hotel, 
            name="Double Room", 
            code="DBL-TEST",
            base_capacity=2,
            price_per_night=Decimal('1000000')
        )

        cls.agency = Agency.objects.create(name="Test Agency")
        AgencyUser.objects.create(user=cls.agency_user, agency=cls.agency)
        
        cls.contract = Contract.objects.create(
            agency=cls.agency,
            hotel=cls.hotel,
            title="10% Discount Contract",
            start_date=jdate(1404, 1, 1),
            end_date=jdate(1404, 12, 29),
            contract_type='dynamic',
            discount_percentage=10
        )

        cls.check_in = jdate(1404, 7, 1)
        cls.check_out = jdate(1404, 7, 5) # This is a 4-night stay
        duration = (cls.check_out - cls.check_in).days
        
        for i in range(duration + 2):
            current_date = cls.check_in + timedelta(days=i)
            Availability.objects.create(room_type=cls.room_type, date=current_date, quantity=5)
            Price.objects.create(
                room_type=cls.room_type,
                board_type=cls.board_type,
                date=current_date,
                price_per_night=Decimal('1000000'),
                extra_person_price=Decimal('200000'),
                child_price=Decimal('100000')
            )

    def test_find_available_hotels_successfully(self):
        results = find_available_hotels(
            city_id=self.city.id,
            check_in_date=self.check_in,
            check_out_date=self.check_out,
            user=self.normal_user
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['hotel_id'], self.hotel.id)
        # The expected value must be the AVERAGE price per night.
        self.assertEqual(results[0]['min_price'], Decimal('1000000.00'))

    def test_find_available_hotels_no_availability(self):
        check_in = jdate(1405, 1, 1)
        check_out = jdate(1405, 1, 3)
        results = find_available_hotels(
            city_id=self.city.id,
            check_in_date=check_in,
            check_out_date=check_out,
            user=self.normal_user
        )
        self.assertEqual(len(results), 0)

    def test_get_daily_price_for_normal_user(self):
        price_info = _get_daily_price_for_user(
            self.room_type, self.board_type, self.check_in, self.normal_user
        )
        self.assertIsNotNone(price_info)
        self.assertEqual(price_info['price_per_night'], Decimal('1000000'))

    def test_get_daily_price_for_agency_user_with_discount(self):
        agency_user_with_profile = CustomUser.objects.get(id=self.agency_user.id)
        price_info = _get_daily_price_for_user(
            self.room_type, self.board_type, self.check_in, agency_user_with_profile
        )
        self.assertIsNotNone(price_info)
        self.assertEqual(price_info['price_per_night'], Decimal('900000.00'))
