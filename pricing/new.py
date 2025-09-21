# وارد کردن ابزارهای لازم
from pricing.selectors import find_available_rooms
from hotels.models import City
from jdatetime import date as jdate

# فرض می‌کنیم می‌خواهیم برای شهر اول در دیتابیس جستجو کنیم
city_to_search = City.objects.first()
if not city_to_search:
    print("لطفاً ابتدا یک شهر در پنل ادمین اضافه کنید.")
else:
    # تعریف پارامترهای جستجو
    check_in = jdate(1404, 6, 2)  # تاریخ را به شمسی وارد می‌کنیم
    check_out = jdate(1404, 6, 7)
    adult_count = 2
    child_count = 0

    print(f"در حال جستجو در شهر '{city_to_search.name}' از تاریخ {check_in} تا {check_out}...")

    # فراخوانی تابع اصلی جستجو
    results = find_available_rooms(
        city_id=city_to_search.id,
        check_in_date=check_in,
        check_out_date=check_out,
        adults=adult_count,
        children=child_count
    )

    # چاپ نتایج
    if results:
        print("اتاق‌های موجود پیدا شد:")
        for room in results:
            print(f"  - هتل: {room['hotel_name']}, اتاق: {room['room_name']}, قیمت کل: {room['total_price']} تومان")
    else:
        print("هیچ اتاق خالی با این مشخصات پیدا نشد.")