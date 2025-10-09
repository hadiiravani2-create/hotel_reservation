// static/admin/js/booking_form.js

document.addEventListener("DOMContentLoaded", function() {
    // اطمینان از اجرای کد فقط در صفحه افزودن/ویرایش رزرو
    if (!window.location.pathname.includes('/admin/reservations/booking/')) {
        return;
    }

    const roomTypeSelect = document.querySelector("#id_room_type");
    const checkInInput = document.querySelector("#id_check_in");
    const checkOutInput = document.querySelector("#id_check_out");
    const adultsInput = document.querySelector("#id_adults");
    const childrenInput = document.querySelector("#id_children");
    const priceInput = document.querySelector("#id_total_price");
    const quoteApiUrl = "/pricing/api/calculate-price/";

    // تابعی برای ارسال درخواست به API
    function updatePrice() {
        const roomTypeId = roomTypeSelect.value;
        const checkIn = checkInInput.value;
        const checkOut = checkOutInput.value;
        const adults = adultsInput.value;
        const children = childrenInput.value;

        // فقط در صورتی که تمام فیلدها مقدار داشته باشند، درخواست را ارسال کن
        if (!roomTypeId || !checkIn || !checkOut || !adults) {
            return;
        }

        const payload = {
            room_type_id: parseInt(roomTypeId),
            check_in: checkIn,
            check_out: checkOut,
            adults: parseInt(adults),
            children: parseInt(children) || 0,
        };

        // برای جلوگیری از ارسال هدر CSRF در درخواست GET/POST داخلی
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        fetch(quoteApiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            if (data.total_price !== undefined) {
                priceInput.value = data.total_price;
            }
        })
        .catch(error => console.error("Error fetching price:", error));
    }

    // افزودن event listener به تمام فیلدهای مرتبط
    roomTypeSelect.addEventListener("change", updatePrice);
    checkInInput.addEventListener("change", updatePrice);
    checkOutInput.addEventListener("change", updatePrice);
    adultsInput.addEventListener("change", updatePrice);
    childrenInput.addEventListener("change", updatePrice);
});
