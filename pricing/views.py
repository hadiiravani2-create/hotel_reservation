# pricing/views.py
# version: 3.0.1
# FIX: Added input sanitization to remove spaces and non-breaking spaces (\xa0) from numbers.

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse

# Third-party imports
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from jdatetime import date as jdate, timedelta
import jdatetime

# Local imports
from hotels.models import RoomType, Hotel, BoardType
from .models import Price, Availability
from .selectors import find_available_hotels, calculate_multi_booking_price
from .serializers import (
    HotelSearchResultSerializer, 
    PriceQuoteInputSerializer, 
    PriceQuoteOutputSerializer
)
from reservations.serializers import PriceQuoteMultiRoomInputSerializer


# --- Helper Function for Sanitization ---
def clean_int(value):
    """
    Removes commas, spaces, and non-breaking spaces from input string
    and converts to integer.
    """
    if not value:
        return 0
    # Replace comma, standard space, and non-breaking space (\xa0)
    clean_str = str(value).replace(',', '').replace(' ', '').replace('\xa0', '')
    try:
        return int(clean_str)
    except ValueError:
        return 0

# ==============================================================================
# 1. API VIEWS (For Frontend / React)
# ==============================================================================

def get_rooms_for_hotel(request, hotel_id):
    rooms = RoomType.objects.filter(hotel_id=hotel_id).values('id', 'name')
    return JsonResponse({'rooms': list(rooms)})

def to_english_digits(text):
    if not text:
        return text
    persian_nums = '۰۱۲۳۴۵۶۷۸۹'
    arabic_nums = '٠١٢٣٤٥٦٧٨٩'
    english_nums = '0123456789'
    trans_table = str.maketrans(persian_nums + arabic_nums, english_nums * 2)
    return str(text).translate(trans_table)

# pricing/views.py

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def get_room_calendar(request, room_id):
    """
    Returns daily price and availability for a specific room AND board type.
    """
    try:
        year = int(request.GET.get('year'))
        month = int(request.GET.get('month'))
        # دریافت شناسه برد از کوئری پارامترها
        board_type_id = request.GET.get('board_type_id')
    except (TypeError, ValueError):
        today = jdate.today()
        year, month = today.year, today.month
        board_type_id = None

    try:
        start_date = jdate(year, month, 1)
        if month <= 6:
            days_in_month = 31
        elif month <= 11:
            days_in_month = 30
        else:
            days_in_month = 29 if not start_date.isleap() else 30
        
        end_date = jdate(year, month, days_in_month)
    except ValueError:
        return Response({"error": "Invalid date"}, status=400)
    
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    # --- اصلاح فیلتر قیمت ---
    price_qs = Price.objects.filter(
        room_type_id=room_id,
        date__range=[start_str, end_str]
    )
    
    # اگر برد خاصی انتخاب شده، فیلتر کن
    if board_type_id:
        price_qs = price_qs.filter(board_type_id=board_type_id)
    else:
        # اگر انتخاب نشده، اولین برد موجود را برگردان (یا منطق پیش‌فرض خودتان)
        # برای جلوگیری از تداخل، بهتر است همیشه برد ارسال شود.
        pass

    prices = price_qs.values('date', 'price_per_night')
    
    availabilities = Availability.objects.filter(
        room_type_id=room_id,
        date__range=[start_str, end_str]
    ).values('date', 'quantity')

    price_map = {str(p['date']): p['price_per_night'] for p in prices}
    avail_map = {str(a['date']): a['quantity'] for a in availabilities}

    calendar_data = []
    current_jalali = start_date
    
    for i in range(days_in_month):
        date_str_jalali = current_jalali.isoformat() 
        
        qty = avail_map.get(date_str_jalali, 0)
        price = price_map.get(date_str_jalali, 0)
        
        is_available = qty > 0 and price > 0
        
        status_text = f"{price:,}" if is_available else "تکمیل"
        
        calendar_data.append({
            "date": date_str_jalali,
            "day": current_jalali.day,
            "price": price if is_available else None,
            "is_available": is_available,
            "status_text": status_text
        })
        
        current_jalali += timedelta(days=1)

    return Response(calendar_data)

class HotelSearchAPIView(APIView):
    def get(self, request):
        city_id = request.query_params.get('city_id')
        check_in_str = request.query_params.get('check_in')
        duration = int(request.query_params.get('duration', 1))
        
        if not city_id or not check_in_str:
             return Response({"error": "City and check_in are required"}, status=400)

        try:
            # 1. تبدیل اعداد فارسی احتمالی به انگلیسی (مثلاً ۱۴۰۳ -> 1403)
            check_in_str = to_english_digits(check_in_str)
            
            # 2. پارس کردن تاریخ (فرض بر این است که ورودی شمسی است: YYYY-MM-DD)
            y, m, d = map(int, check_in_str.split('-'))
            
            # [FIX]: اینجا نباید از fromgregorian استفاده کنیم.
            # مستقیماً تاریخ شمسی می‌سازیم:
            check_in_jalali = jdatetime.date(year=y, month=m, day=d)
            
            # 3. تبدیل به میلادی برای جستجو در دیتابیس (چون دیتابیس میلادی ذخیره می‌کند)
            check_in_gregorian = check_in_jalali.togregorian()
            check_out_gregorian = check_in_gregorian + timedelta(days=duration)
            
            results = find_available_hotels(
                city_id=city_id,
                check_in_date=check_in_gregorian, # ارسال تاریخ میلادی به سلکتور
                check_out_date=check_out_gregorian,
                user=request.user,
                filters=request.query_params
            )
            return Response(results)
        except Exception as e:
            return Response({"error": f"Date parsing error: {str(e)}"}, status=500)

class PriceQuoteAPIView(APIView):
    def post(self, request):
        serializer = PriceQuoteInputSerializer(data=request.data)
        if serializer.is_valid():
            return Response({"status": "Logic needs to be connected to selectors"})
        return Response(serializer.errors, status=400)

class PriceQuoteMultiRoomAPIView(APIView):
    def post(self, request):
        serializer = PriceQuoteMultiRoomInputSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            # 1. Get string dates from serializer (keys match serializers.py now)
            check_in_str = data['check_in']
            check_out_str = data['check_out']
            
            try:
                # 2. Parse Check-in String -> Jalali Date Object
                # Assuming format is YYYY-MM-DD
                check_in_str = to_english_digits(check_in_str)
                y, m, d = map(int, check_in_str.split('-'))
                check_in_jalali = jdatetime.date(year=y, month=m, day=d)
                
                # 3. Calculate Check-out based on duration (Wait, serializer has check_out string, not duration)
                # Note: The input serializer has 'check_out', but the logic below seems to infer duration.
                # Let's rely on the explicit check_out string provided by frontend.
                check_out_str = to_english_digits(check_out_str)
                oy, om, od = map(int, check_out_str.split('-'))
                check_out_jalali = jdatetime.date(year=oy, month=om, day=od)

                # 4. Call Selector
                result = calculate_multi_booking_price(
                    booking_rooms=data['booking_rooms'], # Key is 'booking_rooms', not 'rooms'
                    check_in_date=check_in_jalali,
                    check_out_date=check_out_jalali,
                    user=request.user
                )
                
                if result:
                    return Response(result)
                return Response({"error": "Calculation failed or unavailable"}, status=400)
                
            except ValueError:
                 return Response({"error": "Invalid date format. Use YYYY-MM-DD (Jalali)."}, status=400)
            except Exception as e:
                 return Response({"error": str(e)}, status=500)

        return Response(serializer.errors, status=400)


# ==============================================================================
# 2. ADMIN VIEWS (Calendar Pricing Table)
# ==============================================================================

@staff_member_required
def calendar_pricing_view(request):
    """
    Renders a matrix table for managing prices and availability.
    """
    # 1. Determine Date Range
    today = jdate.today()
    try:
        selected_year = int(request.GET.get('year', today.year))
        selected_month = int(request.GET.get('month', today.month))
    except ValueError:
        selected_year = today.year
        selected_month = today.month
    
    # 2. Fetch Filters Data
    hotels = Hotel.objects.all()
    board_types = BoardType.objects.all()
    
    selected_hotel_id = request.GET.get('hotel_id')
    selected_board_id = request.GET.get('board_type_id')
    
    if not selected_hotel_id and hotels.exists():
        selected_hotel_id = str(hotels.first().id)
    
    if not selected_board_id and board_types.exists():
        selected_board_id = str(board_types.first().id)

    # 3. Handle POST (Saving Data)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                for key, value in request.POST.items():
                    if not value or key == 'csrfmiddlewaretoken': 
                        continue
                    
                    parts = key.split('_')
                    if len(parts) < 3: 
                        continue

                    if key.startswith('avail_'):
                        room_id = parts[1]
                        date_str = parts[2]
                        # FIX: Use clean_int function
                        qty = clean_int(value)
                        
                        Availability.objects.update_or_create(
                            room_type_id=room_id,
                            date=date_str,
                            defaults={'quantity': qty}
                        )
                        
                    elif key.startswith('price_'):
                        price_type = parts[1]
                        room_id = parts[2]
                        date_str = parts[3]
                        
                        # FIX: Use clean_int function (Handles '2 680 000' and '2,680,000')
                        amount = clean_int(value)
                        
                        price_obj, created = Price.objects.get_or_create(
                            room_type_id=room_id,
                            board_type_id=selected_board_id,
                            date=date_str,
                            defaults={
                                'price_per_night': 0,
                                'extra_person_price': 0,
                                'child_price': 0
                            }
                        )
                        
                        if price_type == 'base':
                            price_obj.price_per_night = amount
                        elif price_type == 'extra':
                            price_obj.extra_person_price = amount
                        elif price_type == 'child':
                            price_obj.child_price = amount
                        
                        price_obj.save()
                        
            messages.success(request, "تغییرات با موفقیت ذخیره شد.")
        except Exception as e:
            messages.error(request, f"خطا در ذخیره‌سازی: {str(e)}")
        
        return redirect(f"{request.path}?{request.GET.urlencode()}")

    # 4. Prepare Data for GET Request
    try:
        first_day_of_month = jdate(selected_year, selected_month, 1)
        if selected_month < 12:
            next_month = jdate(selected_year, selected_month + 1, 1)
            days_in_month = (next_month - first_day_of_month).days
        else:
            days_in_month = 29 if not first_day_of_month.isleap() else 30
    except ValueError:
        days_in_month = 30 

    month_dates = []
    month_days_display = []
    for i in range(days_in_month):
        d = first_day_of_month + timedelta(days=i)
        month_dates.append(d.isoformat())
        month_days_display.append(d.day)

    rooms = RoomType.objects.filter(hotel_id=selected_hotel_id) if selected_hotel_id else []
    
    room_data = []
    if rooms:
        avail_qs = Availability.objects.filter(room_type__in=rooms, date__in=month_dates)
        avail_map = {}
        for a in avail_qs:
            avail_map[(a.room_type_id, str(a.date))] = a.quantity
        
        price_qs = Price.objects.filter(room_type__in=rooms, board_type_id=selected_board_id, date__in=month_dates)
        price_map = {}
        for p in price_qs:
            price_map[(p.room_type_id, str(p.date))] = p

        for room in rooms:
            days_info = []
            for d_str in month_dates:
                availability = avail_map.get((room.id, d_str), 0)
                price_obj = price_map.get((room.id, d_str))
                
                days_info.append({
                    'date_str': d_str,
                    'availability': availability,
                    'price_base': int(price_obj.price_per_night) if price_obj else None,
                    'price_extra': int(price_obj.extra_person_price) if price_obj else None,
                    'price_child': int(price_obj.child_price) if price_obj else None,
                })
            
            room_data.append({
                'id': room.id,
                'name': room.name,
                'days': days_info
            })

    context = {
        'years': range(1402, 1406),
        'months': [(i, jdate(1400, i, 1).strftime('%B')) for i in range(1, 13)],
        'hotels': hotels,
        'board_types': board_types,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'selected_hotel_id': int(selected_hotel_id) if selected_hotel_id else None,
        'selected_board_id': int(selected_board_id) if selected_board_id else None,
        'month_days': month_days_display,
        'room_data': room_data,
        'title': 'تقویم مدیریت قیمت و ظرفیت',
    }
    
    return render(request, 'admin/pricing/calendar_view.html', context)
